from pathlib import Path
from dpr360.pipeline.steps.raw_conversion import prepare_jpeg
from dpr360.process import run_process
from dpr360.scanning import list_tiffs

def smoke_test(source: Path,out_dir: Path,tools: dict,logger,live=None):
    out_dir.mkdir(parents=True,exist_ok=True)
    def run(step,args,timeout=1800):
        logger.event("smoke_command_start",step=step,command=[str(x) for x in args])
        r=run_process([str(x) for x in args],timeout=timeout,on_line=(lambda s,l: live(f"[{step}] {l}") if live else None))
        logger.event("smoke_command_end",step=step,returncode=r.returncode,stderr=r.stderr[-5000:])
        if r.returncode:raise RuntimeError(f"{step} fallito: {r.stderr}")
        return r
    meta=run("exiftool",[tools["exiftool"],"-json",source],180);(out_dir/"sample_metadata.json").write_text(meta.stdout,encoding="utf-8")
    tdir=out_dir/"tiff";tdir.mkdir(exist_ok=True)
    if source.suffix.lower() in {".jpg",".jpeg"}:
        prepare_jpeg(source,tdir/(source.stem+".tif"),tools.get("exiftool"))
    else:
        run("rawtherapee",[tools["rawtherapee"],"-o",tdir,"-b16","-tz","-Y","-c",source])
    tifs=[p for p in list_tiffs(tdir) if p.stem.lower()==source.stem.lower()]
    if not tifs:raise RuntimeError("La preparazione input non ha prodotto TIFF.")
    pto=out_dir/"sample.pto";run("pto_gen",[tools["pto_gen"],"-o",pto,tifs[0]],600)
    run("nona",[tools["nona"],"-m","TIFF_m","-o",out_dir/"sample_remap_",pto],1200)
    return True
