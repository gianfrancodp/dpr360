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

Each project stores state in `.dpr360/state.json`. The runner treats `completed` and `completed_with_warnings` as successful prerequisites and supports resuming from the first unfinished step.

## Geometry

Version 3.2.1 uses the Hugin control-point/optimiser backend. Before Nona, the PTO is normalized to equirectangular projection, 360° HFOV and exact 2:1 full-canvas crop. Final geometry and actual alpha coverage are validated independently.

## Frozen Windows build

`launcher.py` starts the bundled Streamlit UI. `DPR360_HOME` points runtime state/config/logs at the application directory rather than PyInstaller's internal bundle resource directory. RawTherapee, Hugin and ExifTool remain external dependencies.
