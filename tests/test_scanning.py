import tempfile, unittest
from pathlib import Path
from dpr360.scanning import discover_source_set, list_dngs, list_jpegs
class TestScan(unittest.TestCase):
    def test_scan_once_per_file(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'A.DNG').write_bytes(b'x');(p/'B.dng').write_bytes(b'x');(p/'C.jpg').write_bytes(b'x')
            self.assertEqual(len(list_dngs(p)),2)

    def test_jpeg_extensions_are_case_insensitive_and_sorted(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for name in ("B.JPEG","a.jpg","C.jpeg","ignored.png"):
                (p/name).write_bytes(b'x')
            self.assertEqual([item.name for item in list_jpegs(p)],["a.jpg","B.JPEG","C.jpeg"])
            source=discover_source_set(p)
            self.assertEqual(source.input_format,"jpeg")
            self.assertEqual(len(source.frames),3)

    def test_dng_is_preferred_when_drone_folder_contains_both_formats(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'A.DNG').write_bytes(b'x');(p/'A.JPG').write_bytes(b'x')
            source=discover_source_set(p)
            self.assertEqual(source.input_format,"dng")
            self.assertEqual([item.name for item in source.frames],["A.DNG"])
            self.assertEqual(source.ignored_jpeg_count,1)
if __name__=='__main__':unittest.main()
