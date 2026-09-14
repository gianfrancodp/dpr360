from __future__ import annotations
from PIL import Image, ImageOps
from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.scanning import discover_source_set, list_tiffs


def working_tiff_dir(ctx, input_format: str):
    return ctx.tiff_dir if input_format == "dng" else ctx.tiff_dir / input_format


def list_working_tiffs(ctx, source):
    by_stem = {path.stem.lower(): path for path in list_tiffs(working_tiff_dir(ctx,source.input_format))}
    return [by_stem[frame.stem.lower()] for frame in source.frames if frame.stem.lower() in by_stem]


def prepare_jpeg(source, destination):
    with Image.open(source) as image:
        icc_profile = image.info.get("icc_profile")
        image = ImageOps.exif_transpose(image).convert("RGB")
        save_args = {"format": "TIFF", "compression": "tiff_deflate"}
        if icc_profile:
            save_args["icc_profile"] = icc_profile
        exif = image.getexif()
        if exif:
            save_args["exif"] = exif
        image.save(destination, **save_args)

class RawConversionStep(BaseStep):
    name="raw_conversion"; label="Preparazione input → TIFF"; weight=0.25; prerequisites=("metadata",)
    def run(self,ctx):
        source=discover_source_set(ctx.source_dir); frames=list(source.frames)
        if not frames: return StepResult(self.name,False,2,"Nessun file DNG/JPG/JPEG trovato.")
        output_dir=working_tiff_dir(ctx,source.input_format);output_dir.mkdir(parents=True,exist_ok=True)
        profile=ctx.config.get("pipeline",{}).get("raw_profile","")
        for i,frame in enumerate(frames):
            matches=[p for p in list_tiffs(output_dir) if p.stem.lower()==frame.stem.lower()]
            if matches:
                ctx.live_log(f"[Input → TIFF] già presente: {matches[0].name}")
                ctx.progress((i+1)/len(frames),f"{i+1}/{len(frames)} già preparato")
                continue
            ctx.progress(i/len(frames),f"Preparazione {i+1}/{len(frames)} · {frame.name}")
            if source.input_format == "jpeg":
                try:
                    prepare_jpeg(frame,output_dir/(frame.stem+".tif"))
                except Exception as exc:
                    return StepResult(self.name,False,5,f"Conversione JPEG fallita su {frame.name}",stderr=repr(exc))
            else:
                args=[ctx.tools["rawtherapee"],"-o",str(output_dir),"-b16","-tz","-Y"]
                if profile: args += ["-p",profile]
                args += ["-c",str(frame)]
                r=self.command(ctx,args,timeout=1800)
                if r.returncode != 0:
                    return StepResult(self.name,False,r.returncode,f"RawTherapee fallito su {frame.name}",stderr=r.stderr)
            ctx.progress((i+1)/len(frames),f"Preparati {i+1}/{len(frames)}")
        tifs=list_working_tiffs(ctx,source)
        if len(tifs)<len(frames): return StepResult(self.name,False,4,f"TIFF prodotti {len(tifs)}/{len(frames)}")
        warnings=[]
        if source.input_format == "jpeg":
            warnings.append("I TIFF di lavoro derivano da JPEG a 8 bit: la conversione non ripristina la gamma dinamica RAW.")
        return StepResult(
            self.name,True,0,f"{len(tifs)} TIFF disponibili.",outputs=[str(p) for p in tifs],
            details={"tiff_count":len(tifs),"input_format":source.input_format,"working_depth":"8-bit source" if source.input_format == "jpeg" else "16-bit"},
            warnings=warnings,
        )
