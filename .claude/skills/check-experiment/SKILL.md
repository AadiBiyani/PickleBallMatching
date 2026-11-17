---
name: check-experiment
description: Run an experiment's documented validation commands and report the actual results. Use before committing, before opening a pull request, or when asked whether an experiment still passes.
argument-hint: "[experiment-name]"
---

# Check experiment

1. Pick the experiment. Use `$ARGUMENTS` if given. Otherwise find the `experiments/<name>/` folders touched by `git status` and `git diff --name-only main...HEAD`. If more than one is touched, check each.
2. Read that experiment's `README.md` and find its validation section. Those commands are the source of truth. Do not substitute your own.
3. Run each command from inside the experiment folder, in the documented order. Typical sets:
   - Node: `npm ci` if `node_modules` is missing, then `npm test`, `npm run lint`, `npm run typecheck`, `npm run build`, `npm run test:e2e`
   - Python: `python -m unittest discover -s tests -v`, or `python -m pytest` if the README says so
4. Also run `git diff --check` for whitespace errors.
5. Report a table of command and observed result, with test counts where shown. Include:
   - anything that failed, with the relevant output
   - anything you could not run, and why (missing browser, model download, video file, display, API key)
   - the OS and runtime versions
6. Do not fix failures unless asked. Do not describe a check as passing if it did not run.
7. If the user wants the results kept, add them to `docs/<experiment>-notes.md` under the validation results.
