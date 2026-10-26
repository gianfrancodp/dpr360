# Issue #25: real JPEG validation

Date: 2026-10-26. Baseline: `6c24302`. Dataset and rendered artifacts remain private and are not part of this repository.

## Fix and regression coverage

The original helper failed on three tested real DJI JPEGs with `RuntimeError: Error setting from dictionary` and an invalid `EXIFIFDOffset` warning from libtiff. All 33 source JPEGs decoded correctly, and a pixels-only compressed TIFF control succeeded. The defect was source EXIF serialization, not source pixel corruption.

Preparation now writes a fresh RGB TIFF with lossless compression, then uses the already-required ExifTool to rebuild selected photographic EXIF. Numeric copying retains the source focal length exactly (6.72 mm, 24 mm equivalent). Orientation is applied once and normalized, output dimensions are updated, and any source ICC profile is retained. JPEG IFD offsets, MakerNotes, and GPS are not transplanted; complete original metadata remains in the private JSON/CSV exports.

The result is validated and atomically replaces the destination. A failed preparation preserves an existing destination and removes its temporary file. Reuse requires a readable canonical TIFF and matching source path, size and mtime. Checkpoints include the selected source manifest; the manifest is metadata-based, not a content hash. Ambiguous same-stem JPEG inputs are rejected. The smoke test selects the current image instead of an unrelated stale TIFF.

The real run also exposed disconnected Hugin alignment despite a valid canvas. PTO validation now reports control-point connectivity independently of 360 x 180 / exact 2:1 geometry. This is a warning requiring review, not an automatic repair or a change to stitching defaults. Saved warnings survive `RESUME`.

The automated suite includes nested EXIF, nontrivial orientation, exact focal precision with real ExifTool, pixel/ICC preservation, atomic failure cleanup, corrupted/replaced cache regeneration, duplicate stems, checkpoint invalidation, warning retention, stale smoke outputs, DNG command compatibility, and JPEG UI readiness without RawTherapee.

Result: **36 passed** (full suite, including the real ExifTool integration). Environment: Windows, Python 3.11.0rc2, Pillow 12.3.0, pytest 9.1.1, Streamlit 1.63.0, ExifTool 13.59, Hugin/Nona 2025.0.1. The same private diagnostic script used before the fix now successfully converts the first, middle and last samples without the libtiff EXIF error.

## Real preparation and smoke checks

- 33 consecutive JPGs, 305,475,584 source bytes; every frame is 4032 x 3024.
- Camera tag: DJI `FC8282`; no DNG frames were provided.
- 33 metadata records and 33 fully decoded RGB working TIFFs, totalling 833,469,992 bytes.
- First, middle and last TIFFs retain make/model, 6.72 mm focal length, 24 mm equivalent and orientation=1, matching the original values.
- Hugin initially recognizes 33 images and an HFOV of 71.591518 degrees, consistent with the retained 35mm equivalent and aspect ratio.
- A real smoke test succeeds on the middle source frame with a deliberately unrelated TIFF already present in the smoke folder; the PTO references the requested current frame.

Private reproducible scripts live beside the local dataset: `analyze_issue25.py`, `run_issue25.py`, `verify_issue25.py`, and `audit_issue25.py`. From the repository, the dataset directory is `../../test_data/010_0284`. Use a fresh project for a new full run. The existing HTML redirect points to a different panorama and is not an input manifest.

Example commands (PowerShell, substitute an available Python environment):

```powershell
python -m pytest -p no:cacheprovider
python ../../test_data/run_issue25.py --project <new-local-output-directory>
python ../../test_data/verify_issue25.py --project <same-output-directory>
python ../../test_data/audit_issue25.py --project <same-output-directory>
```

The last command rechecks current PTO diagnostics and verifies that `RESUME` skips completed steps and preparation reuses verified TIFFs without changing their mtimes.

## Full pipeline run and final audit

Every production step completed with exit code 0 using the existing geometry and blending defaults. The full run took approximately 17 minutes 32 seconds; output artifacts were written to a new local project directory, with original JPEGs read from the network share.

| Step | Seconds |
| --- | ---: |
| Metadata | 24.813 |
| JPEG preparation | 134.469 |
| PTO generation | 0.532 |
| Control-point search | 157.046 |
| Control-point cleaning | 0.422 |
| Optimisation | 55.234 |
| Panorama setup | 0.265 |
| Initial PTO validation | 0.016 |
| Nona remapping | 71.672 |
| Enblend | 605.016 |
| Final validation | 2.296 |

Nona produced 33 remapped TIFFs (1,323,047,088 bytes). Enblend 4.3-993fd4822e8d produced a readable **18650 x 9325 RGBA TIFF**, 427,393,200 bytes, with equirectangular 360 x 180 geometry, exact 2:1 ratio and full canvas. **Measured alpha coverage is 79.513%** (unrounded fraction 0.7951309245376593). Enblend reported redundant images, inability to run the Dijkstra optimizer, and seam endpoints outside the cost image. The existing warning parser also captures explanatory continuation/contour lines; these are not seven independent defect categories.

Pillow issued its large-image warning at 173,911,250 pixels. Decoding, alpha measurement and preview generation still succeeded; no global image-size guard was disabled.

The new connectivity diagnostic was applied to the saved PTO after the full render, then checked through the current runner. `RESUME` executed zero steps, took 0.047 seconds, and retained preparation, alignment and blending warnings. Explicitly rerunning the preparation step reused all verified TIFFs without changing their mtimes. Rendering did not need repeating because the diagnostic does not alter the PTO.

Visual QA inspected a 4096 x 2048 preview and crops spanning the horizontal wrap join and central terrain. Terrain and the wrap join appear broadly continuous at preview scale; that is not a pixel-level approval of every seam. There are substantial, irregular NoData regions across the upper sky/zenith. The lower polar region has the expected strong equirectangular stretching. Complete spherical photographic coverage is **not** established. There was no aesthetic sky filling, cropping, seam-algorithm substitution or automatic placement of disconnected images.

Local artifacts include `validation.json`, `preparation_checks.json`, the final TIFF under `03_hugin/`, and `preview.jpg`, `wrap_preview.jpg`, and `terrain_preview.jpg`. They remain outside the Git checkout.

## Acceptance status

Preserving working TIFF metadata resolves the JPEG preparation blocker. Command success, canvas geometry and photographic alignment are distinct checks. In this real set, the cleaned control-point graph has 2,014 points but six components: one main group of 28 images and five isolated images (zero-based indices 16, 17, 24, 25 and 32). A rendered 2:1 panorama must not be accepted as correctly aligned on that evidence alone.

The JPEG EXIF blocker and technical end-to-end execution are validated. The photographic result still requires review and further alignment work; geometry PASS must not be presented as complete spherical coverage or photographic acceptance.

Keep issue #25 open for user testing (`To be tested`). Real DNG end-to-end behavior was not tested because no DNG dataset was supplied; synthetic regression coverage verifies the existing RawTherapee command contract.
