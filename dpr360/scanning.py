from pathlib import Path

def list_dngs(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".dng"],
        key=lambda p: p.name.lower(),
    )

def list_tiffs(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}],
        key=lambda p: p.name.lower(),
    )
