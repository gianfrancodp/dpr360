from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
class OptimiseStep(BaseStep):
    name="optimise"; label="Ottimizzazione Hugin"; weight=0.07; prerequisites=("cpclean",)
    def run(self,ctx):
        src=ctx.hugin_dir/"project_clean.pto";out=ctx.hugin_dir/"project_opt.pto";ctx.progress(.05,"Ottimizzazione geometrica/fotometrica")
        r=self.command(ctx,[ctx.tools["autooptimiser"],"-a","-m","-l","-o",out,src],timeout=1800)
        if r.returncode:return StepResult(self.name,False,r.returncode,"autooptimiser fallito",stderr=r.stderr)
        ctx.progress(1,"Ottimizzazione completata");return StepResult(self.name,True,0,"Ottimizzazione completata.",outputs=[str(out)])
