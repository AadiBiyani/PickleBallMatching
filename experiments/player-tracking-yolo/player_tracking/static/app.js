"use strict";
const el = id => document.getElementById(id);
let videoId, preview, jobId, manifest, positions;
let selections = [];
const selectedCandidates = new Set();
let playing = false, timer, pollTimer;

async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map(item => `${item.loc.join(".")}: ${item.msg}`).join("\n") : data.detail;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}
function showError(error) { el("error").textContent = error.message; el("error").hidden = false; }
function clearError() { el("error").hidden = true; }
function status(text) { el("progress-area").hidden = false; el("status").textContent = text; }
function busy(value) {
  for (const id of ["upload-button", "preview-button", "preview-frame", "video-file", "max-frames", "ankle-confidence"]) el(id).disabled = value;
  el("run-button").disabled = value || !selections.length;
  el("candidates").disabled = value;
  el("candidate-overlays").querySelectorAll("button").forEach(button => button.disabled = value);
}
function pause() { playing = false; clearTimeout(timer); el("play-button").textContent = "Play frames"; }
function clearResults() { pause(); clearTimeout(pollTimer); el("results").hidden = true; el("retry-status").hidden = true; }

el("upload-form").addEventListener("submit", async event => {
  event.preventDefault(); clearError(); clearResults(); selections = []; selectedCandidates.clear();
  el("selection-section").hidden = true; el("source-info").textContent = ""; busy(true);
  el("progress").value = 0; status("Uploading and checking the video…");
  try {
    const body = new FormData(); body.append("file", el("video-file").files[0]);
    const data = await request("/api/videos", {method:"POST", body});
    videoId = data.video_id;
    const source = data.source;
    el("source-info").textContent = `${source.width} × ${source.height} pixels · ${source.fps.toFixed(2)} FPS · ${source.duration_s.toFixed(1)} seconds`;
    el("preview-frame").value = 0; el("preview-frame").max = source.frame_count - 1;
    await loadPreview();
  } catch (error) { showError(error); status("Upload or preview failed. Check the error and try again."); }
  finally { busy(false); }
});

async function loadPreview() {
  selections = []; selectedCandidates.clear(); clearResults(); busy(true); status("Finding people in the preview…");
  el("candidate-list").replaceChildren(); el("candidate-overlays").replaceChildren();
  el("selection-info").textContent = "Select a player to continue.";
  // Hide stale imagery until the response and original-resolution image both arrive.
  el("selection-section").hidden = true;
  preview = await request(`/api/videos/${videoId}/preview?frame_index=${Number(el("preview-frame").value)}`);
  el("preview-image").src = preview.image_url;
  await el("preview-image").decode();
  preview.candidates.forEach((candidate, index) => {
    const label = document.createElement("label");
    const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.name = "player"; checkbox.value = index;
    checkbox.addEventListener("change", () => choosePlayer(index));
    label.append(checkbox, ` Candidate ${index + 1}`); el("candidate-list").append(label);
    const box = document.createElement("button"); box.type = "button"; box.className = "candidate-box";
    box.setAttribute("aria-label", `Toggle candidate ${index + 1}`); box.setAttribute("aria-pressed", "false");
    const badge = document.createElement("span"); badge.textContent = index + 1; box.append(badge);
    const {x1,y1,x2,y2} = candidate.bbox;
    Object.assign(box.style, {left:`${100*x1/preview.source.width}%`, top:`${100*y1/preview.source.height}%`, width:`${100*(x2-x1)/preview.source.width}%`, height:`${100*(y2-y1)/preview.source.height}%`});
    box.addEventListener("click", () => choosePlayer(index)); el("candidate-overlays").append(box);
  });
  el("selection-section").hidden = false;
  status(preview.candidates.length ? "Preview ready. Select one or more on-court players." : "No people detected. Try a different starting frame or a clearer recording.");
}
function choosePlayer(index) {
  // Keep the original bbox untouched. CSS scales only its visual representation.
  if (selectedCandidates.has(index)) selectedCandidates.delete(index); else selectedCandidates.add(index);
  const indexes = [...selectedCandidates].sort((a,b) => a-b);
  selections = indexes.map(i => ({frame_index:preview.frame_index, bbox:{...preview.candidates[i].bbox}}));
  el("candidate-list").querySelectorAll("input").forEach((checkbox,i) => checkbox.checked = selectedCandidates.has(i));
  el("candidate-overlays").querySelectorAll("button").forEach((button,i) => button.setAttribute("aria-pressed", String(selectedCandidates.has(i))));
  const mapping = indexes.map((i,n) => `Candidate ${i+1} → player_${n+1}`).join("; ");
  el("selection-info").textContent = selections.length ? `${mapping}. Selected at frame ${preview.frame_index} in original ${preview.source.width} × ${preview.source.height} pixels.` : "Select at least one player to continue.";
  el("run-button").disabled = !selections.length;
}
el("preview-form").addEventListener("submit", async event => {
  event.preventDefault(); clearError();
  try { await loadPreview(); } catch (error) { showError(error); status("Preview failed. Upload again or try another frame."); }
  finally { busy(false); }
});
el("run-form").addEventListener("submit", async event => {
  event.preventDefault(); clearError(); clearResults(); busy(true); el("progress").value = 0;
  try {
    const job = await request("/api/jobs", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({video_id:videoId, selections, config:{max_frames:Number(el("max-frames").value), ankle_confidence:Number(el("ankle-confidence").value)}})});
    jobId = job.job_id; await poll();
  } catch (error) { showError(error); status("Could not start tracking."); busy(false); }
});
async function poll() {
  try {
    const job = await request(`/api/jobs/${jobId}`);
    el("progress").max = job.total_frames; el("progress").value = job.processed_frames;
    status(`${job.status.charAt(0).toUpperCase()+job.status.slice(1)} · ${job.processed_frames} / ${job.total_frames} frames`);
    if (["queued","running"].includes(job.status)) { pollTimer = setTimeout(poll, 750); return; }
    busy(false);
    if (job.status === "failed") showError(new Error(`Tracking failed: ${job.error}`));
    if (job.artifacts_available) await showResults(job);
  } catch (error) { showError(error); el("retry-status").hidden = false; status("Could not read job status. Use Check job status to reconnect."); }
}
el("retry-status").addEventListener("click", () => { clearError(); el("retry-status").hidden = true; poll(); });
async function showResults(job) {
  const base = `/api/jobs/${jobId}/artifacts/`;
  [manifest, positions] = await Promise.all([request(base+"manifest.json"), request(base+"positions.json")]);
  const data = job.metadata;
  el("processed").textContent = data.processed_frame_count; el("usable").textContent = data.usable_position_count;
  el("missing").textContent = data.missing_counts.target_not_detected; el("unreliable").textContent = data.missing_counts.keypoints_unreliable;
  el("completion").textContent = data.complete ? "Requested window complete. Review the selected players and ankle estimates below." : "Incomplete run. Downloads contain only the frames saved before the failure.";
  el("observation-info").textContent = `${data.selected_player_count} selected players × ${data.processed_frame_count} frames = ${data.observation_count} player observations. Missing counts include one record per player per frame.`;
  el("player-results").replaceChildren();
  for (const [player,counts] of Object.entries(data.per_player_counts)) {
    const tr = document.createElement("tr");
    for (const value of [player, data.selected_track_ids?.[player] ?? "unavailable", counts.ok, counts.target_not_detected, counts.keypoints_unreliable]) {
      const td = document.createElement("td"); td.textContent = value; tr.append(td);
    }
    el("player-results").append(tr);
  }
  el("timing").textContent = `Processing: ${data.tracking_processing_s.toFixed(2)} s · Model loading: ${data.model_load_s?.toFixed(2) ?? "unavailable"} s · Device: ${data.device} · Timestamps: ${data.timestamp_source}`;
  el("downloads").replaceChildren();
  for (const [file,label] of [["positions.json","Download JSON"],["positions.csv","Download CSV"],["run.json","Run metadata"],["manifest.json","Frame manifest"]]) {
    const link = document.createElement("a"); link.href = base+file; link.textContent = label; link.download = file; el("downloads").append(link);
  }
  el("results").hidden = false; el("viewer").hidden = !manifest.frames.length;
  el("frame-slider").max = Math.max(0,manifest.frames.length-1); el("frame-slider").value = 0;
  if (manifest.frames.length) await showFrame(0);
  else el("frame-reasons").textContent = "No annotated frames were produced.";
}
async function showFrame(index) {
  const frame = manifest.frames[index];
  const records = positions.frames.filter(row => row.frame_index === frame.frame_index);
  el("frame-slider").value = index;
  el("result-image").src = `/api/jobs/${jobId}/frames/${frame.file}`;
  await el("result-image").decode();
  el("frame-info").textContent = `Frame ${frame.frame_index} · ${frame.timestamp_s.toFixed(3)} s`;
  el("frame-reasons").replaceChildren();
  for (const record of records) {
    const li = document.createElement("li");
    li.textContent = `${record.player_id}: ` + (record.status === "ok" ? `usable ankle midpoint (${record.image_x_px.toFixed(1)}, ${record.image_y_px.toFixed(1)}) pixels.` : `missing position — ${record.reason}`);
    el("frame-reasons").append(li);
  }
}
async function advance() {
  if (!playing) return;
  const index = Number(el("frame-slider").value);
  if (index >= manifest.frames.length-1) { pause(); return; }
  const delay = Math.max(1, 1000*(manifest.frames[index+1].timestamp_s-manifest.frames[index].timestamp_s));
  timer = setTimeout(async () => { if (!playing) return; try { await showFrame(index+1); advance(); } catch (error) { pause(); showError(error); } },delay);
}
el("play-button").addEventListener("click", async () => {
  if (playing) { pause(); return; }
  try {
    if (Number(el("frame-slider").value) >= manifest.frames.length-1) await showFrame(0);
    playing = true; el("play-button").textContent = "Pause frames"; advance();
  } catch (error) { pause(); showError(error); }
});
el("frame-slider").addEventListener("input", () => { pause(); showFrame(Number(el("frame-slider").value)).catch(showError); });
