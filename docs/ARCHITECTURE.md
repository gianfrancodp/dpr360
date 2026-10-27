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

JPEG TIFFs are written atomically: Pillow writes fresh RGB pixels and the original ICC profile; ExifTool rebuilds selected photographic EXIF (make/model, lens, exact numeric focal lengths, exposure and capture time), normalizing orientation and dimensions. Source JPEG IFD offsets, MakerNotes and GPS are not transplanted into working TIFFs. Full original metadata remains in the local JSON/CSV export. A readable TIFF and a matching source path/size/mtime record are required for reuse. Checkpoints also include the selected source filenames, sizes and mtimes; older checkpoints without a manifest are conservatively reset. This identity is not a content hash.

Downstream Hugin and Nona steps receive only working TIFFs whose stems match the active source set. Ambiguous same-stem source files are rejected during preparation. Smoke tests select the current source's output explicitly.

## Geometry

Version 3.2.1 uses the Hugin control-point/optimiser backend. Before Nona, the PTO is normalized to equirectangular projection, 360° HFOV and exact 2:1 full-canvas crop. Final geometry and actual alpha coverage are validated independently.

## Optional boundary-color filling

The `gap_fill` step follows final validation and is disabled by default. It can also run directly against an existing master from the **Colora i vuoti** UI tab without source photographs or external stitching tools. The technical RGBA master and its measured coverage remain authoritative; a separate `04_fill/` export contains an opaque RGB display copy, an 8-bit synthetic-contribution mask, a report and previews.

`boundary_mean` computes one color per connected proxy hole from its photographed boundary. `boundary_gradient` uses those colors to initialize a multiscale harmonic extension clamped to measured colors. Longitude is periodic, latitude ends are distinct, and a completely uncovered pole row converges to one color across longitudes. Both methods estimate colors on a bounded-resolution proxy and interpolate the field in strips at original resolution. Tiny holes within a proxy cell use that cell's measured average. No cloud or terrain texture is generated.

Tifffile/imagecodecs decode LZW/Deflate RGBA TIFFs into temporary disk-backed arrays. The export preserves unsigned 8/16-bit samples and ICC data. Fully opaque source RGB pixels are checked for exact equality after decoding the written result. Partially transparent pixels are composited over the fill field, accounting for associated or unassociated alpha; the contribution mask records those changes as gray values. Missing coverage is read from alpha, not inferred from black RGB values. Fully transparent panoramas, missing/undeclared alpha, unsupported sample types, and non-2:1 canvases are rejected.

Outputs are staged and validated in a temporary folder, then individually replaced; the JSON report is committed last. File signatures in that report prevent reuse of an incomplete multi-artifact update. A matching master signature, method, algorithm version and output signatures allow reuse. The runner refreshes this step's checkpoint when options or the master change, leaving completed stitching steps intact. The UI's last generated preview is labeled with its actual method. Source size/mtime signatures are cache identities, not cryptographic content guarantees.

The generated display copy reports 100% display coverage separately from the unchanged photographic coverage. Filling does not repair disconnected geometry or certify that synthetic regions contain photographed information.

## Frozen Windows build

`launcher.py` starts the bundled Streamlit UI. `DPR360_HOME` points runtime state/config/logs at the application directory rather than PyInstaller's internal bundle resource directory. RawTherapee, Hugin and ExifTool remain external dependencies.
