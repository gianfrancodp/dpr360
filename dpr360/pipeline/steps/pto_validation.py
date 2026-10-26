from dpr360.models import StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.pto import validate_panorama, control_point_connectivity
class PtoValidationStep(BaseStep):
    name="pto_validation";label="Validazione PTO";weight=0.01;prerequisites=("panorama_setup",)
    def run(self,ctx):
        path=ctx.hugin_dir/"project_360.pto";ctx.progress(.2,"Controllo geometria prima del remapping")
        try: info={**validate_panorama(path),**control_point_connectivity(path)}
        except Exception as e:return StepResult(self.name,False,3,f"PTO non leggibile: {e}")
        ctx.progress(1,"PTO valido" if info['valid'] else "PTO non valido")
        if not info['valid']:
            failed=[k for k,v in info['checks'].items() if not v]
            return StepResult(self.name,False,10,"Validazione PTO fallita: "+", ".join(failed),details=info)
        warnings=[]
        if not info["alignment_connected"]:
            warnings.append(f"Allineamento da verificare: {len(info['alignment_components'])} gruppi scollegati per {info['image_count']} immagini. La geometria 2:1 non garantisce un panorama correttamente allineato.")
        return StepResult(self.name,True,0,"Geometria PTO PASS.",details=info,outputs=[str(path)],warnings=warnings)
