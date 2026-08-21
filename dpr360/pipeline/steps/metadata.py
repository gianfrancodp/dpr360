from __future__ import annotations
import csv, json
from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.scanning import list_dngs

KEYS = [
    "FileName", "DateTimeOriginal", "SubSecTimeOriginal", "ImageWidth", "ImageHeight", "FocalLength",
    "FocalLengthIn35mmFormat", "GPSLatitude", "GPSLongitude", "GPSAltitude", "GimbalYawDegree",
    "GimbalPitchDegree", "GimbalRollDegree", "FlightYawDegree", "FlightPitchDegree", "FlightRollDegree",
    "RelativeAltitude", "AbsoluteAltitude", "CalibratedFocalLength", "CalibratedOpticalCenterX",
    "CalibratedOpticalCenterY", "DewarpData", "DewarpFlag"
]

def suffix_value(data, suffix):
    for k, v in data.items():
        if k == suffix or k.endswith(":" + suffix): return v
    return ""

class MetadataStep(BaseStep):
    name="metadata"; label="Drone metadata / EXIF"; weight=0.03
    def run(self, ctx):
        dngs=list_dngs(ctx.source_dir)
        if not dngs: return StepResult(self.name, False, 2, "Nessun DNG trovato.")
        ctx.metadata_dir.mkdir(parents=True, exist_ok=True)
        full=[]; rows=[]
        for i,p in enumerate(dngs):
            ctx.progress(i/len(dngs), f"Metadata {i+1}/{len(dngs)} · {p.name}")
            r=self.command(ctx,[ctx.tools["exiftool"],"-json","-G1","-a","-s",str(p)],timeout=180)
            if r.returncode != 0:
                return StepResult(self.name,False,r.returncode,f"ExifTool fallito su {p.name}",stderr=r.stderr)
            try:
                item=json.loads(r.stdout)[0]
            except Exception as e:
                return StepResult(self.name,False,3,f"JSON ExifTool non valido: {e}",stdout=r.stdout)
            full.append(item); rows.append({k:suffix_value(item,k) for k in KEYS})
        full_path=ctx.metadata_dir/"metadata_full.json"; csv_path=ctx.metadata_dir/"panorama_metadata.csv"
        full_path.write_text(json.dumps(full,ensure_ascii=False,indent=2),encoding="utf-8")
        with csv_path.open("w",newline="",encoding="utf-8-sig") as f:
            writer=csv.DictWriter(f,fieldnames=KEYS); writer.writeheader(); writer.writerows(rows)
        ctx.progress(1,"Metadata completati")
        models=sorted({str(suffix_value(x,"ProductName") or suffix_value(x,"Model")) for x in full if suffix_value(x,"ProductName") or suffix_value(x,"Model")})
        ctx.logger.event("metadata_summary", dng_count=len(dngs), camera_models=models, output_files=2)
        return StepResult(self.name,True,0,f"Estratti metadata da {len(dngs)} DNG.",outputs=[str(full_path),str(csv_path)],details={"dng_count":len(dngs)})
