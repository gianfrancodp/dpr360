from __future__ import annotations
from pathlib import Path
import re, shutil

def _p_line(lines):
    for i, line in enumerate(lines):
        if line.startswith("p "):
            return i, line.rstrip("\n")
    raise ValueError("Linea panorama 'p' non trovata nel PTO.")

def _num(line: str, key: str, kind=float):
    m = re.search(rf'(?<!\S){re.escape(key)}(-?\d+(?:\.\d+)?)', line)
    return kind(float(m.group(1))) if m else None

def parse_panorama(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    _, line = _p_line(lines)
    crop_m = re.search(r'(?<!\S)S(-?\d+),(-?\d+),(-?\d+),(-?\d+)', line)
    crop = tuple(map(int, crop_m.groups())) if crop_m else None
    width = _num(line, "w", int); height = _num(line, "h", int)
    return {
        "projection": _num(line, "f", int),
        "width": width,
        "height": height,
        "hfov": _num(line, "v", float),
        "crop": crop,
        "ratio": (width / height) if width and height else None,
        "p_line": line,
    }

def force_full_equirectangular(src: Path, dst: Path) -> dict:
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines(True)
    idx, line = _p_line(lines)
    width = _num(line, "w", int)
    if not width or width <= 0: raise ValueError("Larghezza canvas non valida nel PTO.")
    height = int(round(width / 2))
    def set_token(s, key, value):
        pattern = rf'(?<!\S){re.escape(key)}-?\d+(?:\.\d+)?'
        token = f"{key}{value}"
        return re.sub(pattern, token, s, count=1) if re.search(pattern, s) else s + " " + token
    line = set_token(line, "f", 2)
    line = set_token(line, "w", width)
    line = set_token(line, "h", height)
    line = set_token(line, "v", 360)
    full_crop = f"S0,{width},0,{height}"
    if re.search(r'(?<!\S)S-?\d+,-?\d+,-?\d+,-?\d+', line):
        line = re.sub(r'(?<!\S)S-?\d+,-?\d+,-?\d+,-?\d+', full_crop, line, count=1)
    else:
        line += " " + full_crop
    lines[idx] = line.rstrip("\r\n") + "\n"
    dst.write_text("".join(lines), encoding="utf-8")
    return parse_panorama(dst)

def validate_panorama(path: Path, ratio_tolerance=1e-4, hfov_tolerance=0.05) -> dict:
    info = parse_panorama(path)
    w, h, crop = info["width"], info["height"], info["crop"]
    checks = {
        "projection_equirectangular": info["projection"] == 2,
        "hfov_360": info["hfov"] is not None and abs(info["hfov"] - 360.0) <= hfov_tolerance,
        "canvas_2_to_1": info["ratio"] is not None and abs(info["ratio"] - 2.0) <= ratio_tolerance,
        "full_canvas_crop": crop == (0, w, 0, h) if crop and w and h else False,
    }
    return {**info, "checks": checks, "valid": all(checks.values())}
