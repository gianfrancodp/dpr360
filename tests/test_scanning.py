import tempfile, unittest
from pathlib import Path
from dpr360.scanning import list_dngs
class TestScan(unittest.TestCase):
    def test_scan_once_per_file(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'A.DNG').write_bytes(b'x');(p/'B.dng').write_bytes(b'x');(p/'C.jpg').write_bytes(b'x')
            self.assertEqual(len(list_dngs(p)),2)
if __name__=='__main__':unittest.main()
