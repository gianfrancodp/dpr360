import ast
import logging
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
SCRIPT_CONTEXT_LOGGER = "streamlit.runtime.scriptrunner_utils.script_run_context"


def test_app_renders_without_exceptions(caplog):
    # Streamlit 1.62 warns while AppTest bootstraps its own SessionState before
    # a test ScriptRunContext exists. Keep that upstream test-only warning from
    # obscuring warnings emitted by the application itself.
    with caplog.at_level(logging.ERROR, logger=SCRIPT_CONTEXT_LOGGER):
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
