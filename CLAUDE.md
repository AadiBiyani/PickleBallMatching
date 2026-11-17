# CLAUDE.md

@AGENTS.md

## Claude Code specifics

The shared instructions are in `AGENTS.md`, imported above, so every coding agent the team uses reads the same rules. Add new always-on rules there. Keep this file for things only Claude Code uses.

- **Path-scoped rules** are in `.claude/rules/`. They load only when a matching file is opened.
- **Skills**
  - `/new-experiment <name>`: plan and scaffold a prototype under `experiments/`.
  - `/check-experiment [name]`: run an experiment's documented checks and report the real results.
  - `/trace-requirements`: map the current changes to FR / NFR IDs.
- **Subagents**
  - `requirements-reviewer`: checks a change against the requirements and the scoring rules.
  - `eval-reviewer`: checks evaluation code and reported metrics for methodology problems.
  Run the relevant one before opening a pull request.
- **Plan first.** Use plan mode before starting a new experiment or changing a data contract. The team agrees scope and acceptance cases before implementation.
- **Personal overrides** go in `CLAUDE.local.md` and `.claude/settings.local.json`. Both are gitignored.
