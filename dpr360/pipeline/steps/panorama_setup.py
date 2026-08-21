from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.pto import force_full_equirectangular
class PanoramaSetupStep(BaseStep):
    name="panorama_setup";label="Setup equirettangolare";weight=0.02;prerequisites=("optimise",)
    def run(self,ctx):
        src=ctx.hugin_dir/"project_opt.pto";tmp=ctx.hugin_dir/"project_360_raw.pto";out=ctx.hugin_dir/"project_360.pto"
        ctx.progress(.1,"Impostazione 360×180")
        r=self.command(ctx,[ctx.tools["pano_modify"],"--projection=2","--fov=360x180","--canvas=AUTO","-o",tmp,src],timeout=600)
        if r.returncode:return StepResult(self.name,False,r.returncode,"pano_modify fallito",stderr=r.stderr)
        try: info=force_full_equirectangular(tmp,out)
        except Exception as e:return StepResult(self.name,False,3,f"Normalizzazione PTO fallita: {e}")
        ctx.progress(1,f"Canvas {info['width']}×{info['height']}")
        return StepResult(self.name,True,0,"PTO normalizzato a full-canvas 360×180.",outputs=[str(out)],details=info)
