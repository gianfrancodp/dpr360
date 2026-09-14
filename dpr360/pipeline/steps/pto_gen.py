from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.scanning import discover_source_set
from dpr360.pipeline.steps.raw_conversion import list_working_tiffs
class PtoGenStep(BaseStep):
    name="pto_gen"; label="Creazione progetto Hugin"; weight=0.02; prerequisites=("raw_conversion",)
    def run(self,ctx):
        source=discover_source_set(ctx.source_dir)
        tifs=list_working_tiffs(ctx,source)
        if not tifs:return StepResult(self.name,False,2,"Nessun TIFF trovato.")
        out=ctx.hugin_dir/"project_initial.pto"; ctx.progress(.1,"Creazione PTO")
        r=self.command(ctx,[ctx.tools["pto_gen"],"--projection=0","-o",out,*tifs],timeout=600)
        if r.returncode:return StepResult(self.name,False,r.returncode,"pto_gen fallito",stderr=r.stderr)
        ctx.progress(1,"PTO creato"); return StepResult(self.name,True,0,"Progetto iniziale creato.",outputs=[str(out)])
