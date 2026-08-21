from __future__ import annotations
from pathlib import Path

def _root():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    return root

def choose_directory(initial: str = "") -> str:
    try:
        from tkinter import filedialog
        root = _root()
        value = filedialog.askdirectory(initialdir=initial or None, mustexist=True)
        root.destroy()
        return value or ""
    except Exception:
        return ""

def choose_file(initial: str = "", filetypes=None) -> str:
    try:
        from tkinter import filedialog
        root = _root()
        initialdir = str(Path(initial).parent) if initial and Path(initial).suffix else (initial or None)
        value = filedialog.askopenfilename(initialdir=initialdir, filetypes=filetypes or [("All files", "*.*")])
        root.destroy()
        return value or ""
    except Exception:
        return ""
