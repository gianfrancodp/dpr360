from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.scanning import list_tiffs
class RemapStep(BaseStep):
    name="remap";label="Nona · remapping";weight=0.25;prerequisites=("pto_validation",)
    def run(self,ctx):
        remap=ctx.hugin_dir/"remap";remap.mkdir(parents=True,exist_ok=True)
        for p in remap.glob("level_*.tif"): p.unlink()
        expected=len(list_tiffs(ctx.tiff_dir));prefix=remap/"level_";pto=ctx.hugin_dir/"project_360.pto"
        ctx.progress(.01,"Avvio remapping")
        def poll():
            n=len(list(remap.glob("level_*.tif")))
            if expected: ctx.progress(min(.98,n/expected),f"Remappate {n}/{expected} immagini")
        r=self.command(ctx,[ctx.tools["nona"],"-m","TIFF_m","-o",prefix,pto],timeout=7200,poll_callback=poll)
        if r.returncode:return StepResult(self.name,False,r.returncode,"nona fallito",stderr=r.stderr)
        files=sorted(remap.glob("level_*.tif"));ctx.progress(1,f"Remapping completato: {len(files)} livelli")
        if expected and len(files)<expected:return StepResult(self.name,False,5,f"Nona ha prodotto {len(files)}/{expected} livelli.")
        return StepResult(self.name,True,0,"Remapping completato.",outputs=[str(p) for p in files],details={"remapped":len(files)})
