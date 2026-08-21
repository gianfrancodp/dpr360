from PIL import Image
from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
class FinalValidationStep(BaseStep):
    name="final_validation";label="Validazione finale";weight=0.03;prerequisites=("blend",)
    def run(self,ctx):
        p=ctx.final_tif
        if not p.exists(): return StepResult(self.name,False,2,"TIFF finale mancante.")
        ctx.progress(.05,"Apertura TIFF finale")
        try:
            with Image.open(p) as img:
                w,h=img.size; ratio=w/h if h else 0; mode=img.mode; fmt=img.format
                geometry_ok=abs(ratio-2.0)<=1e-4
                coverage=None
                if "A" in img.getbands():
                    alpha=img.getchannel("A")
                    strip_h=max(16,int(ctx.config.get("pipeline",{}).get("coverage_strip_height",128)))
                    threshold=int(ctx.config.get("pipeline",{}).get("coverage_alpha_threshold",1))
                    covered=0;total=w*h
                    for y in range(0,h,strip_h):
                        y2=min(h,y+strip_h); strip=alpha.crop((0,y,w,y2)); hist=strip.histogram()
                        covered += sum(hist[threshold:])
                        ctx.progress(.1+.85*(y2/h),f"Coverage {y2}/{h} righe")
                    coverage=covered/total if total else None
                details={"exists":True,"path":str(p),"size_bytes":p.stat().st_size,"width":w,"height":h,"ratio":ratio,"mode":mode,"format":fmt,
                         "geometry_pass":geometry_ok,"coverage_fraction":coverage,"coverage_percent":round(coverage*100,3) if coverage is not None else None}
        except Exception as e:return StepResult(self.name,False,3,f"Impossibile validare TIFF: {e}")
        ctx.progress(1,"Validazione completata")
        if not details["geometry_pass"]:
            return StepResult(self.name,False,11,"Il TIFF finale non è 2:1.",details=details,outputs=[str(p)])
        return StepResult(self.name,True,0,"Geometry PASS" + (f" · Coverage {details['coverage_percent']}%" if details['coverage_percent'] is not None else ""),details=details,outputs=[str(p)])
