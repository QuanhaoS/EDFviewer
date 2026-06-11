import tempfile
import unittest
from pathlib import Path

from core.workflow import AnalysisParameters, EDFViewerError, EDFViewerWorkflow


ROOT = Path(__file__).resolve().parents[1]
PHANTOM = ROOT / "samples" / "phantom.edf"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = EDFViewerWorkflow()

    def test_loads_phantom_metadata(self):
        metadata = self.workflow.load_file(str(PHANTOM))

        self.assertIn("sine", metadata.channel_names)
        self.assertAlmostEqual(metadata.duration_s, 300.0, delta=0.5)

    def test_computes_valid_window(self):
        self.workflow.load_file(str(PHANTOM))
        params = AnalysisParameters(window_start_s=0, window_length_s=5, scalogram_n_scales=8)

        result = self.workflow.compute_window("sine", params)

        self.assertEqual(result.source.channel_name, "sine")
        self.assertGreater(result.processed_signal.size, 0)
        self.assertIn("time_rms", result.features)
        self.assertIn("freq_dominant_hz", result.features)
        self.assertAlmostEqual(result.features["freq_dominant_hz"], 1.5, delta=0.25)

    def test_returns_cache_hit_for_same_key(self):
        self.workflow.load_file(str(PHANTOM))
        params = AnalysisParameters(window_start_s=0, window_length_s=5, scalogram_n_scales=8)

        first = self.workflow.compute_window("sine", params)
        second = self.workflow.compute_window("sine", params)

        self.assertIs(first, second)
        self.assertTrue(second.from_cache)

    def test_parameter_change_invalidates_cache(self):
        self.workflow.load_file(str(PHANTOM))
        first_params = AnalysisParameters(window_start_s=0, window_length_s=5, scalogram_n_scales=8)
        second_params = AnalysisParameters(window_start_s=100, window_length_s=5, scalogram_n_scales=8)

        first = self.workflow.compute_window("sine", first_params)
        second = self.workflow.compute_window("sine", second_params)

        self.assertIsNot(first, second)
        self.assertFalse(second.from_cache)

    def test_exports_requested_outputs(self):
        self.workflow.load_file(str(PHANTOM))
        params = AnalysisParameters(window_start_s=0, window_length_s=5, scalogram_n_scales=8)
        result = self.workflow.compute_window("sine", params)

        with tempfile.TemporaryDirectory() as tmpdir:
            exported = self.workflow.export_result(
                result,
                {"output_dir": tmpdir, "types": ["csv", "parameters"]},
            )

            paths = exported.csv_paths + exported.parameter_record_paths
            self.assertEqual(len(paths), 2)
            for path in paths:
                self.assertTrue(Path(path).exists())

    def test_invalid_window_fails(self):
        self.workflow.load_file(str(PHANTOM))
        params = AnalysisParameters(window_start_s=299, window_length_s=5, scalogram_n_scales=8)

        with self.assertRaises(EDFViewerError):
            self.workflow.compute_window("sine", params)


if __name__ == "__main__":
    unittest.main()
