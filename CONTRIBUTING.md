# Contributing to DPR360

Thank you for helping improve DronePanoRAW 360.

## Project principles

DPR360 is free and open source, local-first, RAW-first, and designed for drone photographers. Changes should preserve reproducibility, diagnostic transparency and the integrity of the 16-bit technical master.

## Development setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

The unit tests do not require RawTherapee/Hugin/ExifTool. End-to-end panorama tests do.

## Pull requests

- Keep changes focused.
- Add or update tests for behavior changes.
- Do not silently change panorama geometry or blending defaults without before/after validation.
- Do not add remote telemetry, cloud uploads or persistent device/user identifiers without an explicit project decision.
- Avoid copying code from repositories with unclear/incompatible licenses.
- New dependencies require a license review.

## Test data and privacy

Do **not** commit user photographs, GPS coordinates, camera serials, usernames, absolute local paths or raw diagnostic logs. Small synthetic fixtures are preferred. If a real panorama is needed for validation, keep it outside the public repository unless its publication rights and privacy implications are explicit.

## Commit style

Clear imperative messages are preferred, for example:

```text
Fix full-canvas Enblend output
Add PTO geometry regression test
```
