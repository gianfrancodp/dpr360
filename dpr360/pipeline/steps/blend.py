from __future__ import annotations
import re
from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.pto import validate_panorama

_WARNING_RE = re.compile(r"(?i)\b(?:warning|note):\s*(.+)$")

def build_enblend_args(enblend, out, files, width, height, verbose=1):
    args = [
        str(enblend),
        "--wrap=horizontal",
        "-f",
        f"{int(width)}x{int(height)}+0+0",
    ]
    if verbose:
        args.append(f"--verbose={int(verbose)}")
    args += ["-o", str(out)]
    args += [str(p) for p in files]
    return args

def collect_enblend_warnings(stderr: str) -> list[str]:
    warnings = []
    for raw in (stderr or "").splitlines():
        m = _WARNING_RE.search(raw.strip())
        if m:
            text = m.group(1).strip()
            if text and text not in warnings:
                warnings.append(text)
    return warnings

class BlendStep(BaseStep):
    name = "blend"
    label = "Enblend · fusione"
    weight = 0.14
    prerequisites = ("remap",)

    def run(self, ctx):
        files = sorted((ctx.hugin_dir / "remap").glob("level_*.tif"))
        if not files:
            return StepResult(self.name, False, 2, "Nessun livello remappato.")

        pto = ctx.hugin_dir / "project_360.pto"
        try:
            info = validate_panorama(pto)
        except Exception as e:
            return StepResult(
                self.name,
                False,
                10,
                f"Impossibile leggere la geometria PTO prima di Enblend: {e}",
            )

        if not info.get("valid"):
            return StepResult(
                self.name,
                False,
                10,
                "Geometria PTO non valida prima di Enblend.",
                details=info,
            )

        width = info["width"]
        height = info["height"]
        out = ctx.final_tif

        if out.exists():
            out.unlink()

        ctx.progress(.02, f"Avvio blending · canvas {width}×{height}")

        def line_hook(stream, line):
            m = re.search(r'(?<!\d)(\d{1,3})\s*%', line)
            if m:
                ctx.progress(
                    min(.98, int(m.group(1)) / 100),
                    f"Blending {m.group(1)}%",
                )

        verbose = int(
            ctx.config.get("pipeline", {}).get("enblend_verbose", 1)
        )

        args = build_enblend_args(
            ctx.tools["enblend"],
            out,
            files,
            width,
            height,
            verbose=verbose,
        )

        r = self.command(
            ctx,
            args,
            timeout=10800,
            line_hook=line_hook,
        )

        if r.returncode:
            return StepResult(
                self.name,
                False,
                r.returncode,
                "enblend fallito",
                stderr=r.stderr,
            )

        if not out.exists():
            return StepResult(
                self.name,
                False,
                6,
                "Enblend terminato ma il TIFF finale non esiste.",
            )

        warnings = collect_enblend_warnings(r.stderr)

        details = {
            "size_bytes": out.stat().st_size,
            "canvas_width": width,
            "canvas_height": height,
            "enblend_frame": f"{width}x{height}+0+0",
            "wrap": "horizontal",
            "warning_count": len(warnings),
            "warnings": warnings,
        }

        ctx.progress(1, "Blending completato")

        if warnings:
            return StepResult(
                self.name,
                True,
                0,
                f"Panorama fuso con {len(warnings)} warning Enblend.",
                stderr=r.stderr,
                outputs=[str(out)],
                details=details,
                warnings=warnings,
            )

        return StepResult(
            self.name,
            True,
            0,
            "Panorama fuso.",
            outputs=[str(out)],
            details=details,
        )
