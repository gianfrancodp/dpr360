"""JPEG development without transplanting JPEG EXIF directory offsets."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile

from PIL import Image, ImageOps

from dpr360.process import run_process


PHOTOGRAPHIC_TAGS = (
    "Make", "Model", "FocalLength", "FocalLengthIn35mmFormat", "LensModel",
    "LensMake", "FNumber", "ExposureTime", "ISO", "DateTimeOriginal",
)


def _copy_metadata(source, target, size, exiftool):
    result = run_process([
        str(exiftool), "-n", "-overwrite_original", "-TagsFromFile", str(source),
        *["-" + tag for tag in PHOTOGRAPHIC_TAGS],
        "-Orientation#=1", f"-ExifImageWidth={size[0]}",
        f"-ExifImageHeight={size[1]}", str(target),
    ], timeout=180)
    if result.returncode:
        raise RuntimeError("JPEG TIFF metadata write failed: " + result.stderr)


def prepare_jpeg(source: Path, destination: Path, exiftool=None):
    """Atomically create a decoded TIFF with fresh, selected photographic EXIF.

    GPS/MakerNotes and sensor-stage data remain in the source metadata export.
    ExifTool rebuilds valid TIFF IFDs; Pillow never serializes source EXIF offsets.
    """
    source, destination = Path(source), Path(destination)
    exiftool = exiftool or shutil.which("exiftool")
    if not exiftool:
        raise RuntimeError("ExifTool is required to preserve JPEG lens metadata.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".jpeg-", suffix=".tif", dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        with Image.open(source) as original:
            icc = original.info.get("icc_profile")
            oriented = ImageOps.exif_transpose(original).convert("RGB")
            # A fresh Image has neither cached EXIF nor JPEG IFD pointers.
            with Image.frombytes("RGB", oriented.size, oriented.tobytes()) as pixels:
                size = pixels.size
                options = {"format": "TIFF", "compression": "tiff_deflate"}
                if icc:
                    options["icc_profile"] = icc
                pixels.save(temporary, **options)
        _copy_metadata(source, temporary, size, exiftool)
        with Image.open(temporary) as check:
            check.load()
            if check.format != "TIFF" or check.mode != "RGB" or check.size != size:
                raise RuntimeError("Prepared JPEG TIFF has invalid pixels or dimensions.")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
