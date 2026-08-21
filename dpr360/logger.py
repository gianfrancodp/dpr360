from __future__ import annotations
from pathlib import Path
import datetime, json, re, threading, uuid

_LOCK = threading.Lock()
_PROCESS_SESSION = str(uuid.uuid4())

def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")

_WINDOWS_PATH_RE = re.compile(
    r'(?i)(?:\b[A-Z]:[\\/][^\r\n"\']+|\\\\[^\\/\r\n"\']+[\\/][^\r\n"\']+)'
)

_SENSITIVE_JSON_FIELDS = re.compile(
    r'(?i)'
    r'("?(?:[^"\r\n]*:)?'
    r'(?:GPSLatitude|GPSLongitude|GPSPosition|CameraSerialNumber|SensorID|SerialNumber)'
    r'"?\s*:\s*)'
    r'(?:"[^"]*"|[-+]?\d+(?:\.\d+)?)'
)

_PATH_JSON_FIELDS = re.compile(
    r'(?i)("?(?:SourceFile|Directory)"?\s*:\s*)"[^"]*"'
)

def _sanitize_string(value: str, include_paths: bool, include_sensitive_metadata: bool) -> str:
    s = value
    if not include_paths:
        s = _PATH_JSON_FIELDS.sub(r'\1"<PATH_REDACTED>"', s)
        s = _WINDOWS_PATH_RE.sub("<PATH_REDACTED>", s)
    if not include_sensitive_metadata:
        s = _SENSITIVE_JSON_FIELDS.sub(r'\1"<SENSITIVE_REDACTED>"', s)
    return s

def _sanitize(value, include_paths: bool, include_sensitive_metadata: bool):
    if isinstance(value, dict):
        clean = {}
        for k, v in value.items():
            kl = str(k).lower()
            if not include_sensitive_metadata and any(
                token in kl for token in (
                    "gpslatitude", "gpslongitude", "gpsposition",
                    "cameraserialnumber", "sensorid", "serialnumber"
                )
            ):
                clean[k] = "<SENSITIVE_REDACTED>"
            elif not include_paths and kl in {"sourcefile", "directory", "path", "cwd"}:
                clean[k] = "<PATH_REDACTED>"
            else:
                clean[k] = _sanitize(v, include_paths, include_sensitive_metadata)
        return clean
    if isinstance(value, (list, tuple)):
        return [_sanitize(v, include_paths, include_sensitive_metadata) for v in value]
    if isinstance(value, str):
        return _sanitize_string(value, include_paths, include_sensitive_metadata)
    return value

class UsageLogger:
    def __init__(
        self,
        log_dir: Path,
        enabled: bool = True,
        include_paths: bool = False,
        diagnostic_mode: bool = False,
        include_sensitive_metadata: bool = False,
    ):
        self.enabled = enabled
        self.include_paths = include_paths
        self.diagnostic_mode = diagnostic_mode
        self.include_sensitive_metadata = include_sensitive_metadata
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.file = self.log_dir / f"usage_{datetime.date.today().isoformat()}.jsonl"

    @property
    def session_id(self):
        return _PROCESS_SESSION

    def event(self, event_type: str, **data):
        if not self.enabled:
            return
        record = {
            "ts": _now(),
            "session_id": _PROCESS_SESSION,
            "event": event_type,
            "data": _sanitize(
                data,
                self.include_paths,
                self.include_sensitive_metadata,
            ),
        }
        with _LOCK:
            with self.file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
