from __future__ import annotations
from pathlib import Path
import copy, yaml

def _merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out

def load_config(root: Path) -> dict:
    base = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}
    local = root / "config.local.yaml"
    if local.exists():
        base = _merge(base, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    return base

def save_tool_override(root: Path, tool_key: str, value: str) -> None:
    p = root / "config.local.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    data = data or {}
    data.setdefault("tools", {})[tool_key] = value
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
