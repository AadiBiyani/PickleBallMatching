"""Local-only demo. One worker owns all inference; jobs are forgotten on restart."""

import asyncio
import copy
import json
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from .backend import RUNTIME, YoloBackend
from .contracts import InputError, Selection, StrictModel, TrackingConfig
from .tracking import preview_video, run_tracking
from .video import MAX_UPLOAD_BYTES, inspect_video

STATIC = Path(__file__).with_name("static")
ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
ARTIFACTS = {"positions.json", "positions.csv", "run.json", "manifest.json"}


class JobRequest(StrictModel):
    video_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    selections: list[Selection] = Field(min_length=1, max_length=8)
    config: TrackingConfig = Field(default_factory=TrackingConfig)


class LocalService:
    def __init__(self, root, backend_factory):
        self.root = root
        self.backend_factory = backend_factory
        self.videos = {}
        self.jobs = {}
        self.lock = threading.RLock()
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="yolo")
        self.pending = 0
        (root / "uploads").mkdir(parents=True, exist_ok=True)

    def submit(self, function, *args):
        with self.lock:
            if self.pending >= 8:
                raise HTTPException(429, "Inference queue is full. Wait for an existing job to finish.")
            self.pending += 1
        future = self.worker.submit(function, *args)

        def finished(_):
            with self.lock:
                self.pending -= 1

        future.add_done_callback(finished)
        return future

    def video(self, video_id):
        with self.lock:
            if not ID_PATTERN.fullmatch(video_id) or video_id not in self.videos:
                raise HTTPException(404, "Video not found. Upload again after a server restart.")
            return self.videos[video_id]

    def job(self, job_id):
        with self.lock:
            if not ID_PATTERN.fullmatch(job_id) or job_id not in self.jobs:
                raise HTTPException(404, "Job not found. Jobs do not survive a server restart.")
            return copy.deepcopy(self.jobs[job_id])

    def update(self, job_id, **changes):
        with self.lock:
            self.jobs[job_id].update(changes)

    def run_job(self, job_id, request):
        self.update(job_id, status="running")
        try:
            result = run_tracking(
                self.video(request.video_id)["path"],
                request.selections,
                request.config,
                self.root / "runs",
                run_id=job_id,
                backend_factory=self.backend_factory,
                progress=lambda done, total: self.update(job_id, processed_frames=done, total_frames=total),
            )
            self.update(job_id, status="completed", metadata=result["metadata"], artifacts_available=True)
        except Exception as error:  # noqa: BLE001 -- job failure must not kill the worker
            metadata_file = self.root / "runs" / job_id / "run.json"
            try:
                metadata = json.loads(metadata_file.read_text()) if metadata_file.is_file() else None
            except (OSError, ValueError):
                metadata = None  # A failed export must still transition the job out of running.
            self.update(
                job_id,
                status="failed",
                error=str(error),
                metadata=metadata,
                artifacts_available=metadata is not None,
            )


def create_app(data_dir=None, backend_factory=YoloBackend):
    service = LocalService(Path(data_dir) if data_dir else RUNTIME / "api", backend_factory)

    @asynccontextmanager
    async def lifespan(app):
        yield
        service.worker.shutdown(wait=True, cancel_futures=True)

    app = FastAPI(title="Pickleball player tracking · local prototype", lifespan=lifespan)
    app.state.service = service

    @app.get("/api/health")
    def health():
        return {"status": "ok", "model": "yolo26n-pose.pt", "worker_count": 1}

    @app.post("/api/videos", status_code=201)
    async def upload(file: UploadFile):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
            await file.close()
            raise HTTPException(422, "Choose an MP4, MOV, AVI, MKV, or WebM video.")
        video_id = uuid.uuid4().hex
        path = service.root / "uploads" / f"{video_id}{suffix}"
        try:
            size = 0
            with path.open("xb") as destination:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, "Video exceeds the 600 MiB local-demo limit.")
                    destination.write(chunk)
            info = await asyncio.to_thread(inspect_video, path, enforce_demo_limits=True)
            with service.lock:
                service.videos[video_id] = {"path": path, "info": info}
            return {"video_id": video_id, "source": info.model_dump()}
        except (InputError, OSError) as error:
            path.unlink(missing_ok=True)
            raise HTTPException(422, str(error)) from error
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

    @app.get("/api/videos/{video_id}/preview")
    async def preview(video_id: str, frame_index: int = Query(default=0, ge=0)):
        video = service.video(video_id)
        if frame_index >= video["info"].frame_count:
            raise HTTPException(422, "Preview frame is outside the video.")
        output = service.root / "previews" / video_id / str(frame_index)
        future = service.submit(
            preview_video, video["path"], output, frame_index, TrackingConfig(), service.backend_factory
        )
        try:
            result = await asyncio.wrap_future(future)
        except Exception as error:
            raise HTTPException(422, f"Preview failed: {error}") from error
        result["image_url"] = f"/api/videos/{video_id}/preview/{frame_index}.jpg"
        return result

    @app.get("/api/videos/{video_id}/preview/{frame_index}.jpg")
    def preview_image(video_id: str, frame_index: int):
        service.video(video_id)
        path = service.root / "previews" / video_id / str(frame_index) / "preview.jpg"
        if frame_index < 0 or not path.is_file():
            raise HTTPException(404, "Generate this preview first.")
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/jobs", status_code=202)
    def start_job(request: JobRequest):
        info = service.video(request.video_id)["info"]
        if any(
            item.frame_index >= info.frame_count or not item.bbox.in_image(info.width, info.height)
            for item in request.selections
        ):
            raise HTTPException(422, "Selection must lie within the original video frame.")
        first_frame = request.selections[0].frame_index
        if any(item.frame_index != first_frame for item in request.selections):
            raise HTTPException(422, "Select all players on the same preview frame.")
        job_id = uuid.uuid4().hex
        with service.lock:
            service.jobs[job_id] = {
                "job_id": job_id,
                "video_id": request.video_id,
                "status": "queued",
                "error": None,
                "processed_frames": 0,
                "total_frames": min(request.config.max_frames, info.frame_count - first_frame),
                "artifacts_available": False,
                "metadata": None,
            }
        try:
            service.submit(service.run_job, job_id, request)
        except HTTPException:
            with service.lock:
                del service.jobs[job_id]
            raise
        return {"job_id": job_id, "status": "queued", "status_url": f"/api/jobs/{job_id}"}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        return service.job(job_id)

    @app.get("/api/jobs/{job_id}/artifacts/{name}")
    def artifact(job_id: str, name: str):
        job = service.job(job_id)
        if name not in ARTIFACTS or not job["artifacts_available"]:
            raise HTTPException(404, "Artifact is not available.")
        path = service.root / "runs" / job_id / name
        if not path.is_file():
            raise HTTPException(404, "Artifact is missing from disk.")
        return FileResponse(path, filename=name)

    @app.get("/api/jobs/{job_id}/frames/{frame_name}")
    def frame(job_id: str, frame_name: str):
        job = service.job(job_id)
        if not re.fullmatch(r"[0-9]{8}\.jpg", frame_name) or not job["artifacts_available"]:
            raise HTTPException(404, "Annotated frame is not available.")
        path = service.root / "runs" / job_id / "frames" / frame_name
        if not path.is_file():
            raise HTTPException(404, "Annotated frame is missing from disk.")
        return FileResponse(path, media_type="image/jpeg")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    return app
