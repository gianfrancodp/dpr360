import tempfile, unittest
from pathlib import Path
from dpr360.state import PipelineState
class TestState(unittest.TestCase):
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            s=PipelineState(Path(td),['a','b']);s.set_result('a','completed',{'returncode':0})
            s2=PipelineState(Path(td),['a','b']);self.assertEqual(s2.status('a'),'completed');self.assertEqual(s2.status('b'),'pending')
if __name__=='__main__':unittest.main()
