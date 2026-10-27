from __future__ import annotations
from dpr360.models import ProgressEvent, StepResult
from dpr360.scanning import discover_source_set, source_manifest
from dpr360.state import PipelineState

SUCCESS_STATUSES = {"completed", "completed_with_warnings"}

class PipelineRunner:
    def __init__(self, ctx, steps):
        self.ctx = ctx
        self.steps = steps
        self.by_name = {s.name: s for s in steps}
        self.total_weight = sum(s.weight for s in steps)
        self.state = PipelineState(ctx.project_dir, [s.name for s in steps])
        self._sync_source()
        self._refresh_checkpoints()
        self.ui_progress_callback = None

    def _refresh_checkpoints(self):
        for step in self.steps:
            validator = getattr(step, "checkpoint_valid", None)
            if validator and self._is_success(self.state.status(step.name)):
                saved = self.state.data["steps"][step.name].get("result") or {}
                if not validator(self.ctx, saved):
                    self.state.set_result(step.name, "pending", None)

    def _sync_source(self):
        ctx = self.ctx
        source_format = discover_source_set(ctx.source_dir).input_format
        manifest = source_manifest(ctx.source_dir)
        saved_dir = self.state.data.get("source_dir")
        saved_format = self.state.data.get("source_format", "")
        if saved_dir and (saved_dir != str(ctx.source_dir) or saved_format != source_format
                          or self.state.data.get("source_manifest") != manifest):
            self.state.reset(str(ctx.source_dir), source_format, manifest)
        elif not self.state.data.get("source_dir"):
            self.state.set_source(str(ctx.source_dir), source_format, manifest)

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
        self._sync_source()
        self._refresh_checkpoints()
        if not resume:
            self.reset()

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
        for step in self.steps:
            saved=self.state.data["steps"][step.name].get("result") or {}
            all_warnings.extend([f"{step.name}: {w}" for w in saved.get("warnings",[])])

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
        self._sync_source()
        self._refresh_checkpoints()
        return self._run_one(self.by_name[name])

    def reset(self):
        source_format = discover_source_set(self.ctx.source_dir).input_format
        self.state.reset(str(self.ctx.source_dir), source_format, source_manifest(self.ctx.source_dir))
