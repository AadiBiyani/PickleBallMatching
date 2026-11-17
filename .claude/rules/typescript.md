---
paths:
  - "**/*.ts"
  - "**/*.tsx"
---

# TypeScript

- Strict TypeScript. No `any`. Data from outside the module arrives as `unknown` and is validated before use.
- Keep domain modules independent of the DOM and of fixtures so they can move into the React Native app later.
- Validation reports every problem with a readable field path and throws. It does not coerce, trim, or drop malformed entries.
- Keep calculation apart from formatting. Calculations keep full precision, and rounding happens only at display.
- An unavailable value is `null` and shows as `N/A`. It is different from `0`.
- Render supplied strings as text, never as HTML.
- Avoid runtime dependencies unless there is a clear need. Commit the lockfile and install with `npm ci`.
- Before calling work done, run the experiment's `npm test`, `npm run lint`, and `npm run typecheck`, plus `npm run build` and `npm run test:e2e` where they exist.
