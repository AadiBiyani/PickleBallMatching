# Agent guide

This file is the entry point for working in this repo. Long project documents live in `docs/` and are read on demand.

## What this project is

Personalized Doubles Partner Coordination: the ECE 49595 senior design project of Team 2 at Purdue (Aadi Biyani, Nishaant Shah, Liam He, Logan Hanson). A player records standardized individual pickleball drills on an iPhone. A server pipeline turns the video into court-coordinate movement and attempt outcomes, builds a coverage profile, and ranks complementary doubles partners with an explanation.

**Current stage: prototyping.** There is no application code yet. Work happens as small self-contained prototypes under `experiments/`. The production stack in the proposal (React Native, FastAPI, Celery, PostgreSQL) is a plan. Do not scaffold it unless asked.

## Read before you decide

Open the file that matches the task. Leave the others closed.

| When | Read |
| --- | --- |
| Product summary, data flow, planned stack, scoring and matching rules | `docs/project-brief.md` |
| Requirement IDs, thresholds, test methods, open instructor feedback | `docs/requirements-index.md` |
| Exact wording of a requirement, deliverables, standards | `docs/software-development-plan.md` |
| Stakeholders, competitive analysis, full proposal text | `docs/project-proposal.md`, lines 1-345 only |
| The VLM comparison harness | `docs/vlm-harness-notes.md` |
| What an experiment does and how to run it | that experiment's `README.md` |

`docs/project-proposal.md` ends with two embedded base64 images (line 346 onward, about 170 KB). Never read the whole file. It also carries revision markup: `~~struck~~` text was deleted from the proposal and is not current.

## Repo layout

```
AGENTS.md, CLAUDE.md      agent instructions (CLAUDE.md imports this file)
.claude/                  Claude Code settings, rules, skills, subagents
docs/                     project documents and per-experiment notes
experiments/<name>/       one self-contained prototype each
```

## Working in this repo

- Treat `docs/project-proposal.md` as the source for what the product is and who it is for, and `docs/software-development-plan.md` as the source for requirements and sequencing. The brief and the index are summaries. If they disagree with the source documents, the source wins and the summary gets fixed.
- Change the two submitted course documents only when asked. They are records of what was turned in.
- **Experiments are isolated.** Each has its own folder, `README.md`, dependency file, and tests. Do not import code from another experiment or add package files at the repo root. To reuse something, copy it and say where it came from.
- **Trace work to requirements.** Name the FR / NFR / SYS IDs an experiment supports in its README and in the pull request. Claim only what was built and tested, and say what is not covered.
- **Attempt outcomes** are exactly `successful`, `unsuccessful`, `invalid_feed`, `uncertain`. Scored attempts are successful plus unsuccessful. `invalid_feed` and `uncertain` are excluded from scoring and keep an exclusion reason. With zero scored attempts the rate is unavailable, not 0. Never force an uncertain observation into a success or a failure.
- **Units go in the name**: `x_ft`, `x_m`, `time_s`. The player-tracking experiment reports court positions in feet. NFR-06 is stated in meters. Convert explicitly.
- **Synthetic data is labeled synthetic** in the data, the UI, and the README.
- Keep new always-on instructions in this file, and keep them short. Put longer reference material in `docs/`.

## Data and secrets

- Never commit videos, extracted frames, or anything that identifies a participant. Recordings stay outside Git.
- Secrets live in a local `.env` that is never committed. `.env.example` lists the variable names.
- Send footage to a third-party model API only when everyone visible in it has agreed to that use. SYS-08 requires consent and private footage.

## Verifying work

- Run the checks the experiment's README documents. Report what actually happened, including failures and anything you could not run.
- Record the plan, acceptance cases, and observed results in `docs/<experiment>-notes.md`.
- Accuracy claims need labeled ground truth that was not used for tuning. A missing estimate counts as missing. It is never dropped to improve a metric.

## Git

- Work on a branch named `<firstname>-<topic>`, for example `liam-test-harness`. Changes reach `main` through pull requests.
- Use Conventional Commit subjects: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Do not push, force-push, or rewrite history unless asked.
