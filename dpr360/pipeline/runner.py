from __future__ import annotations
from dpr360.models import ProgressEvent, StepResult
from dpr360.state import PipelineState

SUCCESS_STATUSES = {"completed", "completed_with_warnings"}

class PipelineRunner:
    def __init__(self, ctx, steps):
        self.ctx = ctx
        self.steps = steps
        self.by_name = {s.name: s for s in steps}
        self.total_weight = sum(s.weight for s in steps)
        self.state = PipelineState(ctx.project_dir, [s.name for s in steps])
        if self.state.data.get("source_dir") and self.state.data["source_dir"] != str(ctx.source_dir):
            self.state.reset(str(ctx.source_dir))
        elif not self.state.data.get("source_dir"):
            self.state.set_source(str(ctx.source_dir))
        self.ui_progress_callback = None

    def _is_success(self, status: str) -> bool:
        return status in SUCCESS_STATUSES

    def _completed_weight(self, before_name=None):
        total = 0
        for s in self.steps:
            if before_name and s.name == before_name:
                break
            if self._is_success(self.state.status(s.name)):
                total += s.weight
        return total

    def overall_fraction(self):
        return min(
            1.0,
            sum(
                s.weight
                for s in self.steps
                if self._is_success(self.state.status(s.name))
            ) / self.total_weight,
        )

    def _run_one(self, step):
        for dep in step.prerequisites:
            if not self._is_success(self.state.status(dep)):
                return StepResult(
                    step.name,
                    False,
                    20,
                    f"Prerequisito non completato: {dep}",
                )

        self.state.set_running(step.name)
        self.ctx.logger.event("pipeline_step_start", step=step.name)

        base = sum(
            s.weight
            for s in self.steps
            if self._is_success(self.state.status(s.name)) and s.name != step.name
        )

        def progress(frac, msg):
            overall = min(1.0, (base + step.weight * frac) / self.total_weight)
            if self.ui_progress_callback:
                self.ui_progress_callback(
                    ProgressEvent(
                        step.name,
                        step.label,
                        frac,
                        overall,
                        msg,
                    )
                )

        self.ctx.progress_callback = progress

        try:
            result = step.run(self.ctx)
        except Exception as e:
            result = StepResult(
                step.name,
                False,
                99,
                f"Eccezione non gestita: {e}",
                stderr=repr(e),
            )

        if result.returncode == 0 and result.success:
            status = "completed_with_warnings" if result.has_warnings else "completed"
        else:
            status = "failed"

        self.state.set_result(step.name, status, result.to_dict())
        self.ctx.logger.event(
            "pipeline_step_end",
            step=step.name,
            status=status,
            returncode=result.returncode,
            message=result.message,
            warning_count=len(result.warnings),
            warnings=result.warnings,
        )
        return result

    def run_all(self, resume=False):
        if not resume:
            self.state.reset(str(self.ctx.source_dir))

        self.ctx.logger.event("pipeline_run_all_start", resume=resume)
        results = []

        for step in self.steps:
            if resume and self._is_success(self.state.status(step.name)):
                continue

            result = self._run_one(step)
            results.append(result)

            if result.returncode != 0:
                self.ctx.logger.event(
                    "pipeline_stopped",
                    failed_step=step.name,
                    returncode=result.returncode,
                )
                return result, results

        all_warnings = []
        for r in results:
            all_warnings.extend([f"{r.name}: {w}" for w in r.warnings])

        msg = "Pipeline completata."
        if all_warnings:
            msg = f"Pipeline completata con {len(all_warnings)} warning."

        ok = StepResult(
            "run_all",
            True,
            0,
            msg,
            warnings=all_warnings,
            details={"warning_count": len(all_warnings)},
        )
        self.ctx.logger.event(
            "pipeline_run_all_end",
            ok=True,
            warning_count=len(all_warnings),
        )
        return ok, results

    def run_step(self, name):
        return self._run_one(self.by_name[name])

    def reset(self):
        self.state.reset(str(self.ctx.source_dir))
