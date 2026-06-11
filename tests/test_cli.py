import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from cli.main import main


ROOT = Path(__file__).resolve().parents[1]
PHANTOM = ROOT / "samples" / "phantom.edf"


class CLITests(unittest.TestCase):
    def test_cli_success_creates_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code, stdout, stderr = self._run_cli(
                [
                    str(PHANTOM),
                    "--channel",
                    "sine",
                    "--start",
                    "0",
                    "--length",
                    "5",
                    "--cwt-scales",
                    "8",
                    "--export",
                    "csv,parameters",
                    "-o",
                    tmpdir,
                ]
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn("Analysis completed.", stdout)
            self.assertIn("csv:", stdout)
            self.assertTrue(list(Path(tmpdir).glob("*_features.csv")))
            self.assertTrue(list(Path(tmpdir).glob("*_parameters.json")))

    def test_cli_invalid_file_returns_nonzero(self):
        code, stdout, stderr = self._run_cli(
            [
                str(ROOT / "samples" / "missing.edf"),
                "--channel",
                "sine",
                "--export",
                "csv",
            ]
        )

        self.assertNotEqual(code, 0)
        self.assertEqual(stdout, "")
        self.assertIn("Error:", stderr)

    def test_cli_invalid_channel_returns_nonzero(self):
        code, stdout, stderr = self._run_cli(
            [
                str(PHANTOM),
                "--channel",
                "not-a-channel",
                "--export",
                "csv",
            ]
        )

        self.assertNotEqual(code, 0)
        self.assertEqual(stdout, "")
        self.assertIn("Channel not found", stderr)

    def test_cli_invalid_window_returns_nonzero(self):
        code, stdout, stderr = self._run_cli(
            [
                str(PHANTOM),
                "--channel",
                "sine",
                "--start",
                "299",
                "--length",
                "5",
                "--export",
                "csv",
            ]
        )

        self.assertNotEqual(code, 0)
        self.assertEqual(stdout, "")
        self.assertIn("exceeds recording duration", stderr)

    def _run_cli(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()


if __name__ == "__main__":
    unittest.main()
