import contextlib
import csv
import io
import json
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

    def test_cli_legacy_color_range_applies_to_parameters(self):
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
                    "--color-min",
                    "-2",
                    "--color-max",
                    "3",
                    "--export",
                    "parameters",
                    "-o",
                    tmpdir,
                ]
            )

            self.assertEqual(code, 0, stderr)
            record_path = next(Path(tmpdir).glob("*_parameters.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["display"]["color_range_mode"], "manual")
            self.assertEqual(record["display"]["color_min"], -2.0)
            self.assertEqual(record["display"]["color_max"], 3.0)

    def test_cli_plot_specific_color_range_overrides_legacy_in_parameters(self):
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
                    "--color-min",
                    "-2",
                    "--color-max",
                    "3",
                    "--scalogram-color-min",
                    "0.25",
                    "--scalogram-color-max",
                    "1.5",
                    "--spectrogram-color-min",
                    "-70",
                    "--spectrogram-color-max",
                    "-5",
                    "--export",
                    "parameters",
                    "-o",
                    tmpdir,
                ]
            )

            self.assertEqual(code, 0, stderr)
            record_path = next(Path(tmpdir).glob("*_parameters.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["display"]["scalogram_color_range_mode"], "manual")
            self.assertEqual(record["display"]["scalogram_color_min"], 0.25)
            self.assertEqual(record["display"]["spectrogram_color_range_mode"], "manual")
            self.assertEqual(record["display"]["spectrogram_color_max"], -5.0)

    def test_cli_partial_plot_specific_color_range_returns_nonzero(self):
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
                "--scalogram-color-min",
                "0.25",
                "--export",
                "parameters",
            ]
        )

        self.assertNotEqual(code, 0)
        self.assertEqual(stdout, "")
        self.assertIn("Manual scalogram_color range requires min and max", stderr)

    def test_cli_band_stop_filter_family_parameters_export(self):
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
                    "--filter",
                    "band_stop",
                    "--filter-low",
                    "4",
                    "--filter-high",
                    "8",
                    "--filter-order",
                    "3",
                    "--filter-family",
                    "ellip",
                    "--filter-ripple-db",
                    "1.5",
                    "--filter-stop-atten-db",
                    "45",
                    "--export",
                    "parameters",
                    "-o",
                    tmpdir,
                ]
            )

            self.assertEqual(code, 0, stderr)
            record_path = next(Path(tmpdir).glob("*_parameters.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["filtering"]["filter_type"], "band_stop")
            self.assertEqual(record["filtering"]["filter_family"], "ellip")
            self.assertEqual(record["filtering"]["filter_ripple_db"], 1.5)
            self.assertEqual(record["filtering"]["filter_stop_atten_db"], 45.0)

    def test_cli_batch_windows_writes_summary_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code, stdout, stderr = self._run_cli(
                [
                    str(PHANTOM),
                    "--channels",
                    "sine,chirp",
                    "--start",
                    "0",
                    "--length",
                    "5",
                    "--batch-windows",
                    "--end",
                    "10",
                    "--step",
                    "5",
                    "--cwt-scales",
                    "8",
                    "--export",
                    "csv",
                    "-o",
                    tmpdir,
                ]
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn("Analyses: 4", stdout)
            summary_path = Path(tmpdir) / "batch_features.csv"
            self.assertTrue(summary_path.exists())
            with summary_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 4)
            self.assertEqual({row["channel"] for row in rows}, {"sine", "chirp"})
            self.assertEqual(rows[0]["window_start_s"], "0.0")

    def _run_cli(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()


if __name__ == "__main__":
    unittest.main()
