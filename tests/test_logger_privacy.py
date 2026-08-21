import json, tempfile, unittest
from pathlib import Path
from dpr360.logger import UsageLogger

class TestLoggerPrivacy(unittest.TestCase):
    def test_paths_gps_and_serial_are_redacted(self):
        with tempfile.TemporaryDirectory() as td:
            logger = UsageLogger(
                Path(td),
                enabled=True,
                include_paths=False,
                diagnostic_mode=True,
                include_sensitive_metadata=False,
            )
            logger.event(
                "x",
                stdout='{"SourceFile":"C:/Users/Utente/PANO.DNG","GPSLatitude":"37 deg N","CameraSerialNumber":"ABC123"}',
                command=[r"C:\Users\Utente\tool.exe", r"C:\Users\Utente\PANO.DNG"],
            )
            raw = logger.file.read_text(encoding="utf-8")
            self.assertNotIn("C:/Users/Utente", raw)
            self.assertNotIn(r"C:\\Users\\Utente", raw)
            self.assertNotIn("37 deg N", raw)
            self.assertNotIn("ABC123", raw)
            self.assertIn("PATH_REDACTED", raw)
            self.assertIn("SENSITIVE_REDACTED", raw)

if __name__ == "__main__":
    unittest.main()
