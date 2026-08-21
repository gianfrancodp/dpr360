from pathlib import Path
import argparse
from dpr360.settings import load_config
from dpr360.logger import UsageLogger
from dpr360.tools import detect_tools, install_exiftool_official, install_winget
import os
ROOT=Path(os.environ.get("DPR360_HOME", Path(__file__).resolve().parent)).resolve()

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--auto",action="store_true");args=ap.parse_args()
    cfg=load_config(ROOT);logger=UsageLogger(ROOT/"logs",True,False)
    tools=detect_tools(ROOT,cfg)
    print("\n=== DronePanoRAW 360 · dipendenze ===")
    if args.auto and not tools.get("exiftool"):
        try: print("Installazione ExifTool portable...");install_exiftool_official(ROOT,logger)
        except Exception as e: print("  ExifTool: fallback manuale:",e)
    tools=detect_tools(ROOT,cfg)
    if args.auto and not tools.get("rawtherapee"):
        ok,msg=install_winget(cfg.get("winget",{}).get("rawtherapee_id","RawTherapee.RawTherapee"),logger=logger,tool="rawtherapee")
        if not ok: print("  RawTherapee: fallback manuale:",msg[-800:])
    tools=detect_tools(ROOT,cfg)
    if args.auto and not tools.get("pto_gen"):
        ok,msg=install_winget(name="Hugin",logger=logger,tool="hugin")
        if not ok: print("  Hugin: fallback manuale:",msg[-800:])
    tools=detect_tools(ROOT,cfg)
    for k,v in tools.items(): print(f"  {k:14}: {v or 'MANCANTE'}")
    missing=[k for k,v in tools.items() if not v]
    print("\nToolchain completa." if not missing else "\nToolchain parziale; usa la scheda Tool Windows per il fallback.")
    return 0
if __name__=="__main__":raise SystemExit(main())
