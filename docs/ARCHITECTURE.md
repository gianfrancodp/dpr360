# DPR360 architecture

DPR360 separates UI/orchestration from external image-processing tools.

```text
Streamlit UI (app.py)
        │
        ▼
DPR360 Python core
  ├─ tool discovery
  ├─ process supervision
  ├─ checkpoint state
  ├─ privacy-aware logging
  ├─ PTO geometry validation
  └─ pipeline runner
        │
        ▼
External native tools
RawTherapee · Hugin/Nona · Enblend · ExifTool
```

## Pipeline state

Each project stores state in `.dpr360/state.json`. The runner records both the source directory and detected input format, treats `completed` and `completed_with_warnings` as successful prerequisites, and supports resuming from the first unfinished step.

## Source preparation

Source discovery is case-insensitive and accepts DNG, JPG, and JPEG extensions. DNG takes precedence when both formats occur in one folder, preserving the existing RAW-first behavior. RawTherapee develops DNG files to 16-bit TIFF in `02_tiff`. Pillow decodes JPEG frames to losslessly compressed working TIFFs in `02_tiff/jpeg`, preserving available EXIF and ICC data while applying EXIF orientation. These TIFFs still contain information originating from an 8-bit compressed source.

Downstream Hugin and Nona steps receive only working TIFFs whose stems match the active source set, preventing stale artifacts or another input format from entering the panorama.

## Geometry

Version 3.2.1 uses the Hugin control-point/optimiser backend. Before Nona, the PTO is normalized to equirectangular projection, 360° HFOV and exact 2:1 full-canvas crop. Final geometry and actual alpha coverage are validated independently.

## Frozen Windows build

`launcher.py` starts the bundled Streamlit UI. `DPR360_HOME` points runtime state/config/logs at the application directory rather than PyInstaller's internal bundle resource directory. RawTherapee, Hugin and ExifTool remain external dependencies.
