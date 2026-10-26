from pathlib import Path

from PIL import Image

from dpr360.process import ProcessResult
from dpr360.smoke import smoke_test


def test_jpeg_smoke_uses_selected_output_instead_of_stale_tiff(tmp_path,monkeypatch):
    source=tmp_path/"selected.jpg"
    Image.new("RGB",(8,4)).save(source)
    output=tmp_path/"smoke"
    working=output/"tiff";working.mkdir(parents=True)
    Image.new("RGB",(8,4)).save(working/"aaa_stale.tif")
    calls=[]
    def fake_prepare(src,target,exiftool):
        Image.new("RGB",(8,4)).save(target)
    def fake_run(args,**kwargs):
        calls.append(args)
        return ProcessResult(0,"[]","",0)
    monkeypatch.setattr("dpr360.smoke.prepare_jpeg",fake_prepare)
    monkeypatch.setattr("dpr360.smoke.run_process",fake_run)
    class Logger:
        def event(self,*args,**kwargs): pass
    assert smoke_test(source,output,{"exiftool":"exiftool","pto_gen":"pto_gen","nona":"nona"},Logger())
    pto_call=next(args for args in calls if args[0]=="pto_gen")
    assert Path(pto_call[-1])==working/"selected.tif"
