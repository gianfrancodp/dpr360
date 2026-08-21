import unittest
from pathlib import Path
from dpr360.pipeline.steps.blend import build_enblend_args, collect_enblend_warnings

class TestBlend(unittest.TestCase):
    def test_enblend_full_canvas_args(self):
        args = build_enblend_args(
            r"C:\Program Files\Hugin\bin\enblend.exe",
            Path("out.tif"),
            [Path("a.tif"), Path("b.tif")],
            17844,
            8922,
            verbose=1,
        )
        self.assertIn("--wrap=horizontal", args)
        self.assertIn("-f", args)
        self.assertIn("17844x8922+0+0", args)
        self.assertIn("--verbose=1", args)

    def test_warning_parser(self):
        text = """enblend: warning: some images are redundant and will not be blended
enblend: note: usually this means that at least one image does not belong to the set
"""
        warnings = collect_enblend_warnings(text)
        self.assertEqual(len(warnings), 2)
        self.assertTrue(any("redundant" in x for x in warnings))

if __name__ == "__main__":
    unittest.main()
