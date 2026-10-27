# Changelog

All notable changes to DPR360 will be documented in this file.

## Unreleased

### Optional boundary-color gap filling
- Added per-hole boundary mean and smooth boundary-gradient color filling with periodic longitude and a consistent uncovered pole color.
- Exported a separate opaque RGB TIFF, synthetic-contribution mask, report and before/after previews while retaining the original master and photographic coverage.
- Preserved 8/16-bit TIFF samples, ICC profiles and exact fully opaque photographic pixels; used disk-backed arrays for large panoramas.
- Added a dedicated UI tab and an optional resumable final pipeline step whose settings invalidate only the fill checkpoint.

### JPEG panorama input
- Rebuilt photographic TIFF metadata with ExifTool to support real nested DJI EXIF without libtiff offset errors; retained exact numeric focal values.
- Added atomic JPEG preparation, readable-output/source-identity checks, checkpoint manifest invalidation and duplicate-stem rejection.
- Fixed smoke tests selecting stale TIFFs; added nested-EXIF, orientation, retry and real-data validation coverage.
- Added a separate warning for disconnected PTO alignment and retained saved warnings on resume; real-data results distinguish canvas geometry from photographic coverage.
- Added case-insensitive discovery of individual JPG/JPEG panorama frames.
- Added lossless working-TIFF preparation with EXIF orientation and available EXIF/ICC preservation.
- Isolated JPEG intermediates and checkpoints from DNG projects.
- Added non-blocking warnings for missing DJI orientation metadata and JPEG source limitations.
- Updated the UI, smoke test, documentation, and automated coverage for JPEG input.

### Repository preparation / rebrand
- Project renamed to **DronePanoRAW 360 (DPR360)**.
- Python package renamed from the development name to `dpr360`.
- Project checkpoint folder renamed to `.dpr360`.
- Added GitHub repository documentation, issue templates and contribution/security guidance.
- Added CI, CodeQL, Windows PyInstaller build and tagged-release workflows.
- Added author/credits metadata for Gianfranco Di Pietro.

## 3.2.1
- Fix Enblend: validated PTO canvas is explicitly passed with `-f WIDTHxHEIGHT+0+0`.
- Enblend uses `--wrap=horizontal` for 360° equirectangular panoramas.
- Added configurable Enblend verbosity for improved blend diagnostics.
- Added `completed_with_warnings`; exit code 0 continues the pipeline while preserving warnings.
- `RESUME`, prerequisites and progress treat `completed_with_warnings` as successful.
- Added parsing of warning/note output produced by Enblend.
- Privacy-conscious logging: command stdout disabled by default.
- ExifTool stdout omitted from normal logs.
- Extended redaction for Windows paths, GPS and camera identifiers.
- Added optional diagnostic mode with redaction retained unless sensitive metadata is explicitly enabled.
- Added regression tests for Enblend arguments, warning state and logger privacy.

## 3.2.0
- Refactored processing core away from the UI.
- Added `RUN ALL`, stop-on-error, persistent checkpoints and `RESUME`.
- Added single-step execution.
- Added weighted overall progress and per-process progress.
- Added live collapsible execution logs.
- Added preventive PTO validation and full-canvas 360×180 2:1 normalization.
- Added separate final geometry and coverage validation.
- Added native file/folder selectors with path fallback.
- Added Windows setup helpers and external-tool discovery.
- Adopted GPL-3.0-or-later.
