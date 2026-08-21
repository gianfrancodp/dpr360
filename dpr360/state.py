from __future__ import annotations
from pathlib import Path
import datetime, json

class PipelineState:
    def __init__(self, project_dir: Path, step_names: list[str]):
        self.path = Path(project_dir) / ".dpr360" / "state.json"
        self.step_names = step_names
        self.data = self._load_or_new()

    def _new(self):
        return {
            "schema": 1,
            "updated_at": None,
            "source_dir": "",
            "steps": {n: {"status": "pending", "result": None} for n in self.step_names},
        }

    def _load_or_new(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for n in self.step_names:
                    data.setdefault("steps", {}).setdefault(n, {"status": "pending", "result": None})
                return data
            except Exception:
                pass
        return self._new()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def reset(self, source_dir=""):
        self.data = self._new(); self.data["source_dir"] = source_dir; self.save()

    def set_source(self, source_dir: str):
        self.data["source_dir"] = source_dir; self.save()

    def status(self, name): return self.data["steps"].get(name, {}).get("status", "pending")
    def set_running(self, name):
        self.data["steps"][name] = {"status": "running", "result": None}; self.save()
    def set_result(self, name, status, result):
        self.data["steps"][name] = {"status": status, "result": result}; self.save()
