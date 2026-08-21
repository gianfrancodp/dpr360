from io import BytesIO
from pathlib import Path
import zipfile

import pytest

from dpr360 import tools


class FakeResponse:
    def __init__(self, *, text="", body=b"", status=200):
        self.text = text
        self.body = body
        self.status = status
        self.headers = {"Content-Length": str(len(body))} if body else {}

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def iter_content(self, _chunk_size):
        yield self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def make_exiftool_zip() -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("exiftool-13.59_64/exiftool(-k).exe", b"fake executable")
        archive.writestr("exiftool-13.59_64/exiftool_files/keep.txt", b"support files")
    return output.getvalue()


def test_find_exiftool_windows_url_ignores_unrelated_archives():
    page = """
    <a href="/ExifToolWrapper.zip">wrapper</a>
    <a href="https://sourceforge.net/projects/exiftool/files/exiftool-13.58_64.zip/download">old</a>
    <a href="https://sourceforge.net/projects/exiftool/files/exiftool-13.59_64.zip/download">current</a>
    """
    assert tools._find_exiftool_windows_url(page, "https://exiftool.org/").endswith(
        "exiftool-13.59_64.zip/download"
    )


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="Percorso non sicuro"):
            tools._safe_extract_zip(archive, tmp_path / "extract")


def test_install_exiftool_is_transactional(monkeypatch, tmp_path):
    page = '<a href="https://sourceforge.net/projects/exiftool/files/exiftool-13.59_64.zip/download">64-bit</a>'
    responses = iter([FakeResponse(text=page), FakeResponse(body=make_exiftool_zip())])
    monkeypatch.setattr(tools.requests, "get", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(tools, "test_exiftool", lambda _path: (True, "13.59"))

    installed = Path(tools.install_exiftool_official(tmp_path))

    assert installed.name == "exiftool.exe"
    assert installed.read_bytes() == b"fake executable"
    assert (installed.parent / "exiftool_files" / "keep.txt").is_file()


def test_failed_download_preserves_existing_install(monkeypatch, tmp_path):
    target = tmp_path / "tools" / "exiftool"
    target.mkdir(parents=True)
    existing = target / "exiftool.exe"
    existing.write_bytes(b"working version")
    page = '<a href="https://sourceforge.net/projects/exiftool/files/exiftool-13.59_64.zip/download">64-bit</a>'
    responses = iter([FakeResponse(text=page), FakeResponse(body=b"not a zip")])
    monkeypatch.setattr(tools.requests, "get", lambda *_args, **_kwargs: next(responses))

    with pytest.raises(RuntimeError, match="ZIP valido"):
        tools.install_exiftool_official(tmp_path)

    assert existing.read_bytes() == b"working version"
