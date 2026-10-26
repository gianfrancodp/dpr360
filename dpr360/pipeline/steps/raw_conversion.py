from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
from PIL import Image
from dpr360.jpeg import prepare_jpeg
from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.scanning import discover_source_set, list_tiffs


def working_tiff_dir(ctx, input_format: str):
    return ctx.tiff_dir if input_format == "dng" else ctx.tiff_dir / input_format


def list_working_tiffs(ctx, source):
    if source.input_format == "jpeg":
        # Only the canonical outputs produced by JPEG preparation are inputs.
        outputs=[working_tiff_dir(ctx,"jpeg")/(frame.stem+".tif") for frame in source.frames]
        return [path for path in outputs if path.is_file()]
    by_stem = {path.stem.lower(): path for path in list_tiffs(working_tiff_dir(ctx,source.input_format))}
    return [by_stem[frame.stem.lower()] for frame in source.frames if frame.stem.lower() in by_stem]


def source_signature(path):
    stat = path.stat()
    return [str(path.resolve()), stat.st_size, stat.st_mtime_ns]


def save_preparation_manifest(path, records):
    fd, name = tempfile.mkstemp(prefix=".manifest-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(records, stream)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def reusable_jpeg_tiff(source, output, record):
    if record != source_signature(source):
        return False
    try:
        with Image.open(source) as original, Image.open(output) as image:
            expected = original.size
            if original.getexif().get(274, 1) in (5, 6, 7, 8):
                expected = expected[::-1]
            image.load()
            return image.format == "TIFF" and image.mode == "RGB" and image.size == expected
    except (OSError, ValueError):
        return False

class RawConversionStep(BaseStep):
    name="raw_conversion"; label="Preparazione input → TIFF"; weight=0.25; prerequisites=("metadata",)
    def run(self,ctx):
        source=discover_source_set(ctx.source_dir); frames=list(source.frames)
        if not frames: return StepResult(self.name,False,2,"Nessun file DNG/JPG/JPEG trovato.")
        output_dir=working_tiff_dir(ctx,source.input_format);output_dir.mkdir(parents=True,exist_ok=True)
        stems=[p.stem.lower() for p in frames]
        if len(set(stems)) != len(stems):
            return StepResult(self.name,False,6,"Nomi sorgente ambigui: più file hanno lo stesso nome base.")
        manifest=output_dir/"sources.json"
        records={}
        if source.input_format == "jpeg" and manifest.exists():
            try:
                records=json.loads(manifest.read_text(encoding="utf-8"))
                if not isinstance(records,dict): records={}
            except (OSError,ValueError):
                records={}
        profile=ctx.config.get("pipeline",{}).get("raw_profile","")
        for i,frame in enumerate(frames):
            if source.input_format == "jpeg":
                target=output_dir/(frame.stem+".tif")
                matches=[target] if target.is_file() else []
            else:
                matches=[p for p in list_tiffs(output_dir) if p.stem.lower()==frame.stem.lower()]
            if matches and (source.input_format != "jpeg" or reusable_jpeg_tiff(frame,matches[0],records.get(frame.name))):
                ctx.live_log(f"[Input → TIFF] già presente: {matches[0].name}")
                ctx.progress((i+1)/len(frames),f"{i+1}/{len(frames)} già preparato")
                continue
            ctx.progress(i/len(frames),f"Preparazione {i+1}/{len(frames)} · {frame.name}")
            if source.input_format == "jpeg":
                try:
                    prepare_jpeg(frame,output_dir/(frame.stem+".tif"),ctx.tools.get("exiftool"))
                    records[frame.name]=source_signature(frame)
                    save_preparation_manifest(manifest,records)
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
