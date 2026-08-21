# DronePanoRAW 360 (DPR360)

[![CI](https://github.com/gianfrancodp/dpr360/actions/workflows/ci.yml/badge.svg)](https://github.com/gianfrancodp/dpr360/actions/workflows/ci.yml)
[![Windows build](https://github.com/gianfrancodp/dpr360/actions/workflows/build-windows.yml/badge.svg)](https://github.com/gianfrancodp/dpr360/actions/workflows/build-windows.yml)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE)

**Pano Mode → RAW → 360°**

**Drone Panorama Mode RAWs → One 360° Master**

Free and open source. Local-first. **Designed by drone photographers, for drone photographers.**

DPR360 is a Windows-first RAW-to-360 workflow for reconstructing high-resolution spherical panoramas from the original RAW frames captured by a drone panorama sequence. The project prioritizes a 16-bit technical master, deterministic geometry checks, resumable processing, transparent diagnostics, and local processing.

> **Project status: alpha.** Version 3.2.1 is the first repository-ready DPR360 codebase and preserves the previously validated Hugin-based pipeline. The current default geometry backend still uses Hugin control points and optimisation. Metadata-driven Auto-Geometry is not yet part of this release.

## Why DPR360?

Drone panorama modes often create a convenient stitched JPEG while also saving the individual RAW/DNG frames. DPR360 is built for photographers who want to reconstruct the sphere from those original frames instead of giving up RAW latitude and high-bit-depth output.

The current validated workflow targets a **33-DNG DJI Air 3 spherical panorama dataset**, while the codebase is intentionally structured for additional supported panorama capture profiles in future releases.

## Current features

- RAW/DNG → 16-bit TIFF development through RawTherapee.
- Hugin project generation and control-point workflow.
- Full equirectangular **360° × 180°** normalization.
- Exact **2:1** full-canvas handling propagated to Enblend.
- Preventive PTO geometry validation before rendering.
- Nona remapping + Enblend blending.
- Final geometry and alpha-coverage validation as separate quality checks.
- Per-step execution, `RUN ALL`, checkpointing and `RESUME`.
- `completed_with_warnings` state for successful commands with diagnostic warnings.
- Weighted progress and live execution logs.
- Native Windows file/folder pickers with path-entry fallback.
- Privacy-conscious local JSONL logging with path/GPS/camera-ID redaction enabled by default.
- Tool discovery and Windows setup helpers for ExifTool, RawTherapee and Hugin.

## Processing pipeline

```text
DNG metadata
    ↓
RAW → TIFF 16-bit
    ↓
pto_gen
    ↓
cpfind --multirow --celeste
    ↓
cpclean
    ↓
autooptimiser
    ↓
360×180 / exact 2:1 project setup
    ↓
PTO geometry validation
    ↓
nona
    ↓
enblend (full canvas)
    ↓
final geometry + coverage validation
```

## Windows quick start — source distribution

### Requirements

- Windows 10/11
- Python 3.11+ recommended
- RawTherapee CLI
- Hugin command-line tools
- ExifTool

The setup helper can discover existing installations and can assist with installing missing tools.

### Install

1. Download or clone the repository.
2. Run `setup.bat`.
3. Run `run_dpr360.bat`.
4. Select the source DNG folder and a project/output folder.
5. Run the smoke test if this is the first installation.
6. Run the pipeline.

`setup.bat` invokes PowerShell with `-ExecutionPolicy Bypass` **for that process only**; it does not permanently alter the user's Windows execution policy.

## Project state

Checkpoints are stored inside the project folder:

```text
<project>/.dpr360/state.json
```

A successful step with warnings is treated as a completed prerequisite and remains visible as `completed_with_warnings`.

## Privacy

DPR360 is designed as a **local-first** application. Source photographs are processed on the user's machine. The application does not require a cloud account or upload images for processing.

By default, diagnostic logging omits command stdout and redacts local paths, GPS fields and camera identifiers. Logs should still be treated as potentially sensitive before public sharing. See [`docs/PRIVACY.md`](docs/PRIVACY.md).

Streamlit usage statistics are disabled in `.streamlit/config.toml` and in the Windows launcher.

## Build a Windows application package

The repository includes a PyInstaller build configuration and GitHub Actions workflow. The generated Windows package embeds the Python/Streamlit application but **does not bundle RawTherapee, Hugin or ExifTool**; those remain separately discovered/installed external tools.

Local build:

```powershell
py -3.13 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean dpr360.spec
```

See [`docs/BUILDING.md`](docs/BUILDING.md) and [`docs/RELEASING.md`](docs/RELEASING.md).

## Repository structure

```text
dpr360/                  processing core
  pipeline/              pipeline runner and steps
app.py                    Streamlit UI
launcher.py               frozen Windows application launcher
dpr360.spec               PyInstaller build specification
tests/                    regression/unit tests
.github/workflows/         CI, build, release and CodeQL
docs/                     architecture, privacy and release docs
```

## Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request. For bugs, use the issue templates and avoid posting photographs, GPS coordinates, serial numbers, local filesystem paths or unsanitized diagnostic logs publicly.

## License

DPR360 is licensed under **GPL-3.0-or-later**. See [`LICENSE`](LICENSE).

The source repository does not include RawTherapee, Hugin, Enblend or ExifTool binaries. These are independent upstream projects with their own licenses. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Independence statement

DronePanoRAW 360 / DPR360 is an independent open-source project. DJI and other manufacturer names may be used only to identify compatible cameras or panorama capture profiles. The project is not affiliated with, sponsored by, or endorsed by DJI or any other drone manufacturer.

## Author

**Gianfranco Di Pietro**<br>
https://gianfrancodp.github.io

Copyright © 2026 Gianfranco Di Pietro.
