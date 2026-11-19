# Frontend: mobile app (prototype)

Expo (React Native + TypeScript) app for the record → upload → analysis flow. For the prototype it runs in a desktop browser through react-native-web. The same screens can later be built for iOS.

## Run

Start the backend first (see `../backend/README.md`), then:

```powershell
cd frontend
npm install
npx expo start --web
```

The app opens at http://localhost:8081. In a desktop-width window it shows inside a phone frame with the **debug panel** beside it:

- **Jump to any screen**, including the error and empty variants (3.2, 3.4, 4.1b, 4.3).
- **Pick a scenario for the next recording**: normal, upload fails once, processing fails, or not enough data.
- **Reset demo data.**

In a narrow window, the debug panel opens from the small DEBUG button in the top-right corner. To hide it (for example, for a clean recording), start with `$env:EXPO_PUBLIC_DEBUG='false'`. To point at another API, set `EXPO_PUBLIC_API_URL`, which defaults to `http://localhost:8000`.

Checks: `npx tsc --noEmit`.

## Screens (Figma numbering)

| Route | Figma |
| --- | --- |
| `/` | 1.0 Dashboard / 1.0b published |
| `/drills` | 1.2 Choose a drill |
| `/drill/[drillId]` | 1.3 Drill instructions |
| `/drill/[drillId]/checklist` | 1.4 Readiness checklist (+ feed method) |
| `/record/camera` | 2.2 / 2.3 Camera check (static court; tap a check to simulate) |
| `/record/countdown` | 2.4 Countdown |
| `/record/recording` | 2.5 Recording (auto-stops at 60 s) |
| `/session/[id]/model` | Prototype-only vision model + clip selector (before upload) |
| `/session/[id]/upload-error` | 3.2 Upload error (retry, same session) |
| `/session/[id]/status` | 3.3 Upload & processing status (polls API) |
| `/session/[id]/processing-error` | 3.4 Processing error |
| `/session/[id]/results` | 4.1 Provisional profile / 4.1b Not enough data |
| `/session/[id]/attempts` | 4.2 Review attempts + 4.3 flag sheet |
| `/session/[id]/published` | 4.4 Assessment published |
| `/partners` | Dummy matches (section 5 placeholder) |

Where the Figma mockup and the SDP disagree, the app follows the SDP:

- 60 s recording cap and roughly 60 s turnaround.
- 20 feeds per drill.
- Minimum of 5 scored attempts per direction.
- Exclusions are only "invalid feed" or "uncertain".
- Drills are the proposal's candidates.
