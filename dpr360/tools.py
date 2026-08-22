from __future__ import annotations
from pathlib import Path
import os, re, shutil, subprocess, tempfile, zipfile
from urllib.parse import urljoin, urlparse
from uuid import uuid4
import requests
from dpr360.process import external_process_env

HUGIN_TOOLS = ["pto_gen", "cpfind", "cpclean", "autooptimiser", "pano_modify", "nona", "enblend"]
EXIFTOOL_DOWNLOAD_LIMIT = 128 * 1024 * 1024
EXIFTOOL_WINDOWS_ARCHIVE = re.compile(
    r"(?:^|/)exiftool-(?P<version>\d+(?:\.\d+)*)_64\.zip(?:/download)?/?$",
    flags=re.I,
)
EXIFTOOL_DOWNLOAD_HOSTS = {"exiftool.org", "www.exiftool.org", "sourceforge.net", "www.sourceforge.net"}

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
    return subprocess.run(
        [str(x) for x in args],
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        env=external_process_env(),
    )

def test_exiftool(path: str):
    if not path or not Path(path).exists(): return False, "missing"
    r = run_simple([path, "-ver"], 60)
    return r.returncode == 0, (r.stdout or r.stderr).strip()

def _find_exiftool_windows_url(page_text: str, page_url: str) -> str:
    candidates = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', page_text, flags=re.I):
        url = urljoin(page_url, href)
        parsed = urlparse(url)
        if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in EXIFTOOL_DOWNLOAD_HOSTS:
            continue
        match = EXIFTOOL_WINDOWS_ARCHIVE.search(parsed.path)
        if not match:
            continue
        version = tuple(int(part) for part in match.group("version").split("."))
        candidates.append((version, url))
    if not candidates:
        raise RuntimeError("Impossibile individuare lo ZIP Windows 64-bit di ExifTool nella pagina ufficiale.")
    return max(candidates, key=lambda item: item[0])[1]

def _safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.infolist():
        member_path = (root / member.filename).resolve()
        if member_path != root and root not in member_path.parents:
            raise RuntimeError(f"Percorso non sicuro nell'archivio ExifTool: {member.filename}")
    archive.extractall(root)

def _download_exiftool_archive(url: str, destination: Path) -> None:
    downloaded = 0
    with requests.get(url, timeout=(30, 120), stream=True, headers={"User-Agent": "DPR360"}) as response:
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > EXIFTOOL_DOWNLOAD_LIMIT:
            raise RuntimeError("Il pacchetto ExifTool supera la dimensione massima consentita.")
        with destination.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > EXIFTOOL_DOWNLOAD_LIMIT:
                    raise RuntimeError("Il pacchetto ExifTool supera la dimensione massima consentita.")
                output.write(chunk)
    if not downloaded or not zipfile.is_zipfile(destination):
        raise RuntimeError("Il download ExifTool non è un archivio ZIP valido.")


def install_exiftool_official(project_root: Path, logger=None) -> str:
    if logger: logger.event("install_attempt", tool="exiftool", method="official_portable")
    try:
        page_url = "https://exiftool.org/"
        page = requests.get(page_url, timeout=30, headers={"User-Agent": "DPR360"})
        page.raise_for_status()
        url = _find_exiftool_windows_url(page.text, page_url)

        tools_root = project_root / "tools"
        tools_root.mkdir(parents=True, exist_ok=True)
        target = tools_root / "exiftool"
        with tempfile.TemporaryDirectory(prefix=".exiftool-staging-", dir=tools_root) as td:
            staging = Path(td)
            zpath = staging / "exiftool.zip"
            extracted = staging / "extracted"
            install_root = staging / "install"
            extracted.mkdir()
            install_root.mkdir()
            _download_exiftool_archive(url, zpath)
            with zipfile.ZipFile(zpath) as archive:
                _safe_extract_zip(archive, extracted)

            children = list(extracted.iterdir())
            source_root = children[0] if len(children) == 1 and children[0].is_dir() else extracted
            for child in source_root.iterdir():
                destination = install_root / child.name
                if child.is_dir(): shutil.copytree(child, destination)
                else: shutil.copy2(child, destination)

            exe = next((p for p in install_root.rglob("*.exe") if p.name.lower().startswith("exiftool")), None)
            if not exe:
                raise RuntimeError("exiftool(-k).exe non trovato nel pacchetto scaricato.")
            if not (install_root / "exiftool_files").is_dir():
                raise RuntimeError("Cartella exiftool_files non trovata nel pacchetto scaricato.")
            staged_exe = install_root / "exiftool.exe"
            if exe.resolve() != staged_exe.resolve():
                shutil.move(str(exe), str(staged_exe))

            ok, message = test_exiftool(str(staged_exe))
            if not ok:
                raise RuntimeError(f"Test ExifTool fallito dopo l'installazione: {message}")

            backup = tools_root / f".exiftool-backup-{uuid4().hex}"
            try:
                if target.exists(): target.rename(backup)
                install_root.rename(target)
            except Exception:
                if backup.exists():
                    if target.exists(): shutil.rmtree(target)
                    backup.rename(target)
                raise
            else:
                if backup.exists(): shutil.rmtree(backup)

        final = target / "exiftool.exe"
        if logger: logger.event("install_result", tool="exiftool", ok=True, message=message)
        return str(final)
    except Exception as exc:
        if logger: logger.event("install_result", tool="exiftool", ok=False, message=str(exc))
        raise

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
