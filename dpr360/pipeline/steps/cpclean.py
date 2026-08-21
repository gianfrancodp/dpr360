from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
class CpCleanStep(BaseStep):
    name="cpclean"; label="Pulizia control points"; weight=0.03; prerequisites=("cpfind",)
    def run(self,ctx):
        src=ctx.hugin_dir/"project_cp.pto"; out=ctx.hugin_dir/"project_clean.pto";ctx.progress(.1,"Pulizia control points")
        r=self.command(ctx,[ctx.tools["cpclean"],"-o",out,src],timeout=900)
        if r.returncode:return StepResult(self.name,False,r.returncode,"cpclean fallito",stderr=r.stderr)
        ctx.progress(1,"Pulizia completata");return StepResult(self.name,True,0,"Control points puliti.",outputs=[str(out)])
