import json
import tempfile
from pathlib import Path

from PIL import Image

from dpr360.models import PipelineContext
from dpr360.pipeline.steps.metadata import MetadataStep
from dpr360.pipeline.steps.pto_gen import PtoGenStep
from dpr360.pipeline.steps.raw_conversion import RawConversionStep, list_working_tiffs
from dpr360.process import ProcessResult
from dpr360.scanning import discover_source_set


class Logger:
    def event(self,*args,**kwargs):
        pass


def make_context(root):
    source=root/"source";project=root/"project"
    source.mkdir();project.mkdir()
    return PipelineContext(source,project,{"exiftool":"exiftool","pto_gen":"pto_gen"}, {}, Logger())


def test_jpeg_preparation_creates_isolated_lossless_tiff_with_exif():
    with tempfile.TemporaryDirectory() as td:
        ctx=make_context(Path(td))
        exif=Image.Exif();exif[37386]=(24,1)
        jpeg=ctx.source_dir/"frame.JPG"
        Image.new("RGB",(32,16),(10,20,30)).save(jpeg,format="JPEG",exif=exif)

        result=RawConversionStep().run(ctx)

        assert result.success
        assert result.has_warnings
        assert result.details["input_format"]=="jpeg"
        source=discover_source_set(ctx.source_dir)
        outputs=list_working_tiffs(ctx,source)
        assert len(outputs)==1
        assert outputs[0].parent==ctx.tiff_dir/"jpeg"
        with Image.open(outputs[0]) as converted:
            assert converted.format=="TIFF"
            assert converted.size==(32,16)
            assert converted.getexif().get(37386)==(24,1)


def test_metadata_step_warns_when_jpeg_lacks_dji_orientation_fields():
    with tempfile.TemporaryDirectory() as td:
        ctx=make_context(Path(td))
        (ctx.source_dir/"frame.jpeg").write_bytes(b"jpeg")
        step=MetadataStep()
        payload=[{"EXIF:FileName":"frame.jpeg","EXIF:FocalLength":"24 mm"}]
        step.command=lambda *args,**kwargs: ProcessResult(0,json.dumps(payload),"",0.01)

        result=step.run(ctx)

        assert result.success
        assert result.has_warnings
        assert "GimbalYawDegree" in result.warnings[0]
        assert result.details=={"source_count":1,"input_format":"jpeg"}
        assert (ctx.metadata_dir/"metadata_full.json").is_file()
        assert (ctx.metadata_dir/"panorama_metadata.csv").is_file()


def test_pto_generation_uses_only_current_jpeg_working_files():
    with tempfile.TemporaryDirectory() as td:
        ctx=make_context(Path(td));ctx.hugin_dir.mkdir()
        jpeg=ctx.source_dir/"frame.jpg"
        Image.new("RGB",(16,8)).save(jpeg)
        prepared=RawConversionStep().run(ctx)
        assert prepared.success
        ctx.tiff_dir.joinpath("stale-dng.tif").write_bytes(b"stale")

        calls=[]
        step=PtoGenStep()
        step.command=lambda _ctx,args,**kwargs: (calls.append(args) or ProcessResult(0,"","",0.01))
        result=step.run(ctx)

        assert result.success
        image_args=[Path(arg) for arg in calls[0] if str(arg).lower().endswith((".tif",".tiff"))]
        assert image_args==[ctx.tiff_dir/"jpeg"/"frame.tif"]
