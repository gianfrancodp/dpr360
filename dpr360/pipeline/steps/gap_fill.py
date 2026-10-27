from dpr360.gap_fill import ARTIFACTS, cached_report, export_fill, options
from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep


class GapFillStep(BaseStep):
    name = "gap_fill"
    label = "Riempimento cromatico dei vuoti"
    weight = .06
    prerequisites = ("final_validation",)

    def checkpoint_valid(self, ctx, result):
        settings = options(ctx.config)
        if result.get("details", {}).get("settings") != settings:
            return False
        return not settings["enabled"] or cached_report(ctx.final_tif, ctx.fill_dir, settings["method"]) is not None

    def run(self, ctx):
        settings = options(ctx.config)
        if not settings["enabled"]:
            return StepResult(self.name, True, 0, "Riempimento opzionale disattivato.", details={"settings": settings})
        try:
            report = export_fill(ctx.final_tif, ctx.fill_dir, settings["method"], ctx.progress)
        except Exception as exc:
            return StepResult(self.name, False, 7, f"Riempimento non completato: {exc}", stderr=repr(exc))
        warnings = []
        if report["uncovered_pixel_count"] or report["partial_alpha_pixel_count"]:
            warnings.append("Le aree colorate sono sintetiche. La copertura fotografica originale non è aumentata.")
        return StepResult(self.name, True, 0, "Copia colorata e maschera create; master originale conservato.",
                          outputs=[str(ctx.fill_dir / name) for name in (*ARTIFACTS, "fill_report.json")],
                          details={"settings": settings, **report}, warnings=warnings)
