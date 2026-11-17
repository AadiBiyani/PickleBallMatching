---
name: new-experiment
description: Plan and scaffold a new self-contained prototype under experiments/. Use when starting a new experiment or prototype in this repo.
argument-hint: <experiment-name>
disable-model-invocation: true
---

# New experiment

Create `experiments/$ARGUMENTS/` following the repo conventions. If no name was given, ask for one in kebab-case.

## 1. Plan before writing code

1. Read `AGENTS.md`, `docs/requirements-index.md`, and any existing `docs/$ARGUMENTS-notes.md`.
2. Look at an existing experiment's README, if one is present on this branch, to match its structure.
3. Propose to the user:
   - the question the experiment answers and what it leaves out
   - the requirement IDs it supports, and which parts of them it does not cover
   - the language and tools, with a reason for any dependency
   - the data contract at its boundary
   - acceptance cases with expected values worked out by hand before implementation
4. Wait for approval. Do not create files before the user agrees to the scope.

## 2. Scaffold

Create only what the approved plan needs:

- `README.md`: what it is and is not, requirements supported, how to run, how to validate, the data contract
- a dependency file with bounded versions (`requirements.txt`, or `package.json` with a lockfile)
- `.gitignore` for generated output, models, and installed packages
- `tests/` with the acceptance cases as failing tests
- a line in `experiments/README.md`. Create that file if it is missing
- `docs/$ARGUMENTS-notes.md` with the approved scope and acceptance cases

## 3. Build and verify

1. Implement until the acceptance tests pass.
2. Run every documented check and record the real results, the environment, and any failures in the notes file.
3. Finish with the limitations: what the experiment does not establish.

Do not commit or push unless asked.
