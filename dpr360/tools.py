from __future__ import annotations
from pathlib import Path
import os, re, shutil, subprocess, tempfile, zipfile
import requests

HUGIN_TOOLS = ["pto_gen", "cpfind", "cpclean", "autooptimiser", "pano_modify", "nona", "enblend"]

def _existing(path: str | Path | None):
    if path and Path(path).is_file(): return Path(path)
    return None

def _which(name):
    p = shutil.which(name)
    return Path(p) if p else None

def _first(patterns):
    for pattern in patterns:
        try:
            hits = sorted(Path().glob(pattern)) if False else []
        except Exception:
            hits = []
        if hits: return hits[0]
    return None

def _glob_roots(roots, relative_patterns):
    for root in roots:
        if not root: continue
        rp = Path(root)
        if not rp.exists(): continue
        for pat in relative_patterns:
            try:
                for p in sorted(rp.glob(pat)):
                    if p.is_file(): return p
            except OSError:
                pass
    return None

def detect_tools(project_root: Path, cfg: dict) -> dict[str, str]:
    configured = cfg.get("tools", {})
    result = {}

    # 1 configured -> 2 local tools -> 3 PATH -> 4 standard/versioned folders
    ex = _existing(configured.get("exiftool"))
    if not ex:
        ex = _existing(project_root / "tools" / "exiftool" / "exiftool.exe")
    if not ex: ex = _which("exiftool")
    result["exiftool"] = str(ex or "")

    rt = _existing(configured.get("rawtherapee"))
    if not rt: rt = _which("rawtherapee-cli")
    if not rt:
        rt = _glob_roots(
            [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")],
            ["RawTherapee*/rawtherapee-cli.exe", "RawTherapee*/**/rawtherapee-cli.exe"],
        )
    result["rawtherapee"] = str(rt or "")

    hugin_bin = configured.get("hugin_bin", "")
    roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")]
    for name in HUGIN_TOOLS:
        p = _existing(Path(hugin_bin) / f"{name}.exe") if hugin_bin else None
        if not p: p = _which(name)
        if not p:
            p = _glob_roots(roots, [f"Hugin*/bin/{name}.exe", f"Hugin*/**/{name}.exe"])
        result[name] = str(p or "")
    return result

def run_simple(args, timeout=900):
    return subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=timeout, shell=False)

def test_exiftool(path: str):
    if not path or not Path(path).exists(): return False, "missing"
    r = run_simple([path, "-ver"], 60)
    return r.returncode == 0, (r.stdout or r.stderr).strip()

def install_exiftool_official(project_root: Path, logger=None) -> str:
    if logger: logger.event("install_attempt", tool="exiftool", method="official_portable")
    page_url = "https://exiftool.org/"
    page = requests.get(page_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    page.raise_for_status()
    candidates = re.findall(r'href=["\']([^"\']*exiftool[^"\']*\.zip)["\']', page.text, flags=re.I)
    if not candidates:
        raise RuntimeError("Impossibile individuare lo ZIP Windows di ExifTool nella pagina ufficiale.")
    candidates = sorted(set(candidates), key=lambda u: ("64" not in u.lower(), "win" not in u.lower(), u))
    href = candidates[0]
    if href.startswith("http"): url = href
    elif href.startswith("/"): url = "https://exiftool.org" + href
    else: url = "https://exiftool.org/" + href

    with tempfile.TemporaryDirectory() as td:
        td = Path(td); zpath = td / "exiftool.zip"; extracted = td / "extracted"; extracted.mkdir()
        with requests.get(url, timeout=90, stream=True, headers={"User-Agent": "Mozilla/5.0"}) as r:
            r.raise_for_status()
            with zpath.open("wb") as f:
                for chunk in r.iter_content(1024*1024):
                    if chunk: f.write(chunk)
        with zipfile.ZipFile(zpath) as z: z.extractall(extracted)
        target = project_root / "tools" / "exiftool"
        if target.exists(): shutil.rmtree(target)
        target.mkdir(parents=True)
        # flatten a single wrapper directory, otherwise preserve payload
        children = list(extracted.iterdir())
        source_root = children[0] if len(children) == 1 and children[0].is_dir() else extracted
        for child in source_root.iterdir():
            dst = target / child.name
            if child.is_dir(): shutil.copytree(child, dst)
            else: shutil.copy2(child, dst)
        exe = next((p for p in target.rglob("*.exe") if p.name.lower().startswith("exiftool")), None)
        if not exe: raise RuntimeError("exiftool(-k).exe non trovato nel pacchetto scaricato.")
        final = target / "exiftool.exe"
        if exe.resolve() != final.resolve():
            if final.exists(): final.unlink()
            shutil.move(str(exe), str(final))
    ok, msg = test_exiftool(str(final))
    if logger: logger.event("install_result", tool="exiftool", ok=ok, message=msg)
    if not ok: raise RuntimeError(f"Test ExifTool fallito dopo l'installazione: {msg}")
    return str(final)

def install_winget(package_id: str = "", name: str = "", logger=None, tool=""):
    if not shutil.which("winget"): return False, "WinGet non disponibile"
    cmd = ["winget", "install"]
    if package_id: cmd += ["--id", package_id, "-e"]
    elif name: cmd += ["--name", name, "-e"]
    else: return False, "Package non specificato"
    cmd += ["--accept-source-agreements", "--accept-package-agreements"]
    if logger: logger.event("install_attempt", tool=tool or package_id or name, method="winget")
    r = run_simple(cmd, 1200)
    msg = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
    ok = r.returncode == 0
    if logger: logger.event("install_result", tool=tool or package_id or name, ok=ok, message=msg[-6000:])
    return ok, msg
