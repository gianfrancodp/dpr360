import tempfile, unittest
from pathlib import Path
from dpr360.pto import force_full_equirectangular, validate_panorama
class TestPTO(unittest.TestCase):
    def test_force_full(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"a.pto";dst=Path(td)/"b.pto"
            src.write_text('p f2 w17844 h8922 v360 S0,17844,1239,7683 n"TIFF_m"\n',encoding="utf-8")
            force_full_equirectangular(src,dst);v=validate_panorama(dst)
            self.assertTrue(v["valid"]);self.assertEqual(v["crop"],(0,17844,0,8922));self.assertEqual(v["ratio"],2.0)
if __name__=='__main__':unittest.main()
