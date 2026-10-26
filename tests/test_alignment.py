import pytest

from dpr360.models import PipelineContext
from dpr360.pipeline.steps.pto_validation import PtoValidationStep
from dpr360.pto import control_point_connectivity


def test_valid_canvas_does_not_hide_disconnected_alignment(tmp_path):
    ctx=PipelineContext(tmp_path,tmp_path,{}, {},None)
    ctx.hugin_dir.mkdir()
    pto=ctx.hugin_dir/"project_360.pto"
    pto.write_text("p f2 w100 h50 v360 S0,100,0,50\ni w40 h30\ni w40 h30\ni w40 h30\nc n0 N1 x1 y1 X2 Y2 t0\n")
    result=PtoValidationStep().run(ctx)
    assert result.success and result.warnings
    assert result.details["valid"]
    assert not result.details["alignment_connected"]
    assert result.details["alignment_components"]==[[0,1],[2]]
    with pto.open("a") as stream:
        stream.write("c n1 N2 x1 y1 X2 Y2 t0\n")
    result=PtoValidationStep().run(ctx)
    assert result.success and not result.warnings
    assert result.details["alignment_connected"]


def test_invalid_control_point_indices_are_rejected(tmp_path):
    pto=tmp_path/"invalid.pto"
    pto.write_text("i w40 h30\nc n0 N9 x1 y1 X2 Y2 t0\n")
    with pytest.raises(ValueError,match="image index"):
        control_point_connectivity(pto)
