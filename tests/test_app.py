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


def test_existing_master_can_be_filled_without_source_or_external_tools(tmp_path,monkeypatch,caplog):
    import hashlib
    import numpy as np
    import tifffile
    import dpr360.tools
    project=tmp_path/"project";folder=project/"03_hugin";folder.mkdir(parents=True)
    master=folder/"panorama_360_finale.tif"
    pixels=np.full((8,16,4),128,np.uint8);pixels[...,3]=255;pixels[:2,:,3]=0
    tifffile.imwrite(master,pixels,photometric="rgb",extrasamples="unassalpha")
    before=hashlib.sha256(master.read_bytes()).digest()
    monkeypatch.setattr(dpr360.tools,"detect_tools",lambda *args:{})
    with caplog.at_level(logging.ERROR,logger=SCRIPT_CONTEXT_LOGGER):
        app=AppTest.from_file(APP)
    app.session_state["project_dir"]=str(project)
    app.session_state["gap_fill_enabled"]=True
    app.run(timeout=30)
    assert not app.exception
    app.button(key="generate_gap_fill").click().run(timeout=30)
    assert not app.exception
    assert (project/"04_fill/panorama_360_filled.tif").exists()
    assert (project/"04_fill/fill_mask.tif").exists()
    assert hashlib.sha256(master.read_bytes()).digest()==before
