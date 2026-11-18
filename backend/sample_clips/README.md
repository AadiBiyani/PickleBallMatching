# Sample clips

Put pre-recorded drill clips (`.mp4` or `.mov`) in this folder. The API lists them at `GET /api/clips`, and the "upload" step sends the chosen clip to the selected vision model. In the prototype, recording and upload are simulated.

Clips are gitignored: they are large and show identifiable people (SDP SYS-08). Share them through the team drive instead.

Each clip also needs its four court corners in `corners.json` in this folder. The format is the court evaluation harness's registry; see `../corners.example.json`. Without corners, a clip is listed but can't be analyzed.

If the folder is empty, the API offers a synthetic clip. Only models with `requires_clip_file = False`, such as the simulated tracker, accept it.
