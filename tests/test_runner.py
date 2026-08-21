import tempfile, unittest
from pathlib import Path
from dpr360.models import PipelineContext, StepResult
from dpr360.pipeline.base import BaseStep
from dpr360.pipeline.runner import PipelineRunner

class Logger:
    def event(self,*a,**k): pass

class A(BaseStep):
    name='a'; label='A'; weight=.5
    def run(self,ctx): ctx.progress(1,'A'); return StepResult('a',True,0,'ok')
class B(BaseStep):
    name='b'; label='B'; weight=.3; prerequisites=('a',)
    fail=True
    def run(self,ctx):
        if self.fail: return StepResult('b',False,7,'boom')
        return StepResult('b',True,0,'ok')
class C(BaseStep):
    name='c'; label='C'; weight=.2; prerequisites=('b',)
    def run(self,ctx): return StepResult('c',True,0,'ok')

class TestRunner(unittest.TestCase):
    def test_stop_and_resume(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/'src'; prj=root/'prj'; src.mkdir(); prj.mkdir()
            ctx=PipelineContext(src,prj,{}, {}, Logger())
            b=B(); r=PipelineRunner(ctx,[A(),b,C()])
            result,_=r.run_all(False)
            self.assertEqual(result.returncode,7)
            self.assertEqual(r.state.status('a'),'completed')
            self.assertEqual(r.state.status('b'),'failed')
            self.assertEqual(r.state.status('c'),'pending')
            b.fail=False
            result,_=r.run_all(True)
            self.assertEqual(result.returncode,0)
            self.assertEqual(r.state.status('c'),'completed')


class W(BaseStep):
    name='w'; label='W'; weight=.1
    def run(self,ctx):
        return StepResult('w',True,0,'ok con warning',warnings=['test warning'])

class TestWarningState(unittest.TestCase):
    def test_warning_is_successful_for_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/'src2'; prj=root/'prj2'; src.mkdir(); prj.mkdir()
            ctx=PipelineContext(src,prj,{}, {}, Logger())
            r=PipelineRunner(ctx,[W()])
            result,_=r.run_all(False)
            self.assertEqual(result.returncode,0)
            self.assertEqual(r.state.status('w'),'completed_with_warnings')
            self.assertEqual(r.overall_fraction(),1.0)

if __name__=='__main__': unittest.main()
