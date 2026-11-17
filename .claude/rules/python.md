---
paths:
  - "**/*.py"
---

# Python

- Target Python 3.12. Start modules with `from __future__ import annotations` and add type hints to public functions.
- Open each module with a docstring that says what it does and what it deliberately does not do.
- Use frozen dataclasses for result records. Use named constants for court geometry and status strings.
- Install one OpenCV wheel only. `mediapipe` depends on `opencv-contrib-python`. Adding `opencv-python` or `opencv-python-headless` shadows it and breaks window support.
- Court positions are in feet on the court plane with the origin at the far-left outside corner: `x` from 0 to 20, `y` from 0 to 44. Put the unit in the name (`x_ft`, `time_s`) and convert to meters explicitly when checking NFR-06.
- A frame without an estimate keeps its row with empty coordinates and a status that explains why. Do not interpolate over it or drop it silently.
- Tests must run without a video file, a model download, a display, or a network. Put a fake at that boundary.
- Use the test runner the experiment already uses. `experiments/player-tracking` uses `python -m unittest discover -s tests -v`. A new experiment may choose pytest and must say so in its README.
- Read API keys from environment variables. Never hard-code a key, and never print one.
- Use `pathlib` or `os.path` for paths. The team develops on both Windows and macOS.
