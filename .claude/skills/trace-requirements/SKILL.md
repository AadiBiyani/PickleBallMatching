---
name: trace-requirements
description: Map the current changes to the project's FR, NFR, and SYS requirement IDs and say what evidence supports each. Use when writing a pull request description, a README requirements section, or the traceability matrix for deliverable D-05.
---

# Trace requirements

1. Get the change set: `git diff --stat main...HEAD` plus uncommitted changes from `git status`.
2. Read `docs/requirements-index.md`. Open `docs/software-development-plan.md` only for the exact wording of a requirement you are about to cite.
3. For each requirement the change touches, produce one row:

   | Requirement | What this change does for it | Evidence | Not covered |
   | --- | --- | --- | --- |

   - **Evidence** is a test file and test name, a documented manual check, or a measured result with its dataset. A file that merely exists is not evidence.
   - **Not covered** names the parts of the requirement's test method that this change does not satisfy.
4. Flag these problems:
   - a README or notes file that claims a requirement the code does not support
   - a threshold from the index reported as met without a measurement on held-out data
   - synthetic data that is not labeled as synthetic
   - behavior that contradicts the scoring rules in `AGENTS.md`
5. Give a short summary the user can paste into a pull request: requirements supported, requirements partly supported, and explicit non-claims.

Use IDs exactly as written, such as `FR-10` and `NFR-06`. Do not invent requirement IDs. If a change fits no requirement, say so.
