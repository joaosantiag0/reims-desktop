from __future__ import annotations
import os
import subprocess
import unittest
from pathlib import Path


class TestScriptsAndWorkflows(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.scripts_dir = cls.repo_root / "scripts"
        cls.workflows_dir = cls.repo_root / ".github" / "workflows"

        for script in cls.scripts_dir.glob("*.sh"):
            os.chmod(script, 0o755)

    def test_run_reims_vm_dry_run(self):
        script = self.scripts_dir / "run_reims_vm.sh"
        res = subprocess.run([str(script), "--dry-run"], capture_output=True, text=True)
        self.assertEqual(
            res.returncode,
            0,
            f"run_reims_vm.sh --dry-run failed:\n{res.stderr}",
        )
        self.assertIn("qemu-system-x86_64", res.stdout)
        self.assertIn("-cdrom", res.stdout)
        self.assertIn("-m 4096", res.stdout)

    def test_github_workflows_exist_and_valid(self):
        ci_file = self.workflows_dir / "ci.yml"
        iso_file = self.workflows_dir / "build-iso.yml"

        self.assertTrue(ci_file.exists(), "ci.yml does not exist")
        self.assertTrue(iso_file.exists(), "build-iso.yml does not exist")

        ci_text = ci_file.read_text(encoding="utf-8")
        self.assertIn("ubuntu-24.04", ci_text)
        self.assertIn("build_all.sh", ci_text)
        self.assertIn("build_iso.sh", ci_text)

        iso_text = iso_file.read_text(encoding="utf-8")
        self.assertIn("debootstrap", iso_text)
        self.assertIn("xorriso", iso_text)


if __name__ == "__main__":
    unittest.main()
