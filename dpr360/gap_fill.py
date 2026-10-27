"""Deterministic boundary-color filling for derived spherical TIFF copies."""
from __future__ import annotations

from collections import deque
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image
import tifffile

METHODS = ("boundary_gradient", "boundary_mean")
ALGORITHM_VERSION = 1
ARTIFACTS = ("panorama_360_filled.tif", "fill_mask.tif", "preview_original.jpg", "preview_filled.jpg")


def options(config):
    value = config.get("gap_fill", {})
    return {"enabled": bool(value.get("enabled", False)),
            "method": value.get("method", "boundary_gradient")}


def signature(path):
    path = Path(path)
    stat = path.stat()
    return [str(path.resolve()), stat.st_size, stat.st_mtime_ns]


def cached_report(source, destination, method):
    try:
        report = json.loads((Path(destination) / "fill_report.json").read_text(encoding="utf-8"))
        if (report["algorithm_version"] != ALGORITHM_VERSION or report["method"] != method
                or report["source_signature"] != signature(source)):
            return None
        for name in ARTIFACTS:
            if report["artifacts"][name] != signature(Path(destination) / name):
                return None
        return report
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _resize(field, height, width):
    """Bilinear interpolation with longitude wrap and finite latitude ends."""
    old_h, old_w = field.shape[:2]
    x = (np.arange(width) + .5) * old_w / width - .5
    x0 = np.floor(x).astype(int)
    wx = (x - x0).astype(np.float32)[None, :, None]
    horizontal = field[:, x0 % old_w] * (1 - wx) + field[:, (x0 + 1) % old_w] * wx
    y = np.clip((np.arange(height) + .5) * old_h / height - .5, 0, old_h - 1)
    y0 = np.floor(y).astype(int)
    wy = (y - y0).astype(np.float32)[:, None, None]
    return horizontal[y0] * (1 - wy) + horizontal[np.minimum(y0 + 1, old_h - 1)] * wy


def _component_means(colors, known):
    """One boundary mean per hole; disconnected holes do not share a color."""
    height, width = known.shape
    visited = known.copy()
    field = colors.copy()
    for y, x in zip(*np.nonzero(~known)):
        if visited[y, x]:
            continue
        visited[y, x] = True
        queue = deque([(y, x)])
        region, border = [], set()
        while queue:
            row, col = queue.popleft()
            region.append(row * width + col)
            neighbors = [(row, (col - 1) % width), (row, (col + 1) % width)]
            if row:
                neighbors.append((row - 1, col))
            if row + 1 < height:
                neighbors.append((row + 1, col))
            for ny, nx in neighbors:
                if known[ny, nx]:
                    border.add(ny * width + nx)
                elif not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        if not border:
            raise ValueError("No photographed boundary is available for filling.")
        mean = colors.reshape(-1, 3)[list(border)].mean(axis=0)
        field.reshape(-1, 3)[region] = mean
    return field


def boundary_field(colors, known, method):
    """Smooth only the extrapolated field; measured pixels stay clamped."""
    if method not in METHODS:
        raise ValueError("Unknown gap-fill method: " + str(method))
    if not known.any():
        raise ValueError("The panorama is entirely transparent; there are no colors to sample.")
    field = _component_means(colors, known)
    if method == "boundary_mean" or known.all():
        return field
    pyramid = [(colors, known)]
    while min(pyramid[-1][1].shape) > 24:
        seed, mask = pyramid[-1]
        height, width = mask.shape
        sums = np.zeros(((height + 1) // 2, (width + 1) // 2, 3), np.float32)
        counts = np.zeros(sums.shape[:2], np.float32)
        for dy in (0, 1):
            for dx in (0, 1):
                part = mask[dy::2, dx::2]
                ph, pw = part.shape
                sums[:ph, :pw] += seed[dy::2, dx::2] * part[..., None]
                counts[:ph, :pw] += part
        coarse = sums / np.maximum(counts[..., None], 1)
        pyramid.append((coarse, counts > 0))
    for seed, mask in reversed(pyramid):
        field = _resize(field, *mask.shape)
        field[mask] = seed[mask]
        unknown = ~mask
        for iteration in range(280):
            update = np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1)
            update[1:] += field[:-1]
            update[:-1] += field[1:]
            update[0] += field[0]
            update[-1] += field[-1]
            update *= .25
            if unknown[0].all():
                update[0] = update[0].mean(axis=0)
            if unknown[-1].all():
                update[-1] = update[-1].mean(axis=0)
            if iteration % 10 == 0 and np.max(np.abs(update[unknown] - field[unknown]), initial=0) < 1e-5:
                field[unknown] = update[unknown]
                break
            field[unknown] = update[unknown]
    return np.clip(field, 0, 1)


def _proxy(image, associated, maximum):
    height, width = image.shape[:2]
    scale = max(1, math.ceil(width / 768), math.ceil(height / 384))
    ys = np.arange(0, height, scale)
    xs = np.arange(0, width, scale)
    colors = np.zeros((len(ys), len(xs), 3), np.float32)
    weights = np.zeros(colors.shape[:2], np.float32)
    observed = partial = 0
    for index, y in enumerate(ys):
        block = image[y:y + scale]
        alpha = block[..., 3].astype(np.float32) / maximum
        observed += int(np.count_nonzero(block[..., 3]))
        partial += int(np.count_nonzero((block[..., 3] > 0) & (block[..., 3] < maximum)))
        rgb = block[..., :3].astype(np.float32) / maximum
        weighted = rgb if associated else rgb * alpha[..., None]
        # Alpha=0 RGB is arbitrary, including in nominally associated TIFFs.
        weighted[alpha == 0] = 0
        sums = np.add.reduceat(weighted.sum(axis=0), xs, axis=0)
        weight = np.add.reduceat(alpha.sum(axis=0), xs)
        colors[index] = sums / np.maximum(weight[:, None], 1e-12)
        weights[index] = weight
    return np.clip(colors, 0, 1), weights > 0, observed, partial


def _background_rows(field, height, width, start, stop):
    """Interpolate a field strip without allocating a full-resolution float image."""
    fh, fw = field.shape[:2]
    y = np.clip((np.arange(start, stop) + .5) * fh / height - .5, 0, fh - 1)
    y0 = np.floor(y).astype(int)
    wy = (y - y0).astype(np.float32)[:, None, None]
    rows = field[y0] * (1 - wy) + field[np.minimum(y0 + 1, fh - 1)] * wy
    x = (np.arange(width) + .5) * fw / width - .5
    x0 = np.floor(x).astype(int)
    wx = (x - x0).astype(np.float32)[None, :, None]
    return rows[:, x0 % fw] * (1 - wx) + rows[:, (x0 + 1) % fw] * wx


def export_fill(source, destination, method="boundary_gradient", progress=None):
    """Export an opaque RGB copy, contribution mask, previews and honest coverage report.

    TIFF decoding and output staging use temporary disk-backed arrays. UInt8 and
    UInt16 pixels and the source ICC profile are retained; the source is read-only.
    """
    source, destination = Path(source), Path(destination)
    progress = progress or (lambda fraction, message: None)
    if method not in METHODS:
        raise ValueError("Unknown gap-fill method: " + str(method))
    if source.resolve() in [(destination / name).resolve() for name in (*ARTIFACTS, "fill_report.json")]:
        raise ValueError("The input master must not be a fill output.")
    current = cached_report(source, destination, method)
    if current:
        progress(1, "Copia colorata già aggiornata")
        return current
    before = signature(source)
    destination.mkdir(parents=True, exist_ok=True)
    mappings = []
    with tempfile.TemporaryDirectory(prefix=".fill-work-", dir=destination) as temporary:
        work = Path(temporary)
        try:
            progress(.02, "Lettura del master e della maschera alpha")
            with tifffile.TiffFile(source) as tif:
                page = tif.pages[0]
                if (len(tif.pages) != 1 or len(page.shape) != 3 or page.shape[-1] != 4
                        or int(page.photometric) != 2 or not page.extrasamples
                        or int(page.extrasamples[0]) not in (1, 2)):
                    raise ValueError("A single RGBA TIFF with an explicit alpha coverage mask is required.")
                height, width, _ = page.shape
                if width != height * 2:
                    raise ValueError("The source panorama must have an exact 2:1 canvas.")
                if page.dtype.kind != "u" or page.dtype.itemsize not in (1, 2):
                    raise ValueError("Gap filling supports unsigned 8-bit and 16-bit TIFFs.")
                orientation = page.tags.get(274)
                if orientation is not None and orientation.value != 1:
                    raise ValueError("The master must use normalized orientation.")
                associated = int(page.extrasamples[0]) == 1
                profile_tag = page.tags.get(34675)
                profile = profile_tag.value if profile_tag is not None else None
                image = page.asarray(out=str(work / "decoded.npy"), maxworkers=2)
                mappings.append(image)
            dtype = np.dtype("uint8" if image.dtype.itemsize == 1 else "uint16")
            maximum = np.iinfo(dtype).max
            progress(.15, "Campionamento dei colori fotografati")
            colors, known, observed, partial = _proxy(image, associated, maximum)
            field = boundary_field(colors, known, method)
            progress(.32, "Riempimento delle zone prive di fotografie")
            rgb = np.lib.format.open_memmap(work / "rgb.npy", mode="w+", dtype=dtype, shape=(height, width, 3))
            mask = np.lib.format.open_memmap(work / "mask.npy", mode="w+", dtype="uint8", shape=(height, width))
            mappings.extend([rgb, mask])
            for start in range(0, height, 128):
                stop = min(start + 128, height)
                block = image[start:stop]
                alpha = block[..., 3].astype(np.float32) / maximum
                background = _background_rows(field, height, width, start, stop)
                original = block[..., :3].astype(np.float32) / maximum
                combined = np.where(alpha[..., None] > 0, original, 0) if associated else original * alpha[..., None]
                combined = combined + background * (1 - alpha[..., None])
                result = np.clip(np.rint(combined * maximum), 0, maximum).astype(dtype)
                opaque = block[..., 3] == maximum
                result[opaque] = block[..., :3][opaque]
                rgb[start:stop] = result
                mask[start:stop] = np.ceil((maximum - block[..., 3].astype(np.float64)) * 255 / maximum).astype("uint8")
                progress(.32 + .35 * stop / height, "Colorazione delle aree vuote")
            description = json.dumps({"dpr360_synthetic_fill": method, "original_coverage_percent": observed * 100 / (width * height)})
            extra = [(274, "H", 1, 1, False)]
            if profile:
                extra.append((34675, "B", len(profile), profile, False))
            tifffile.imwrite(work / ARTIFACTS[0], rgb, photometric="rgb", compression="deflate",
                             rowsperstrip=128, maxworkers=2, metadata=None, description=description,
                             extratags=extra, bigtiff=rgb.nbytes > 2**32 - 2**25)
            tifffile.imwrite(work / ARTIFACTS[1], mask, photometric="minisblack", compression="deflate",
                             metadata=None, description="Synthetic color contribution: 0=photograph, 255=fully filled")
            progress(.82, "Verifica della copia colorata")
            with tifffile.TiffFile(work / ARTIFACTS[0]) as filled:
                verified = filled.asarray(out=str(work / "verified.npy"), maxworkers=2)
                mappings.append(verified)
                if verified.shape != (height, width, 3) or verified.dtype != dtype:
                    raise RuntimeError("Filled TIFF dimensions or bit depth changed.")
                for start in range(0, height, 128):
                    original = image[start:start + 128]
                    opaque = original[..., 3] == maximum
                    if not np.array_equal(verified[start:start + 128][opaque], original[..., :3][opaque]):
                        raise RuntimeError("Photographed opaque pixels changed during filling.")
            stride = max(1, math.ceil(width / 2048))
            small = image[::stride, ::stride].astype(np.float32) / maximum
            alpha = small[..., 3:4]
            original = small[..., :3] if associated else small[..., :3] * alpha
            original = np.clip(original + .125 * (1 - alpha), 0, 1)
            filled_preview = rgb[::stride, ::stride].astype(np.float32) / maximum
            size = (min(width, 2048), min(width, 2048) // 2)
            for name, pixels in zip(ARTIFACTS[2:], (original, filled_preview)):
                preview = Image.fromarray(np.rint(np.clip(pixels, 0, 1) * 255).astype("uint8"))
                preview = preview.resize(size, Image.Resampling.LANCZOS)
                preview.save(work / name, quality=92, **({"icc_profile": profile} if profile else {}))
            if signature(source) != before:
                raise RuntimeError("The input master changed while filling; retry on a stable master.")
            report = {"algorithm_version": ALGORITHM_VERSION, "method": method,
                      "source_signature": before, "width": width, "height": height,
                      "bit_depth": dtype.itemsize * 8, "source_associated_alpha": associated,
                      "photographed_pixel_count": observed, "uncovered_pixel_count": width * height - observed,
                      "partial_alpha_pixel_count": partial, "original_coverage_percent": observed * 100 / (width * height),
                      "synthetic_pixel_count": width * height - observed + partial,
                      "display_coverage_percent": 100.0, "opaque_photographic_pixels_unchanged": True,
                      "synthetic_fill": observed < width * height or partial > 0, "artifacts": {}}
            for name in ARTIFACTS:
                os.replace(work / name, destination / name)
                report["artifacts"][name] = signature(destination / name)
            marker = work / "fill_report.json"
            marker.write_text(json.dumps(report, indent=2), encoding="utf-8")
            os.replace(marker, destination / marker.name)
            progress(1, "Copia colorata pronta; copertura fotografica originale conservata")
            return report
        finally:
            # Close every mapping before TemporaryDirectory cleanup on Windows.
            for mapping in reversed(mappings):
                if isinstance(mapping, np.memmap):
                    mapping.flush()
                    mapping._mmap.close()
