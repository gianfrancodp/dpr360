import hashlib

import numpy as np
import pytest
import tifffile

from dpr360.gap_fill import ARTIFACTS, boundary_field, cached_report, export_fill
from dpr360.models import PipelineContext
from dpr360.pipeline.runner import PipelineRunner
from dpr360.pipeline.steps.gap_fill import GapFillStep


def master(path, dtype=np.uint8):
    maximum=np.iinfo(dtype).max
    color=np.array([101,141,181] if dtype==np.uint8 else [10001,25003,60011],dtype=dtype)
    image=np.empty((8,16,4),dtype=dtype)
    image[...,:3]=color;image[...,3]=maximum
    image[:3,:,3]=0
    image[:3,:,:3]=[maximum,0,0]  # Invalid hidden RGB must never contaminate colors.
    path.parent.mkdir(parents=True,exist_ok=True)
    tifffile.imwrite(path,image,photometric="rgb",extrasamples="unassalpha",compression="lzw",
                     extratags=[(34675,"B",7,b"fixture",False)])
    return image,color


@pytest.mark.parametrize("method",["boundary_mean","boundary_gradient"])
@pytest.mark.parametrize("dtype",[np.uint8,np.uint16])
def test_fill_retains_depth_pixels_profile_and_true_coverage(tmp_path,dtype,method):
    source=tmp_path/"master.tif";image,color=master(source,dtype)
    before=hashlib.sha256(source.read_bytes()).digest()
    output=tmp_path/"fill"
    report=export_fill(source,output,method)
    with tifffile.TiffFile(output/ARTIFACTS[0]) as tif:
        result=tif.asarray()
        assert tif.pages[0].tags[34675].value==b"fixture"
    assert result.dtype==dtype and result.shape==(8,16,3)
    np.testing.assert_array_equal(result,np.broadcast_to(color,result.shape))
    mask=tifffile.imread(output/"fill_mask.tif")
    np.testing.assert_array_equal(mask[:3],255)
    np.testing.assert_array_equal(mask[3:],0)
    assert report["original_coverage_percent"]==62.5
    assert report["display_coverage_percent"]==100
    assert report["uncovered_pixel_count"]==48
    assert report["opaque_photographic_pixels_unchanged"]
    assert report["bit_depth"]==np.dtype(dtype).itemsize*8
    assert hashlib.sha256(source.read_bytes()).digest()==before
    assert cached_report(source,output,method)==report
    progress=[]
    assert export_fill(source,output,method,lambda *event:progress.append(event))==report
    assert progress[-1][0]==1
    assert not list(output.glob(".fill-work-*"))


def test_component_means_keep_separate_sky_and_ground_colors():
    colors=np.zeros((8,16,3),np.float32)
    known=np.ones((8,16),bool)
    known[:2]=False;known[-2:]=False
    colors[2:4]=[.2,.5,.8];colors[4:6]=[.5,.3,.1]
    field=boundary_field(colors,known,"boundary_mean")
    np.testing.assert_allclose(field[0],np.tile([.2,.5,.8],(16,1)),atol=1e-6)
    np.testing.assert_allclose(field[-1],np.tile([.5,.3,.1],(16,1)),atol=1e-6)


def test_black_opaque_photographs_are_not_treated_as_gaps(tmp_path):
    source=tmp_path/"black.tif"
    image=np.zeros((8,16,4),np.uint8);image[...,3]=255
    tifffile.imwrite(source,image,photometric="rgb",extrasamples="unassalpha")
    report=export_fill(source,tmp_path/"fill")
    assert report["uncovered_pixel_count"]==0
    assert report["original_coverage_percent"]==100
    assert report["synthetic_fill"] is False
    assert not tifffile.imread(tmp_path/"fill/fill_mask.tif").any()
    assert not tifffile.imread(tmp_path/"fill/panorama_360_filled.tif").any()


def test_gradient_has_periodic_longitude_and_uniform_uncovered_pole():
    width=64
    colors=np.zeros((32,width,3),np.float32)
    colors[16:,:,0]=(np.sin(np.arange(width)*2*np.pi/width)+1)/2
    colors[16:,:,1:]=.5
    known=np.ones((32,width),bool);known[:16]=False
    field=boundary_field(colors,known,"boundary_gradient")
    np.testing.assert_array_equal(field[known],colors[known])
    np.testing.assert_allclose(field[0],np.broadcast_to(field[0,0],(width,3)),atol=1e-6)
    assert np.max(np.abs(field[:16,0]-field[:16,-1])) < .06
    assert np.isfinite(field).all()


@pytest.mark.parametrize("associated",[False,True])
def test_partial_alpha_is_composited_and_reported(tmp_path,associated):
    source=tmp_path/"master.tif";image,_=master(source)
    image[3,0,3]=128
    image[3,0,:3]=[50,70,90] if associated else [100,140,180]
    tifffile.imwrite(source,image,photometric="rgb",extrasamples="assocalpha" if associated else "unassalpha")
    report=export_fill(source,tmp_path/"fill")
    result=tifffile.imread(tmp_path/"fill"/ARTIFACTS[0])
    assert result[:3,:,0].mean() < 110  # Hidden saturated RGB was excluded.
    assert report["partial_alpha_pixel_count"]==1
    assert report["synthetic_pixel_count"]==49
    assert tifffile.imread(tmp_path/"fill/fill_mask.tif")[3,0]==127


def test_transparent_or_maskless_panorama_fails_without_fake_coverage(tmp_path):
    source=tmp_path/"master.tif"
    tifffile.imwrite(source,np.zeros((8,16,4),np.uint8),photometric="rgb",extrasamples="unassalpha")
    with pytest.raises(ValueError,match="entirely transparent"):
        export_fill(source,tmp_path/"fill")
    assert not (tmp_path/"fill/fill_report.json").exists()
    tifffile.imwrite(source,np.zeros((8,16,3),np.uint8),photometric="rgb")
    with pytest.raises(ValueError,match="alpha coverage"):
        export_fill(source,tmp_path/"fill")


def test_failed_replacement_keeps_previous_export_and_report(tmp_path,monkeypatch):
    source=tmp_path/"master.tif";master(source)
    output=tmp_path/"fill"
    report=export_fill(source,output)
    before={name:(output/name).read_bytes() for name in (*ARTIFACTS,"fill_report.json")}
    def fail(*args,**kwargs):
        raise OSError("simulated write failure")
    monkeypatch.setattr(tifffile,"imwrite",fail)
    with pytest.raises(OSError,match="simulated"):
        export_fill(source,output,"boundary_mean")
    assert {name:(output/name).read_bytes() for name in before}==before
    assert cached_report(source,output,"boundary_gradient")==report
    assert not list(output.glob(".fill-work-*"))


def test_fill_settings_invalidate_only_fill_checkpoint(tmp_path):
    class Logger:
        def event(self,*args,**kwargs): pass
    ctx=PipelineContext(tmp_path/"source",tmp_path/"project",{},
                        {"gap_fill":{"enabled":True,"method":"boundary_mean"}},Logger())
    ctx.source_dir.mkdir();master(ctx.final_tif)
    runner=PipelineRunner(ctx,[GapFillStep()])
    runner.state.set_result("final_validation","completed",{"returncode":0})
    assert runner.run_step("gap_fill").success
    assert runner.state.status("gap_fill")=="completed_with_warnings"
    ctx.config["gap_fill"]["method"]="boundary_gradient"
    resumed=PipelineRunner(ctx,[GapFillStep()])
    assert resumed.state.status("gap_fill")=="pending"
    assert resumed.state.status("final_validation")=="completed"
    assert resumed.run_step("gap_fill").success
    ctx.config["gap_fill"]["enabled"]=False
    disabled=PipelineRunner(ctx,[GapFillStep()])
    result=disabled.run_step("gap_fill")
    assert result.success and not result.outputs
    assert result.details["settings"]["enabled"] is False
