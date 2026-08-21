# Building DPR360

## Source/development environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Windows application package

The PyInstaller build embeds Python and the DPR360/Streamlit application. It deliberately does **not** bundle RawTherapee, Hugin/Enblend or ExifTool.

```powershell
py -3.13 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install --upgrade pip
.\.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean dpr360.spec
.\dist\dpr360\dpr360.exe --version
```

The distributable directory is `dist/dpr360/`.

## External-tool validation

A successful application build only verifies the DPR360 package. End-to-end panorama processing additionally requires working installations of RawTherapee, Hugin/Enblend and ExifTool on the target Windows machine.
