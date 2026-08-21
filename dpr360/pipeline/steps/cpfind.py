from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
class CpFindStep(BaseStep):
    name="cpfind"; label="Control points"; weight=0.15; prerequisites=("pto_gen",)
    def run(self,ctx):
        src=ctx.hugin_dir/"project_initial.pto"; out=ctx.hugin_dir/"project_cp.pto"; ctx.progress(.05,"Ricerca control points")
        r=self.command(ctx,[ctx.tools["cpfind"],"--multirow","--celeste","-o",out,src],timeout=3600)
        if r.returncode:return StepResult(self.name,False,r.returncode,"cpfind fallito",stderr=r.stderr)
        ctx.progress(1,"Control points completati");return StepResult(self.name,True,0,"Control points trovati.",outputs=[str(out)])
