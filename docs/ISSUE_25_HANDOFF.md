# Issue #25: real JPEG dataset investigation and execution handoff

Prepared on 2026-10-26. Issue: https://github.com/gianfrancodp/dpr360/issues/25

Follow-up execution and actual results: [real JPEG validation report](ISSUE_25_VALIDATION.md). This document retains the original assignment and findings; the validation report records completed checks and remaining photographic limitations.

## Assignment

Fix and validate the existing JPEG input implementation against the supplied real dataset. Start from commit `6c24302` (`Add JPEG panorama input support`), which is already present in this checkout. Do not implement the feature again from scratch. Keep the TIFF-based downstream architecture and existing DNG development through RawTherapee.

The user will decide when to close the issue. Keep it open. Repository documentation, commits, and GitHub messages must be in English. This handoff is preparation, not proof that end-to-end stitching works. No agent has been dispatched by this preparation task.

## Local layout and confirmed dataset facts

The workspace contains `githubrepo/dpr360` (the Git repository) and sibling `test_data` (private input). Set the application source folder to `test_data/010_0284`, **not** its parent: scanning is intentionally nonrecursive.

| Property | Observed value |
| --- | --- |
| Files | 33 JPEGs, `PANO_0001.JPG` through `PANO_0033.JPG`, no gaps |
| Total source bytes | 305,475,584 (about 291.3 MiB) |
| Dimensions | 4032 x 3024 for every frame |
| Camera Model tag | `FC8282` on all 33 files; do not assume the existing Air 3 RAW profile |
| Focal length | 6.72 mm on all 33 files |
| Orientation | EXIF orientation 1 on all 33 files |
| Integrity | All 33 images fully decoded with Pillow 12.3.0 |
| DJI angles | Gimbal yaw, pitch, roll and flight yaw present in all 33 files |
| Calibration | Calibrated focal length, calibrated optical centers, DewarpData and DewarpFlag absent in all 33 files |
| Other metadata | Capture timestamps, focal length equivalent, GPS latitude and longitude present in all 33 files |

Pitch observations describe four groups of eight frames around -60, -25, +10 and +45 degrees, plus one approximately downward frame at -89.8 degrees. Yaw samples span the circle. These observations suggest a spherical capture, but do not prove sufficient overlap, stitch quality, or complete zenith coverage.

ExifTool `-n` still returns positive DJI angles such as `"+44.90"` as strings, while some negative values are JSON numbers. Convert through `float()` with validation if numeric processing is added; current geometry uses Hugin control points and does not require an Auto-Geometry rewrite.

The separate HTML file `DJI_20261026143755_0283_D.html` is a 216-byte redirect to `../PANORAMA/010_0283/`. That target differs from `010_0284`; it is neither an image nor an authoritative manifest for this set. Do not follow it automatically or include it as an input frame.

Do not commit source photos, generated full metadata, GPS values, contact sheets or rendered panoramas. Store run artifacts outside the Git checkout, e.g. workspace `test_runs/issue25/<new-run-id>/`.

## P0: confirmed blocker in JPEG preparation

The existing `prepare_jpeg()` in `dpr360/pipeline/steps/raw_conversion.py` fails on each tested real frame: `PANO_0001.JPG`, `PANO_0017.JPG`, and `PANO_0033.JPG`.

Observed exception:

```text
RuntimeError: Error setting from dictionary
```

Associated libtiff diagnostic:

```text
Bad LONG8 or IFD8 value 18446744073709551615 for EXIFIFDOffset tag 34665 in ClassicTIFF.
Tag won't be written to file.
```

The code passes `image.getexif()` directly to Pillow's compressed TIFF writer. The real EXIF contains a structure not exercised by the existing synthetic focal-length-only test. The message points at EXIF directory serialization; the exact underlying Pillow/libtiff mechanism still needs isolation. Do not claim that source JPEG corruption caused it: all sources decode.

Confirmed control experiment: the first frame saved and fully reopened as a 4032 x 3024 RGB TIFF with the same `tiff_deflate` compression after creating a fresh pixel-only image. Its original root EXIF includes IFD pointer tags 34665 (EXIF) and 34853 (GPS). This isolates the failure to metadata handling rather than JPEG decoding or TIFF compression. It does **not** justify discarding all metadata as the final fix. The three application-helper failures were reproduced in two separate diagnostic runs.

Reproduce from the repository root (PowerShell):

```powershell
$repo = (Get-Location).Path
$workspace = Split-Path (Split-Path $repo -Parent) -Parent
python (Join-Path $workspace 'test_data/analyze_issue25.py')
```

The supplied local diagnostic script inspects selected metadata, fully decodes all frames, exercises the **current application helper** on three samples using temporary outputs, and prints sanitized aggregate results. It does not modify input photos. It also performs a pixels-only TIFF control experiment. It needs Pillow and ExifTool on PATH; raw metadata values containing GPS are not printed. Conversion exceptions are recorded in output, so exit code 0 alone does not mean this check passed. Inspect `conversion_samples`.

### Required implementation sequence

1. Reproduce the error before editing production code. Record Python, Pillow and ExifTool versions. Preserve source inputs.
2. Isolate TIFF pixel encoding from EXIF serialization. Compare a fresh image without EXIF to the current helper. Inspect EXIF IFD structure locally without publishing private metadata.
3. Implement deliberate TIFF-safe metadata handling. Avoid blindly reusing JPEG EXIF directory offsets. Preserve the actual focal length, 35mm equivalent, make/model and orientation semantics needed by Hugin; preserve ICC when present. Ensure source metadata JSON/CSV remains available independently. A fallback that silently drops all lens metadata is insufficient.
4. Apply EXIF orientation exactly once and ensure serialized dimensions/orientation describe the output pixels. Original orientation=1 in this dataset does not exercise rotation; cover another orientation synthetically.
5. Make output creation atomic. Save to a temporary sibling, validate that it can be reopened/decoded, then replace the final TIFF. Clean up only the temporary file created by the current call on failure. Current code skips any existing TIFF with a matching stem, even if a failed attempt left a partial file.
6. Add meaningful synthetic regression tests using nested EXIF IFDs, not user photos or GPS. Verify the failing structure, readable TIFF pixels, lens metadata as interpreted by ExifTool/Hugin when available, and absence of a reusable partial output after failure. Do not make the test pass merely by relaxing assertions.
7. Retest all 33 JPEGs through the production step. Verify one readable RGB working TIFF per frame, source dimensions preserved, and relevant metadata on first/middle/last outputs using ExifTool. Expect 8-bit JPEG-derived information, not restored RAW dynamic range.

## P1: validate integration after preparation works

Use a fresh project directory for every independent experiment. Existing TIFFs and saved checkpoints can conceal conversion errors. Working JPEG TIFFs belong in `02_tiff/jpeg`; DNG TIFFs retain the legacy directory. Preserve `raw_conversion` step ID because later prerequisites reference it.

Use the application UI or a small local runner built from these existing APIs:

```python
from dpr360.models import PipelineContext
from dpr360.logger import UsageLogger
from dpr360.settings import load_config
from dpr360.tools import detect_tools
from dpr360.pipeline import PipelineRunner, ALL_STEPS
```

Read their current signatures before constructing the runner. Supply source, new project, detected tools, config and logger; call `ctx.ensure_dirs()` then `runner.run_all(resume=False)`. Persist step results/timings locally. Stop at the first failure and inspect it before rerunning. Do not bypass a failed prerequisite or change projection/blending defaults to manufacture success.

Tool observations on this machine: Python 3.11 and Pillow 12.3.0 are available; ExifTool is on PATH. Hugin is installed under `C:\Program Files\Hugin\bin`, containing `pto_gen`, `cpfind`, `cpclean`, `autooptimiser`, `pano_modify`, `nona`, and `enblend`. These Hugin executables were not found on PATH by the initial check. Prefer the existing `detect_tools()` discovery and verify actual executable versions. RawTherapee is not required for JPEG projects. The old temporary validation venv no longer exists; `pytest` is absent from the default Python.

Set up an isolated environment if needed:

```powershell
python -m venv .venv-issue25
& ./.venv-issue25/Scripts/python.exe -m pip install -r requirements-dev.txt
& ./.venv-issue25/Scripts/python.exe -m pytest -p no:cacheprovider
```

On this SMB checkout Git status emitted `unable to open '.git/sequencer/todo': Function not implemented`. Read-only Git log/diff and directory inspection worked; a sequencer directory was not listed. Treat this as an environment observation, not proof of an active cherry-pick/rebase. Never delete `.git` files to resolve it. If filesystem behavior prevents reliable tests, use an explicitly identified local checkout, preserving user changes and recording which checkout is authoritative.

### Integration checks and acceptance gates

- Metadata step extracts 33 records to full JSON and CSV. Real DJI orientation fields are present; missing calibration fields must not stop Hugin geometry.
- PTO generation includes exactly the current 33 TIFFs, no unrelated files. Verify inferred lens FOV against source metadata; lost focal metadata must not silently produce an arbitrary lens.
- Control-point search, cleaning, optimisation and PTO normalization complete with exit code 0. Record warnings.
- PTO is equirectangular, 360 x 180 degrees, and an exact full-canvas 2:1 geometry before Nona.
- Nona produces exactly 33 levels. Enblend uses the validated full canvas and horizontal wrap. Final TIFF decodes and has exact 2:1 dimensions.
- Record actual alpha coverage independently of geometry. No alpha channel means coverage unknown, not 100%. Do not promise complete sky from frame count alone. Visually inspect horizon, architectural edges, seams, exposure discontinuities, wrap seam and zenith/nadir holes on a downsampled preview.
- Resume skips genuinely successful work and can retry interrupted preparation without reusing a partial TIFF.
- DNG regression tests and mixed-folder DNG preference still pass. There are no DNG samples in this dataset, so real DNG end-to-end validation is not demonstrated by a synthetic test.
- UI shows JPEG and 33 frames; JPEG tool readiness does not require RawTherapee. Smoke test must process the selected file, not a stale TIFF from the shared smoke output folder.

## Secondary risks identified by code inspection

These are not all demonstrated failures in this dataset. Address directly related correctness issues with targeted tests; avoid unrelated architecture work.

- `PipelineRunner` identity is source path plus format only. Replacing images at the same path can retain completed checkpoints, and changing source directory still allows same-stem TIFF reuse. Define manifest/invalidation semantics or enforce a new project when sources change.
- `RawConversionStep` currently accepts any matching TIFF without freshness/readability validation. Atomic writes and explicit source identity prevent false resume success.
- `list_working_tiffs()` can map multiple same-stem JPEGs to one TIFF (e.g. `frame.jpg` and `frame.jpeg`). Reject ambiguous source stems clearly; do not silently duplicate one image.
- `smoke_test()` selects the first TIFF in a reusable shared directory. Select the actual current output explicitly and avoid stale cross-format reuse.
- Current DJI warnings only check missing orientation values, not all optional calibration metadata or malformed numeric strings. Do not expand into metadata-driven geometry as part of this JPEG fix.

## Finish and report

Deliver the fix, regression coverage, and an English local test report containing commands, versions, counts, step timings, exceptions/warnings, final dimensions, actual coverage status, and visual findings. Clearly separate tests actually run from pending checks. The previous `25 passed` result was historical synthetic-suite evidence; it did not prove real JPEG conversion.

Before a commit, inspect current changes and preserve unrelated work. Follow the user's existing instruction: commit only validated work, keep issue #25 open and retain/add `To be tested` when reporting the implementation. Do not close the issue on the basis of unit tests. Push/publication is a separate action and must follow the current user's authorization. Never publish private dataset artifacts with an issue comment or commit.
