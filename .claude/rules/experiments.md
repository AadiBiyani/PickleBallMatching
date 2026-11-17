---
paths:
  - "experiments/**"
---

# Experiments

- One folder per experiment, runnable on its own. It has its own `README.md`, dependency file (`requirements.txt`, or `package.json` with a lockfile), ignore rules for generated output, and `tests/`.
- No imports from another experiment. No shared code at the repo root. If you copy code from another experiment, say so in the README.
- The README states what the experiment is and is not, the requirement IDs it supports, how to run it, how to validate it, and the data contract at its boundary.
- List each experiment in `experiments/README.md` with a one-line description.
- Keep the domain logic (scoring, geometry, metrics) free of I/O, UI, and model calls so it can be tested without a video, a network, or a display.
- Validate input at the boundary. Reject malformed input with a readable error. Never return a partial result from bad data.
- Generated output goes in a gitignored `output/` folder. Model files are downloaded on first use. Neither is committed.
- Run commands from inside the experiment folder, as its README says.
- Pin or bound dependency versions and note the OS and runtime versions the experiment was tested with.
