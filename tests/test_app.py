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


def test_jpeg_project_shows_count_and_is_ready_without_rawtherapee(tmp_path,monkeypatch,caplog):
    import dpr360.tools
    source=tmp_path/"source";source.mkdir()
    for index in range(33):
        (source/f"frame_{index:04}.JPG").write_bytes(b"not decoded during discovery")
    tool_names=("exiftool","pto_gen","cpfind","cpclean","autooptimiser","pano_modify","nona","enblend")
    monkeypatch.setattr(dpr360.tools,"detect_tools",lambda *args:{**{name:name for name in tool_names},"rawtherapee":""})
    with caplog.at_level(logging.ERROR,logger=SCRIPT_CONTEXT_LOGGER):
        app=AppTest.from_file(APP)
    app.session_state["source_dir"]=str(source)
    app.session_state["project_dir"]=str(tmp_path/"project")
    app.run(timeout=30)
    assert not app.exception
    metric=next(item for item in app.metric if item.label=="Fotogrammi sorgente")
    assert metric.value=="33"
    assert metric.delta=="JPEG"
    assert any(item.value=="Toolchain pronta" for item in app.success)
