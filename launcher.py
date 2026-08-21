from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import shutil

from dpr360 import __version__


def bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="DronePanoRAW 360 launcher")
    parser.add_argument("--version", action="store_true", help="print DPR360 version and exit")
    parser.add_argument("--headless", action="store_true", help="run Streamlit without opening a browser")
    args = parser.parse_args()

    if args.version:
        print(f"DPR360 {__version__}")
        return 0

    home = bundle_root()
    resources = resource_root()
    os.environ.setdefault("DPR360_HOME", str(home))
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    # PyInstaller keeps bundled data under its resource directory. DPR360 runtime
    # state must live beside the executable, so seed a user-editable config there.
    default_config = resources / "config.yaml"
    runtime_config = home / "config.yaml"
    if default_config.exists() and not runtime_config.exists():
        shutil.copy2(default_config, runtime_config)

    app_path = resources / "app.py"
    if not app_path.exists():
        raise SystemExit(f"Bundled app.py not found: {app_path}")

    import streamlit.web.cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
        f"--server.headless={'true' if args.headless else 'false'}",
    ]
    return int(stcli.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
