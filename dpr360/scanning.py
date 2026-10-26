from dataclasses import dataclass
from pathlib import Path

JPEG_SUFFIXES = {".jpg", ".jpeg"}


@dataclass(frozen=True)
class SourceSet:
    frames: tuple[Path, ...]
    input_format: str
    ignored_jpeg_count: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.frames

def list_dngs(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".dng"],
        key=lambda p: p.name.lower(),
    )


def list_jpegs(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in JPEG_SUFFIXES],
        key=lambda p: p.name.lower(),
    )


def discover_source_set(folder: Path) -> SourceSet:
    """Discover one input format while preserving the legacy DNG preference."""
    dngs = list_dngs(folder)
    jpegs = list_jpegs(folder)
    if dngs:
        return SourceSet(tuple(dngs), "dng", ignored_jpeg_count=len(jpegs))
    if jpegs:
        return SourceSet(tuple(jpegs), "jpeg")
    return SourceSet((), "none")


def source_manifest(folder: Path):
    """Checkpoint identity based on the selected filenames, sizes and mtimes."""
    return [[p.name, p.stat().st_size, p.stat().st_mtime_ns]
            for p in discover_source_set(folder).frames]

def list_tiffs(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}],
        key=lambda p: p.name.lower(),
    )
