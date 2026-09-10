import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EntrypointTests(unittest.TestCase):
    def test_app_cli_help_delegates_to_cli_parser(self):
        proc = subprocess.run(
            [sys.executable, "app.py", "--mode", "cli", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("usage: edfviewer", proc.stdout)
        self.assertIn("--channel", proc.stdout)
        self.assertIn("--export", proc.stdout)

    def test_direct_cli_script_help_resolves_project_imports(self):
        proc = subprocess.run(
            [sys.executable, "cli/main.py", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("usage: edfviewer", proc.stdout)


if __name__ == "__main__":
    unittest.main()
