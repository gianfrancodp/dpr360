# Changelog

All notable changes to DPR360 will be documented in this file.

## Unreleased

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
