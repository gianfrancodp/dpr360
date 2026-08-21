from __future__ import annotations
from abc import ABC, abstractmethod
from dpr360.models import StepResult, PipelineContext
from dpr360.process import run_process

class BaseStep(ABC):
    name = "base"
    label = "Base"
    weight = 1.0
    prerequisites: tuple[str, ...] = ()

    def command(self, ctx: PipelineContext, args: list[str], timeout=3600, poll_callback=None, line_hook=None):
        args = [str(x) for x in args]
        ctx.logger.event("command_start", step=self.name, command=args)

        def on_line(stream, line):
            if line:
                ctx.live_log(f"[{self.label}] {line}")
                if line_hook:
                    line_hook(stream, line)

        r = run_process(
            args,
            timeout=timeout,
            on_line=on_line,
            poll_callback=poll_callback,
        )

        logcfg = ctx.config.get("logging", {})
        diagnostic = bool(logcfg.get("diagnostic_mode", False))
        max_chars = int(logcfg.get("max_command_log_chars", 12000))

        include_stdout = bool(logcfg.get("include_command_stdout", False)) or diagnostic
        include_stderr = bool(logcfg.get("include_command_stderr", True)) or diagnostic

        # ExifTool stdout can contain GPS, serial numbers and complete paths.
        # In normal mode the parsed/summary metadata is logged instead.
        if self.name == "metadata" and not diagnostic:
            include_stdout = False

        payload = {
            "step": self.name,
            "returncode": r.returncode,
            "elapsed_s": round(r.elapsed_s, 3),
            "stdout_chars": len(r.stdout or ""),
            "stderr_chars": len(r.stderr or ""),
        }
        if include_stdout and r.stdout:
            payload["stdout"] = r.stdout[-max_chars:]
        if include_stderr and r.stderr:
            payload["stderr"] = r.stderr[-max_chars:]

        ctx.logger.event("command_end", **payload)
        return r

    @abstractmethod
    def run(self, ctx: PipelineContext) -> StepResult:
        ...
