# Drill results experiment: plan and validation

## Approved scope

The repository initially contained only documentation. After reading the project proposal and software development plan, the agent proposed a standalone TypeScript browser page, independent scoring/validation functions, synthetic fixtures, and unit/browser tests. The user approved the plan before implementation and changed its location from `apps/drill-results/` to `experiments/drill-results/`.

The page answers how many attempts were recorded, scored, successful, unsuccessful, or excluded; why each excluded attempt was omitted; and the success rate among scored attempts. It visibly identifies all examples as synthetic and makes no claim that a video was analyzed.

Acceptance criteria agreed before implementation:

- Validate all input before calculating; report malformed fields, unknown outcomes, duplicate attempt IDs, and missing exclusion reasons without returning partial results.
- Count all attempts, but include only `successful` and `unsuccessful` in the success-rate denominator. Preserve precision until display, with at most one decimal place.
- Use `null`/`N/A` for no scored attempts and `0%` for scored attempts that all fail. Distinguish an empty session from an empty filter result.
- Show session metadata, all four outcome counts, attempt IDs, and exclusion reasons. Filtering changes only the list; switching examples updates the session and resets the filter.
- Provide labeled keyboard controls, textual outcome labels, and a layout usable at 320px width.

Inference, video capture/upload, authentication, persistence, coverage estimation, confidence/skill scores, minimum sample thresholds, and matching are outside this experiment.

## Implementation decisions

- Use TypeScript, Vite, native HTML/CSS, Vitest, Playwright, and ESLint. There are no runtime package dependencies. The experiment has its own package and lockfile.
- The project proposal targets React Native and Jest for the eventual mobile app. This experiment retains TypeScript but uses a browser UI and Vitest. Its domain module is reusable; its DOM interface would need adaptation.
- Support the exclusion and results-review portions of SYS-05 / FR-10 / FR-12. Do not claim completion of FR-11's regional coverage thresholds, video evidence, or NFR-08's CI/merge protections.
- The plan's FR-10 example has six successes, two failures, and two exclusions; the user's primary example has three successes, one failure, and two exclusions. Both yield 75%; the supplied six-attempt example is preserved exactly.
- Keep fixtures separate from `analyzeSession(input: unknown)`. Runtime validation checks a complete session before calculating, including calendar-valid ISO timestamps and per-session unique attempt IDs.
- Show timestamps in UTC. Format percentages separately from calculations. Render supplied strings with `textContent`.
- Include the five required valid fixtures, a rounding fixture, and an explicitly invalid demonstration. Invalid input hides prior results and leaves the example selector available for recovery.

## Independent acceptance references

These values were hand-calculated in the task description before implementation.

| Input | Expected |
| --- | --- |
| 3 successes, 1 failure, 1 invalid feed, 1 uncertain | 6 total, 4 scored, 2 excluded, 75% |
| 2 successes | 2 scored, 100% |
| 3 failures | 3 scored, 0% |
| 1 invalid feed, 1 uncertain | 0 scored, 2 excluded, unavailable rate |
| No attempts | Zero counts, unavailable rate, empty message |
| 1 success, 2 failures | Full precision internally, 33.3% displayed |
| Unknown outcome, duplicate ID, missing/wrongly typed fields | Validation errors |

Browser checks additionally verify exact reasons, unchanged summaries under filtering, updated metadata/counts on session changes, invalid-data recovery, keyboard selection and focus, and a narrow layout without horizontal overflow.

## Actual validation results

Run commands from `experiments/drill-results/`. Full setup instructions are in [the experiment README](../experiments/drill-results/README.md).

| Command | Observed result |
| --- | --- |
| `npm test` | 75 tests passed across two files |
| `npm run lint` | Passed |
| `npm run typecheck` | Passed |
| `npm run build` | Passed; eight modules transformed |
| `npx playwright install chromium` | Browser installation succeeded |
| `npm run test:e2e` | Six tests passed; final run 2.7 seconds |
| `git diff --check` and new-file whitespace inspection | Passed |
| `npm audit --json` | Seven moderate development-tool findings; see below |

Environment: macOS ARM64, Node 26.3.1, npm 11.16.0, TypeScript 6.0.3, Vite 8.3.8, Vitest 5.1.0, Playwright 1.65.1, Chromium 159.0.8154.6. Browser tests used the production build. No pre-existing application checks were available.

Observed failures and corrections:

- The first unit-test run intentionally failed because implementation modules had not yet been written. The implemented functions subsequently passed all 75 assertions/tests reported by Vitest.
- Sandbox restrictions blocked package downloads and the local browser-test server; approved execution outside the sandbox resolved these environment failures.
- Five initial browser tests passed; the keyboard test failed with a popup-dependent ArrowDown/Enter sequence. Adding Space also failed. Native typeahead plus Tab navigation and visible-focus assertions passed, followed by a passing complete suite.
- Screenshot inspection found a clipped example label; shortening it and rebuilding produced a passing browser rerun and refreshed screenshots.
- A new-file whitespace helper initially misread Git's normal difference exit code as an error. Inspecting actual diagnostics confirmed there were no whitespace issues.
- Dependency-engine inspection corrected the original Node minimum to `^22.13.0 || ^24.0.0 || >=26.0.0`, matching the locked tools' supported versions.

## Limitations

All examples are synthetic. Validation does not establish model accuracy, real player performance, native iPhone compatibility, Safari/Firefox behavior, or screen-reader usability. GitHub Actions and branch protection are not configured by this experiment.

The audit's seven moderate package-level findings trace to one [minimatch globparts-amplification advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249) in the TypeScript ESLint development dependency chain. npm proposes a downgrade of `typescript-eslint` to 8.36.0; neither that downgrade nor an untested major transitive override was applied. No runtime package dependencies are shipped with the page.
