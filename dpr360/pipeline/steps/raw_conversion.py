from __future__ import annotations
from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.scanning import list_dngs, list_tiffs

class RawConversionStep(BaseStep):
    name="raw_conversion"; label="RAW → TIFF 16-bit"; weight=0.25; prerequisites=("metadata",)
    def run(self,ctx):
        dngs=list_dngs(ctx.source_dir)
        if not dngs: return StepResult(self.name,False,2,"Nessun DNG trovato.")
        ctx.tiff_dir.mkdir(parents=True,exist_ok=True)
        profile=ctx.config.get("pipeline",{}).get("raw_profile","")
        for i,dng in enumerate(dngs):
            matches=[p for p in list_tiffs(ctx.tiff_dir) if p.stem.lower()==dng.stem.lower()]
            if matches:
                ctx.live_log(f"[RAW → TIFF] già presente: {matches[0].name}")
                ctx.progress((i+1)/len(dngs),f"{i+1}/{len(dngs)} già convertito")
                continue
            args=[ctx.tools["rawtherapee"],"-o",str(ctx.tiff_dir),"-b16","-tz","-Y"]
            if profile: args += ["-p",profile]
            args += ["-c",str(dng)]
            ctx.progress(i/len(dngs),f"Conversione {i+1}/{len(dngs)} · {dng.name}")
            r=self.command(ctx,args,timeout=1800)
            if r.returncode != 0:
                return StepResult(self.name,False,r.returncode,f"RawTherapee fallito su {dng.name}",stderr=r.stderr)
            ctx.progress((i+1)/len(dngs),f"Convertiti {i+1}/{len(dngs)}")
        tifs=list_tiffs(ctx.tiff_dir)
        if len(tifs)<len(dngs): return StepResult(self.name,False,4,f"TIFF prodotti {len(tifs)}/{len(dngs)}")
        return StepResult(self.name,True,0,f"{len(tifs)} TIFF disponibili.",outputs=[str(p) for p in tifs],details={"tiff_count":len(tifs)})
