# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

streamlit_datas, streamlit_binaries, streamlit_hidden = collect_all("streamlit")

project_datas = [
    ("app.py", "."),
    ("config.yaml", "."),
    ("README.md", "."),
    ("LICENSE", "."),
    ("COPYRIGHT", "."),
    ("THIRD_PARTY_NOTICES.md", "."),
    (".streamlit/config.toml", ".streamlit"),
]

hiddenimports = streamlit_hidden + collect_submodules("dpr360") + [
    "yaml",
    "PIL",
    "tkinter",
]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=streamlit_binaries,
    datas=streamlit_datas + project_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="dpr360",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="dpr360",
)
