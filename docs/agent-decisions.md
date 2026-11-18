# Agent-assisted decisions

## 2026-11-18 — Connect YOLO tracking to the shared court harness

- **Issue/PR:** no issue or PR created for this integration yet. The prerequisite harness entered `main` in PR #2 (`e22f8e5`). Work continues on the user's existing `aadi-yolo-player-tracking` branch, which predates the adopted naming convention; future branches follow `DEVELOPMENT.md`.
- **Human direction:** integrate the merged geometry/harness, preserving explicit player selection and continuous YOLO pose + ByteTrack tracking. The user approved approximate corners for a smoke test only.
- **Decision:** merge `origin/main` into the existing branch and register an adapter reading completed schema-1.1 exports. Keep the model, tracker, multi-player UI and native exports intact. Geometry and zones remain shared.
- **Alternatives:** running ByteTrack on sparse samples changes temporal behavior; re-running inference for every evaluation duplicates work; nearest-timestamp matching needs a tolerance and can choose a different frame. The adapter instead uses exact source indices retained by the harness sampler.
- **Contract:** one explicit player per evaluation, validated source SHA-256/dimensions/model/window and observations, resized points, preserved nulls, and a provenance file retaining missing reasons and ankle reference. This does not establish equivalence with heel/floor-contact labels.
- **Initial dependency approach (superseded below):** reuse the locked Python 3.12 YOLO environment and align shared OpenCV/pytest requirements with it. Review of MediaPipe PR #3 led to keeping the model environments separate instead; no new library was added.
- **Consequences:** trajectories can be evaluated repeatedly through common geometry. Near-half zone scope and one player per harness run remain. Shared UI wiring, measured accuracy, reference-point agreement and production packaging remain follow-ups. Experiment imports are temporary; product code should eventually move to the directories specified in `DEVELOPMENT.md`.
- **Approach changes:** exact-frame sampling replaces the proposed nearest-timestamp approach for this adapter. Unique directories prevent evaluations overwriting each other. The older process proposal now points to the adopted process.
- **Agent involvement:** Codex implemented adapter/sampling/CLI changes, tests and docs and ran local verification. Human diff review, teammate approval, remote CI and pushing this integration are not claimed.

Commands, outcomes, limitations and local evidence are in
[the YOLO notes](../doc/yolo-player-tracking.md#shared-harness-integration--2026-11-18).

## 2026-11-18 — Align the YOLO integration with MediaPipe PR #3

- **Issue/PR:** compatibility review of [PR #3](https://github.com/AadiBiyani/PickleBallMatching/pull/3) at `fc4b620e9cd3a194198671d74ea88b4974834ce4`, following integration commit `c13573c`.
- **Factory decision:** preserve ordinary `factory(model)` calls. Route `positions_path` and `player_id` only to YOLO, and reject them for other analyzers. Passing even null YOLO keywords to every factory would break PR #3's one-argument MediaPipe factory. Regression tests exercise that exact signature; an isolated combined copy also runs PR #3's actual adapter tests.
- **Dependency correction:** supersedes the earlier combined-environment approach. Restore shared `requirements.txt` to `main` and keep YOLO's locked environment separate. This avoids changing MediaPipe's dependency choices or installing overlapping OpenCV distributions together. A single environment would require a separately resolved and validated dependency set; it is not established here.
- **Formatting decision:** restore unchanged statements' existing layout and verify equal syntax trees. Add a local Ruff configuration matching YOLO's line length for new files; lint the modified shared files but avoid reformatting their surrounding code. No repository-wide formatting migration is implied.
- **Validation boundary:** PR #3's adapter and tests were exercised in an isolated, ignored copy. This verifies factory/point-contract compatibility with stub detections, not real MediaPipe installation or inference. Keep recorded local results distinct from remote CI and teammate review.
