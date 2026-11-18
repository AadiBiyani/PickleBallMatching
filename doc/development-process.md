# Proposed team development process

**Status: proposed for team review. Adoption, peer approval, and remote CI execution have not been verified.** The [software development plan](../docs/software-development-plan.md) remains the delivery-sequence source; the [project proposal](../docs/project-proposal.md) remains the product-scope source.

## Current architecture

```text
PickleBallMatching/
├── AGENTS.md                          short repository instructions
├── docs/
│   ├── project-proposal.md            product scope/intended architecture
│   └── software-development-plan.md   requirements and sequence
├── Player_Tracking_Context.md         supplied handoff
├── doc/
│   ├── development-process.md         this proposed process
│   └── yolo-player-tracking.md        implementation/evidence/limitations
└── experiments/player-tracking-yolo/
    ├── README.md                      commands, contract and limitations
    ├── pyproject.toml + uv.lock       Python package and pinned environment
    ├── player_tracking/
    │   ├── contracts.py               typed inputs/observations
    │   ├── backend.py + bytetrack.yaml pretrained model adapter/config
    │   ├── video.py + selection.py    decoding, IDs and ankle positions
    │   ├── tracking.py + exports.py   continuous pipeline and output boundary
    │   ├── cli.py + api.py            shared-core entry points and jobs
    │   └── static/                    HTML/CSS/JS client
    ├── tests/                         deterministic offline checks
    ├── scripts/browser_smoke.py       opt-in real model/browser check
    └── runtime/                       ignored local artifacts
```

The browser calls FastAPI; FastAPI serializes inference through one worker. CLI and API share the tracking core. Liam's framework should consume the export boundary after agreement on schema/reference points. This experiment does not implement the broader mobile/database/Celery/S3 architecture.

## Branches, reviews and merges

1. Use a feature branch in the shared team repository, such as `aadi-yolo-player-tracking`. Preserve teammates' local work; no routine personal fork is needed.
2. Keep commits focused. Stage intended source/tests/docs/lockfiles explicitly; exclude recordings, weights, output, virtual environments and secrets.
3. Before review, explain behavior, run checks, inspect the diff, and list failures/limits. Distinguish software tests from model evaluation and link real evidence.
4. Open a PR against the team's agreed integration branch. Obtain teammate review of shared contracts/architecture, address comments and rerun affected checks. Reviewer count and merge authority remain team decisions.
5. Push and merge only when authorized. Neither has been requested or performed for this prototype.

## CI and local checks

Proposed CI baseline from `experiments/player-tracking-yolo/`: Python 3.12, `uv sync --frozen`, `uv run pytest -q`, `uv run ruff check .`, and `uv run ruff format --check --quiet .`. Dependency installation needs network/cache access; tests themselves do not need networks, weights or real recordings.

No GitHub Actions workflow or branch protection was configured in this task. The team must add and verify these checks before calling CI adopted. Model/browser/hardware and labeled-accuracy checks remain separate evidence with footage provenance, versions/settings and limitations. The browser script is opt-in because it needs footage, weights, a running server and Chromium.

Track bugs (including far-side ID fragmentation), owners, and acceptance criteria in the team's GitHub Project. Link the [tracking notes](yolo-player-tracking.md). Agree Liam's contract before asserting cross-model compatibility, and obtain the team's Figma flow before claiming all screens complete.
