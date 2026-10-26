import json
import tempfile
import shutil
from pathlib import Path

import pytest
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from dpr360.jpeg import prepare_jpeg

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


def test_jpeg_preparation_creates_isolated_lossless_tiff_with_exif(monkeypatch):
    commands=[]
    monkeypatch.setattr("dpr360.jpeg.run_process",lambda args,**kw: (commands.append(args) or ProcessResult(0,"","",0)))
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
            converted.load()
        assert "-FocalLength" in commands[0]
        assert "-n" in commands[0]


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


def test_pto_generation_uses_only_current_jpeg_working_files(monkeypatch):
    monkeypatch.setattr("dpr360.jpeg.run_process",lambda *args,**kw: ProcessResult(0,"","",0))
    with tempfile.TemporaryDirectory() as td:
        ctx=make_context(Path(td));ctx.hugin_dir.mkdir()
        jpeg=ctx.source_dir/"frame.jpg"
        Image.new("RGB",(16,8)).save(jpeg)
        prepared=RawConversionStep().run(ctx)
        assert prepared.success
        ctx.tiff_dir.joinpath("stale-dng.tif").write_bytes(b"stale")
        (ctx.tiff_dir/"jpeg"/"frame.tiff").write_bytes(b"stale alternative extension")

        calls=[]
        step=PtoGenStep()
        step.command=lambda _ctx,args,**kwargs: (calls.append(args) or ProcessResult(0,"","",0.01))
        result=step.run(ctx)

        assert result.success
        image_args=[Path(arg) for arg in calls[0] if str(arg).lower().endswith((".tif",".tiff"))]
        assert image_args==[ctx.tiff_dir/"jpeg"/"frame.tif"]


def nested_jpeg(path, orientation=1):
    exif=Image.Exif()
    exif[271]="Synthetic camera"
    exif[272]="Regression fixture"
    exif[274]=orientation
    exif[34665]={37386:IFDRational(672,100),41989:24,40962:32,40963:16}
    image=Image.new("RGB",(32,16),"red")
    image.paste("blue",(0,0,16,16))
    image.save(path,exif=exif,icc_profile=b"synthetic-profile")


def test_nested_exif_is_not_passed_to_compressed_tiff_writer(tmp_path,monkeypatch):
    from PIL import ImageOps
    source=tmp_path/"nested.jpg";target=tmp_path/"result.tif"
    nested_jpeg(source,orientation=6)
    calls=[]
    monkeypatch.setattr("dpr360.jpeg.run_process",lambda args,**kw: (calls.append(args) or ProcessResult(0,"","",0)))
    prepare_jpeg(source,target,"exiftool")
    with Image.open(source) as original,Image.open(target) as prepared:
        assert prepared.size==(16,32)
        assert prepared.tobytes()==ImageOps.exif_transpose(original).convert("RGB").tobytes()
        assert prepared.info["icc_profile"]==b"synthetic-profile"
    assert "-Orientation#=1" in calls[0]
    assert "-ExifImageWidth=16" in calls[0]
    assert "-ExifImageHeight=32" in calls[0]
    assert "-GPS:all" not in calls[0]


def test_failed_metadata_write_preserves_destination_and_cleans_temporary(tmp_path,monkeypatch):
    source=tmp_path/"nested.jpg";target=tmp_path/"result.tif"
    nested_jpeg(source)
    Image.new("RGB",(7,5),"green").save(target)
    previous=target.read_bytes()
    monkeypatch.setattr("dpr360.jpeg.run_process",lambda *args,**kw: ProcessResult(1,"","metadata failure",0))
    with pytest.raises(RuntimeError,match="metadata failure"):
        prepare_jpeg(source,target,"exiftool")
    assert target.read_bytes()==previous
    assert not list(tmp_path.glob(".jpeg-*"))
    target.unlink()
    with pytest.raises(RuntimeError):
        prepare_jpeg(source,target,"exiftool")
    assert not target.exists()


@pytest.mark.skipif(not shutil.which("exiftool"),reason="optional real ExifTool integration")
def test_real_exiftool_preserves_nested_lens_values_and_normalizes_orientation(tmp_path):
    source=tmp_path/"nested.jpg";target=tmp_path/"result.tif"
    nested_jpeg(source,orientation=6)
    prepare_jpeg(source,target)
    with Image.open(target) as image:
        exif=image.getexif();photo=exif.get_ifd(34665)
        assert float(photo[37386])==6.72
        assert photo[41989]==24
        assert (photo[40962],photo[40963])==(16,32)
        assert exif[274]==1
        assert exif[272]=="Regression fixture"


def test_preparation_rebuilds_truncated_and_changed_sources(tmp_path,monkeypatch):
    ctx=make_context(tmp_path)
    calls=[]
    monkeypatch.setattr("dpr360.jpeg.run_process",lambda args,**kw: (calls.append(args) or ProcessResult(0,"","",0)))
    source=ctx.source_dir/"frame.jpg"
    nested_jpeg(source)
    step=RawConversionStep()
    assert step.run(ctx).success
    assert len(calls)==1
    assert step.run(ctx).success
    assert len(calls)==1
    output=ctx.tiff_dir/"jpeg"/"frame.tif"
    output.write_bytes(b"truncated")
    assert step.run(ctx).success
    assert len(calls)==2
    Image.new("RGB",(40,20)).save(source)
    assert step.run(ctx).success
    assert len(calls)==3
    with Image.open(output) as image:
        assert image.size==(40,20)


def test_preparation_rejects_duplicate_source_stems(tmp_path):
    ctx=make_context(tmp_path)
    Image.new("RGB",(8,8)).save(ctx.source_dir/"frame.jpg")
    Image.new("RGB",(8,8)).save(ctx.source_dir/"frame.jpeg")
    result=RawConversionStep().run(ctx)
    assert not result.success
    assert result.returncode==6


def test_dng_preparation_retains_rawtherapee_16bit_profile_and_directory(tmp_path):
    ctx=make_context(tmp_path)
    ctx.tools["rawtherapee"]="rawtherapee-cli"
    ctx.config={"pipeline":{"raw_profile":"custom.pp3"}}
    source=ctx.source_dir/"frame.DNG";source.write_bytes(b"synthetic raw")
    calls=[]
    step=RawConversionStep()
    def command(_ctx,args,**kwargs):
        calls.append(args)
        Image.new("RGB",(8,4)).save(ctx.tiff_dir/"frame.tif")
        return ProcessResult(0,"","",0)
    step.command=command
    result=step.run(ctx)
    assert result.success and not result.warnings
    assert calls==[["rawtherapee-cli","-o",str(ctx.tiff_dir),"-b16","-tz","-Y","-p","custom.pp3","-c",str(source)]]
    assert result.outputs==[str(ctx.tiff_dir/"frame.tif")]
