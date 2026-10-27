# Third-party software notices

DPR360 orchestrates independent external tools. They are **not included in the source repository** and are not incorporated into DPR360 source code.

## RawTherapee

RAW image development. Upstream: https://rawtherapee.com/<br>
License: GNU GPL v3 or later (verify the license shipped with the installed version).

## Hugin

Panorama project/control-point/remapping tools. Upstream: https://hugin.sourceforge.io/<br>
License: GNU GPL v2 or later for the Hugin project (verify component-specific notices shipped upstream).

## Enblend/Enfuse

Image blending. Upstream: https://enblend.sourceforge.net/<br>
License: GNU GPL v2 or later (verify the license shipped with the installed version).

## ExifTool

Metadata extraction. Upstream: https://exiftool.org/<br>
Distributed under the same terms as Perl (Artistic License and/or GNU GPL, as documented upstream).

## Distribution policy

The GitHub source repository and the DPR360 PyInstaller application build do not bundle the tools above. DPR360 discovers existing installations or assists the user in obtaining them separately. If a future release redistributes third-party binaries, the release process must include the exact upstream license texts, version/source references and any corresponding-source obligations applicable to that distribution.

## Python image-processing libraries

Optional color filling uses NumPy (BSD-3-Clause, https://numpy.org/doc/stable/license.html), tifffile (BSD-3-Clause, https://github.com/cgohlke/tifffile), and imagecodecs (BSD-3-Clause, https://github.com/cgohlke/imagecodecs). These are Python package dependencies and may be included in the frozen application, unlike the external executables listed above. Their permissive package licenses are compatible with this project's GPL-3.0-or-later distribution.

Imagecodecs wheels include third-party codec implementations with additional notices. The application build collects the imagecodecs package data, including its `licenses/` directory; retain those bundled notices and the exact dependencies' license texts in distributed builds. Review the resolved wheels and collected notices when releasing a new dependency version. Only LZW/Deflate TIFF decoding and lossless Deflate output are used by the filling feature.
