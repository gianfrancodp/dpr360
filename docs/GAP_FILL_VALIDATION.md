# Boundary-color filling: implementation and validation

Validated on 2026-10-27. The full automated suite passed: **49 passed**. This includes the existing JPEG/DNG and UI regressions plus synthetic 8/16-bit LZW TIFFs, nested color cases, partial associated/unassociated alpha, horizontal periodicity, uniform uncovered pole color, black opaque photographs, atomic failure handling and unchanged master content.

## User workflow

Open **Colora i vuoti**, enable optional filling, choose a method and click **Crea / aggiorna copia colorata**. The same operation is available as the final optional `gap_fill` pipeline step. Existing validated projects need no new stitching run; changing fill options invalidates only the fill checkpoint. The dedicated UI path works with an existing master and project directory even without source frames or external processing tools.

The default method is a smooth boundary gradient. A second method fills each connected empty region from its boundary mean. Both operate on alpha-defined missing regions, handle longitude wrap, preserve the master, and produce a separate RGB TIFF and synthetic-contribution mask. Photographed opaque RGB samples are retained exactly. Partial alpha is composited, not misclassified as a fully opaque original sample. ICC and uint8/uint16 precision are preserved; display JPEG previews are deliberately 8-bit.

The boundary-mean option visibly exposes the outline of irregular holes more than the gradient. The gradient is a color continuation, not a reconstruction of clouds. Sampling at finite proxy resolution can leave a small visual transition where highly textured clouds meet smooth synthetic color. The feature does not fix the existing disconnected-image geometry.

## Real-master validation

The existing local 18650 x 9325 RGBA master from the real JPEG pipeline run was processed directly, without rerunning Hugin, Nona or Enblend. It contains 173,911,250 pixels, of which 35,629,037 were fully uncovered and none had partial alpha. Original photographic coverage is 79.51309245376594%.

| Check | Result |
| --- | --- |
| Boundary gradient export and pixel verification | 39.547 seconds |
| Per-hole boundary mean export and pixel verification | 36.750 seconds |
| Display copy | 18650 x 9325 RGB, 8-bit, lossless Deflate TIFF |
| Gradient copy size | 319,557,271 bytes |
| Contribution mask | 18650 x 9325, 8-bit; 255 in fully synthetic regions |
| Photographic opaque pixels | Exact equality after decoding exported TIFF |
| Original master | SHA-256 unchanged |
| Photographic coverage | Unchanged at 79.513% |
| Display coverage | 100%, explicitly including synthetic color |
| Independent mask audit | Exactly 35,629,037 nonzero pixels; values only 0 and 255 for this source |
| Real-project RESUME | Zero steps executed; all generated export mtimes unchanged |

Both exported previews were inspected locally. The gradient removes the dark sky gaps with a smooth blue-gray continuation and a consistent pole color. The mean-color alternative is usable but its boundary shape remains more visible. Landscape pixels remain photographic; no sky texture or missing scene detail was invented.

The regression suite separately validates non-8-bit-aligned 16-bit values, exact opaque-pixel preservation, retained ICC bytes and 16-bit output. No real DNG master was supplied for this run; 16-bit support is demonstrated by synthetic TIFF tests, not claimed as a new real RAW end-to-end run.

Private artifacts remain outside the repository: the project's `04_fill/` folder holds the gradient result, mask, report and before/after JPEG previews. A sibling `04_fill_mean_comparison/` holds the comparison. The private runner `test_data/run_gap_fill.py` records timings and master-hash verification in `gap_fill_validation.json`. Do not commit photographs or rendered previews.

Environment: Python 3.11.0rc2, Pillow 12.3.0, NumPy 2.4.6, tifffile 2026.3.3 and imagecodecs 2026.3.6 on Windows. Package license metadata and the bundled libtiff/libdeflate/zlib notices relevant to the TIFF path were reviewed; the frozen-build specification includes imagecodecs package data and codec binaries. The release process must retain and audit all resolved wheel notices. A new frozen application build was not executed as part of this feature validation.
