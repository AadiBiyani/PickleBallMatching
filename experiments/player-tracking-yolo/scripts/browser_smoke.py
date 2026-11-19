"""Opt-in real-model browser check, separate from the offline pytest suite.

Run the local server first. Candidate numbers are 1-based and must be visually chosen.
Screenshots and the observed job response are saved locally, never committed.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--frame", type=int, default=0)
    parser.add_argument("--candidates", type=int, nargs="+", required=True)
    parser.add_argument("--max-frames", type=int, default=60)
    parser.add_argument("--output", type=Path, default=Path("runtime/browser-evidence"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(120000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url)
        page.get_by_label("Local video").set_input_files(args.video.resolve())
        with page.expect_response(lambda response: "/preview?" in response.url) as preview_response:
            page.get_by_role("button", name="Upload video").click()
        preview = preview_response.value.json()
        expect(page.locator("#selection-section")).to_be_visible()
        if args.frame:
            page.get_by_label("Starting frame").fill(str(args.frame))
            with page.expect_response(lambda response: "/preview?" in response.url) as response:
                page.get_by_role("button", name="Update preview").click()
            preview = response.value.json()
            expect(page.locator("#selection-section")).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        for candidate in args.candidates:
            checkbox = page.get_by_role("checkbox", name=f"Candidate {candidate}", exact=True)
            checkbox.focus()
            checkbox.press("Space")
            expect(checkbox).to_be_checked()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(args.output / "selection-mobile.png"), full_page=True)
        page.get_by_label("Frames to process").fill(str(args.max_frames))
        with (
            page.expect_request(lambda req: req.url.endswith("/api/jobs") and req.method == "POST") as posted,
            page.expect_response(lambda response: response.url.endswith("/api/jobs")) as started,
        ):
            page.get_by_role("button", name="Track selected players").click()
        submitted = posted.value.post_data_json
        expected = [
            {"frame_index": args.frame, "bbox": preview["candidates"][index - 1]["bbox"]}
            for index in sorted(args.candidates)
        ]
        assert submitted["selections"] == expected, (
            "Display resizing changed original-image selection coordinates"
        )
        job_id = started.value.json()["job_id"]
        expect(page.locator("#results")).to_be_visible(timeout=180000)
        job = page.request.get(f"{args.url}/api/jobs/{job_id}").json()
        assert job["status"] == "completed", job
        assert job["metadata"]["selected_player_count"] == len(args.candidates)
        assert job["metadata"]["observation_count"] == job["processed_frames"] * len(args.candidates)
        expect(page.locator("#player-results tr")).to_have_count(len(args.candidates))
        page.get_by_role("button", name="Play frames").click()
        page.wait_for_function("Number(document.getElementById('frame-slider').value) >= 2")
        page.get_by_role("button", name="Pause frames").click()
        slider = page.get_by_label("Annotated frame", exact=True)
        slider.fill(str(job["processed_frames"] - 1))
        page.wait_for_function(
            "document.getElementById('result-image').complete && document.getElementById('result-image').naturalWidth > 0"
        )
        expect(page.locator("#frame-info")).to_contain_text(
            f"Frame {args.frame + job['processed_frames'] - 1}"
        )
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(args.output / "results-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.locator("#results").screenshot(path=str(args.output / "results-desktop.png"))
        with page.expect_download() as download:
            page.get_by_role("link", name="Download JSON").click()
        downloaded = args.output / "downloaded-positions.json"
        download.value.save_as(downloaded)
        assert json.loads(downloaded.read_text())["metadata"]["run_id"] == job_id
        assert not errors, errors
        report = {
            "job": job,
            "checks": [
                "real upload and preview",
                "keyboard multi-selection",
                "original pixel boxes preserved at 390px width",
                "real tracking completed",
                "per-player counts",
                "frame playback advanced",
                "scrubbed final frame",
                "JSON download",
                "no horizontal overflow",
                "no JavaScript page errors",
            ],
        }
        (args.output / "browser-check.json").write_text(json.dumps(report, indent=2))
        print(
            json.dumps({"job_id": job_id, "metadata": job["metadata"], "checks": report["checks"]}, indent=2)
        )
        browser.close()


if __name__ == "__main__":
    main()
