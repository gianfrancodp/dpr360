from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

@dataclass
class StepResult:
    name: str
    success: bool
    returncode: int = 0
    message: str = ""
    stdout: str = ""
    stderr: str = ""
    outputs: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ProgressEvent:
    step_name: str
    step_label: str
    step_fraction: float
    overall_fraction: float
    message: str = ""

@dataclass
class PipelineContext:
    source_dir: Path
    project_dir: Path
    tools: dict[str, str]
    config: dict[str, Any]
    logger: Any
    progress_callback: Callable[[float, str], None] | None = None
    live_log_callback: Callable[[str], None] | None = None

    @property
    def metadata_dir(self) -> Path:
        return self.project_dir / "01_metadata"

    @property
    def tiff_dir(self) -> Path:
        return self.project_dir / "02_tiff"

    @property
    def hugin_dir(self) -> Path:
        return self.project_dir / "03_hugin"

    @property
    def final_tif(self) -> Path:
        return self.hugin_dir / "panorama_360_finale.tif"

    def ensure_dirs(self) -> None:
        for p in (self.project_dir, self.metadata_dir, self.tiff_dir, self.hugin_dir):
            p.mkdir(parents=True, exist_ok=True)

    def progress(self, fraction: float, message: str = "") -> None:
        fraction = max(0.0, min(1.0, float(fraction)))
        if self.progress_callback:
            self.progress_callback(fraction, message)

    def live_log(self, line: str) -> None:
        if self.live_log_callback and line:
            self.live_log_callback(line.rstrip())
