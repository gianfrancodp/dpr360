import argparse
import os
from pathlib import Path

from dpr360.settings import load_config
from dpr360.logger import UsageLogger
from dpr360.tools import detect_tools, install_exiftool_official, install_winget

ROOT = Path(os.environ.get("DPR360_HOME", Path(__file__).resolve().parent)).resolve()
PARTIAL_TOOLCHAIN_EXIT_CODE = 3


def _print_status(tools):
    for name, path in tools.items():
        print(f"  {name:14}: {path or 'MANCANTE'}")
    return [name for name, path in tools.items() if not path]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(ROOT)
    logger = UsageLogger(ROOT / "logs", True, False)
    tools = detect_tools(ROOT, cfg)
    errors = []
    print("\n=== DronePanoRAW 360 · dipendenze ===")
    if args.auto and not tools.get("exiftool"):
        try:
            print("Installazione ExifTool portable...")
            install_exiftool_official(ROOT, logger)
        except Exception as exc:
            errors.append(f"ExifTool: {exc}")
            print("  ExifTool: fallback manuale:", exc)
    tools = detect_tools(ROOT, cfg)
    if args.auto and not tools.get("rawtherapee"):
        ok, message = install_winget(
            cfg.get("winget", {}).get("rawtherapee_id", "RawTherapee.RawTherapee"),
            logger=logger,
            tool="rawtherapee",
        )
        if not ok:
            errors.append(f"RawTherapee: {message[-800:]}")
            print("  RawTherapee: fallback manuale:", message[-800:])
    tools = detect_tools(ROOT, cfg)
    if args.auto and not tools.get("pto_gen"):
        ok, message = install_winget(name="Hugin", logger=logger, tool="hugin")
        if not ok:
            errors.append(f"Hugin: {message[-800:]}")
            print("  Hugin: fallback manuale:", message[-800:])
    tools = detect_tools(ROOT, cfg)
    missing = _print_status(tools)
    if missing:
        print("\nToolchain parziale. Mancano: " + ", ".join(missing))
        print("Usa la scheda Tool Windows o configura i percorsi manualmente.")
        if errors:
            print("Problemi rilevati durante il setup:")
            for error in errors:
                print("  - " + error)
        return PARTIAL_TOOLCHAIN_EXIT_CODE
    print("\nToolchain completa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
