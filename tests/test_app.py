import ast
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


def test_app_renders_without_exceptions():
    app = AppTest.from_file(APP)
    app.run(timeout=30)

    assert not app.exception
    assert [title.value for title in app.title] == ["DronePanoRAW 360"]


def test_app_does_not_use_deprecated_container_width_keyword():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    deprecated = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword) and node.arg == "use_container_width"
    ]

    assert deprecated == []
