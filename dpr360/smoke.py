from pathlib import Path
from dpr360.process import run_process

def smoke_test(dng: Path,out_dir: Path,tools: dict,logger,live=None):
    out_dir.mkdir(parents=True,exist_ok=True)
    def run(step,args,timeout=1800):
        logger.event("smoke_command_start",step=step,command=[str(x) for x in args])
        r=run_process([str(x) for x in args],timeout=timeout,on_line=(lambda s,l: live(f"[{step}] {l}") if live else None))
        logger.event("smoke_command_end",step=step,returncode=r.returncode,stderr=r.stderr[-5000:])
        if r.returncode:raise RuntimeError(f"{step} fallito: {r.stderr}")
        return r
    meta=run("exiftool",[tools["exiftool"],"-json",dng],180);(out_dir/"sample_metadata.json").write_text(meta.stdout,encoding="utf-8")
    tdir=out_dir/"tiff";tdir.mkdir(exist_ok=True)
    run("rawtherapee",[tools["rawtherapee"],"-o",tdir,"-b16","-tz","-Y","-c",dng])
    tifs=list(tdir.glob("*.tif"))+list(tdir.glob("*.tiff"))
    if not tifs:raise RuntimeError("RawTherapee non ha prodotto TIFF.")
    pto=out_dir/"sample.pto";run("pto_gen",[tools["pto_gen"],"-o",pto,tifs[0]],600)
    run("nona",[tools["nona"],"-m","TIFF_m","-o",out_dir/"sample_remap_",pto],1200)
    return True
