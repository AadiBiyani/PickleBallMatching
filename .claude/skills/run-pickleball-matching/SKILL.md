---
name: run-pickleball-matching
description: Start, run, and drive the PickleBall Matching prototype (Expo web app in frontend/ + FastAPI backend in backend/). Use when asked to run or start the app or API, screenshot a screen, walk the record -> upload -> analysis flow, smoke-test the API, or run the backend tests.
---

The prototype is two processes. The FastAPI backend runs on :8000 and the Expo/React Native app is served to a browser on :8081. Agents drive the app with `.claude/skills/run-pickleball-matching/driver.mjs`, which runs headless system Chrome through `playwright-core`.

All paths are relative to the repo root. All commands are **Windows PowerShell 5.1**, the only platform this was verified on.

## Prerequisites

Already present on the dev machine where this was verified; nothing extra was installed system-wide:

- Node 24 (`node`, `npx`) and Python 3.15 (`python`).
- Google Chrome. Set `$env:CHROME_CHANNEL='msedge'` to use Edge instead.
- `git` is **not** on PATH in the agent shell. Use GitHub Desktop or ask the user to commit.

## Setup (once per clone)

```powershell
python -m venv backend\.venv; backend\.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt
npm install --prefix frontend
npm install --prefix .claude\skills\run-pickleball-matching
```

The last line installs the driver's only dependency (`playwright-core`). It uses system Chrome, so no browser download is needed.

## Start both servers

```powershell
New-Item -ItemType Directory -Force .run-logs | Out-Null
Start-Process -WindowStyle Hidden -WorkingDirectory backend -FilePath backend\.venv\Scripts\python.exe -ArgumentList '-m','uvicorn','app.main:app','--port','8000' -RedirectStandardOutput .run-logs\api.out.log -RedirectStandardError .run-logs\api.err.log
$env:CI='1'; Start-Process -WindowStyle Hidden -WorkingDirectory frontend -FilePath cmd.exe -ArgumentList '/c','npx expo start --web --port 8081' -RedirectStandardOutput .run-logs\web.out.log -RedirectStandardError .run-logs\web.err.log
foreach($u in 'http://localhost:8000/api/health','http://localhost:8081'){ $ok=$false; for($i=0;$i -lt 60;$i++){ try { if((Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 3).StatusCode -eq 200){$ok=$true;break} } catch {}; Start-Sleep 2 }; "$u up: $ok" }
```

`CI=1` stops Expo prompting, but it **also disables reload**: after editing app or backend code, stop and start again.

## Run (agent path): the driver

| command | what it does |
|---|---|
| `node .claude\skills\run-pickleball-matching\driver.mjs smoke` | API only, no browser. Resets data, then runs drills/models, upload fails once and the retry uses the same session ID, polls to completed, checks results, publishes. Prints PASS/FAIL; exits 1 on any FAIL. |
| `node .claude\skills\run-pickleball-matching\driver.mjs flow` | Full browser walk at 390×844: dashboard → drill → checklist → camera check → countdown → recording → model select → processing → results → attempts + flag → publish → partners. Then opens 3.2, 3.4 and 4.1b through the debug panel, then a 1280×900 desktop shot. About 2 minutes; prints `FLOW OK`. |
| `node .claude\skills\run-pickleball-matching\driver.mjs shot /drills --wait "Choose a drill"` | Screenshot one route. Add `--desktop` for the phone frame + docked debug panel layout. |

Screenshots land in `.claude\skills\run-pickleball-matching\shots\` (gitignored). `flow` clears the folder first. Each run prints the browser console error count; it should be `console errors: 0`. **Open the PNGs and look at them**: a pass only means the expected text appeared.

To reach a screen that needs a session in a given state, create one through the debug API, then `shot` its route:

```powershell
$s = Invoke-RestMethod -Method Post http://localhost:8000/api/debug/sessions -ContentType 'application/json' -Body '{"state":"completed","scenario":"insufficient_data"}'
node .claude\skills\run-pickleball-matching\driver.mjs shot "/session/$($s.id)/results" --wait "NOT ENOUGH DATA"
```

`state` takes `awaiting_upload | processing | completed | failed | published`. `scenario` takes `normal | upload_error | processing_error | insufficient_data`.

## Stop

```powershell
foreach($p in 8000,8081){ Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force } }
```

## Run (human path)

Run the same start commands, then open http://localhost:8081 in a desktop browser. Use the debug panel beside the phone frame to jump between screens.

## Test

```powershell
cd backend; .\.venv\Scripts\python.exe -m pytest -q; cd ..
cd frontend; npx tsc --noEmit; cd ..
```

Expected: `17 passed, 1 warning` (the warning is a Starlette/httpx deprecation, harmless), and tsc exits 0.

## Gotchas

- **PowerShell 5.1 writes UTF-8 with a BOM.** `Set-Content -Encoding utf8` / `ConvertTo-Json | Set-Content` on `frontend/package.json` broke Expo (`JsonFileError ... Unexpected token '﻿'`). Edit JSON with the editor tool, or write with `[IO.File]::WriteAllText(path, text, (New-Object Text.UTF8Encoding $false))`.
- **Expo Router keeps earlier screens mounted but hidden.** `getByText('X').last()` can resolve to a hidden copy and time out ("locator resolved to hidden"). The driver always filters `locator('visible=true').first()`; do the same when extending it.
- **Text split across nested `<Text>` doesn't match exactly.** The model card renders "Simulated tracker" plus a nested "v0.1.0", so `getByText('Simulated tracker', {exact:true})` never matches. Wait on a sibling line ("UI prototype") instead.
- **Routes compile lazily.** The first visit to a route can take more than 10 s, so the driver uses 30–60 s waits on first navigation.
- **React Native 0.88 removed `StyleSheet.absoluteFillObject`.** tsc error TS2551; write `position:'absolute', top:0, right:0, bottom:0, left:0`.
- **On web, combining `flex: 1` (base) with `flex: 0` (override) collapses the element's width to 0.** This happened to the phone frame. Use separate style objects instead of overriding flex.
- **Demo randomness is seeded per session ID.** Results differ each run. Only the `insufficient_data` scenario may produce "Not enough data"; the other scenarios are capped so every direction keeps ≥5 scored attempts.
- **Data is in memory.** Restarting the backend wipes sessions and profiles. `smoke` and `flow` reset it anyway.

## Troubleshooting

- **`JsonFileError: Error parsing JSON: ﻿{` on `expo start`**: BOM in `package.json`. Rewrite it without a BOM (see Gotchas).
- **`ConfigError: Cannot determine the project's Expo SDK version because the module 'expo' is not installed`**: `npm install --prefix frontend` was not run.
- **Code changes don't show up**: Expo was started with `CI=1` (no watch) and uvicorn without `--reload`. Run Stop, then Start.
- **`smoke` FAIL on `results ... scored`**: a scenario other than `insufficient_data` came back insufficient. That was a real bug (fixed in `backend/app/pipeline.py`); if it reappears, check the `excludable` cap in `simulate_attempts`.
- **Upload-error screen opened from the debug panel, and the first Retry fails too**: fixed in `/api/debug/sessions`, which now records the first failed attempt. Restart the backend if it is still running old code.
