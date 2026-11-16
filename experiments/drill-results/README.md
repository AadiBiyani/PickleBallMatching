# Drill results summary experiment

A small browser demo for Personalized Doubles Partner Coordination. It presents supplied attempt labels and explains which attempts contribute to a drill's success rate. **Every selectable session is synthetic sample data. No video was recorded or analyzed for this demo.**

This experiment supports the results-review portion of SYS-05 / FR-10 / FR-12. It does not implement the full mobile application, a vision pipeline, coverage estimation, or partner recommendations.

## Run locally

Use Node.js 24.x or 26+ with npm (Node 22.x starting at 22.13 is also supported by the locked tools). From the repository root:

```sh
cd experiments/drill-results
npm ci
npm run dev
```

Open the local URL Vite prints, normally `http://127.0.0.1:5173`. Stop the server with Ctrl+C. No account, API keys, database, or uploaded recordings are needed.

## Validate

From `experiments/drill-results/`:

```sh
npm test
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright's browser install is needed once per machine (and again after browser-version updates). Browser tests start and stop a local server on port 4173 and test the production build, so run `npm run build` first. Port 4173 must be available. `npm run test:watch` runs unit tests interactively. `npx playwright show-report` opens the last browser-test report.

To inspect the production build yourself, run `npm run preview` after building. `dist/`, installed dependencies, and generated Playwright reports are ignored by Git.

## Data contract and integration boundary

`src/domain/drill-results.ts` is independent of the browser and fixtures. `analyzeSession(input: unknown)` validates the complete input before returning `{ session, summary }`. Invalid data throws `SessionValidationError` with readable field paths in `issues`; it never returns a partial summary or drops malformed attempts.

Session fields:

- `sessionId`: nonblank string, unique for the session.
- `drillName`: nonblank string.
- `recordedAt`: valid ISO timestamp with seconds and an explicit `Z` or numeric timezone offset.
- `dataSource`: nonblank source string; every example uses `sample`.
- `attempts`: array of attempt objects, including an empty array.

Attempt fields:

- `attemptId`: nonblank string, unique within that session; IDs can repeat in separate sessions.
- `outcome`: exactly `successful`, `unsuccessful`, `invalid_feed`, or `uncertain`.
- `exclusionReason`: required nonblank string for `invalid_feed` and `uncertain`. If present on another outcome, it must also be a nonblank string.

Additional fields are tolerated for future API metadata. The validator does not trim or coerce supplied values. Uniqueness across stored sessions is the future persistence layer's responsibility; this experiment checks that its fixture IDs are unique.

Calculation rules:

```text
total = attempts.length
scored = successful + unsuccessful
excluded = invalid_feed + uncertain
success rate = scored > 0 ? successful / scored * 100 : null
```

`src/format.ts` formats a percentage with at most one decimal place. The calculation retains full numeric precision. Zero scored attempts is unavailable (`N/A`); scored attempts that all fail produce `0%`. Dates display in UTC so the synthetic recording time is unambiguous.

The page imports examples only from `src/fixtures/sessions.ts`. A future API adapter can pass its response through the same domain function. The DOM page would need adaptation for the planned React Native application; no backend or native-device integration is claimed here.

## Examples and controls

The example selector includes mixed results, all successful, all unsuccessful, all excluded, empty, rounding, and deliberately invalid input. Every example is labeled as sample data. The mixed example preserves the assignment's supplied fields and exclusion reasons exactly.

The outcome filter changes only the attempt list. It resets to “All outcomes” when switching sessions. Empty sessions and filters with no matches have distinct messages. Invalid input replaces the results with field-specific errors; choosing another example recovers the page.

The unscorable and empty examples test unavailable results without inventing sample-size or confidence thresholds. Attempt labels come from the input; this page does not judge whether a pickleball return was actually successful.

## Planning and validation record

See [the implementation notes](../../docs/drill-results-notes.md) for the approved scope, acceptance cases, decisions, actual validation results, and known limitations.

Browser tests save mixed-results, all-excluded, invalid-data, and narrow-screen screenshots in `test-results/`. These generated files and the HTML test report are local artifacts and are not committed.

The dependency audit reports seven moderate findings tracing to one `minimatch` advisory in the TypeScript ESLint development dependency chain. There are no runtime package dependencies. The proposed automatic remediation downgrades the lint tooling; it has not been applied. See the implementation notes for details.
