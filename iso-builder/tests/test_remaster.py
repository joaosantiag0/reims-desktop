from __future__ import annotations
import os
import subprocess
import unittest
from pathlib import Path


class TestIsoRemastering(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.custom_dir = cls.repo_root / "iso-builder" / "customization"
        cls.scripts_dir = cls.repo_root / "iso-builder" / "scripts"

        script = cls.scripts_dir / "remaster_iso.sh"
        if script.exists():
            os.chmod(script, 0o755)

    def test_wallpaper_exists_and_valid_svg(self):
        wp = self.custom_dir / "wallpaper.svg"
        self.assertTrue(wp.exists(), "wallpaper.svg not found")
        content = wp.read_text(encoding="utf-8")
        self.assertIn("<svg", content)
        self.assertIn("REIMS OS", content)

    def test_remove_packages_list(self):
        pkg_file = self.custom_dir / "remove-packages.list"
        self.assertTrue(pkg_file.exists(), "remove-packages.list not found")
        content = pkg_file.read_text(encoding="utf-8")
        self.assertIn("libreoffice", content)
        self.assertIn("transmission", content)
        self.assertIn("vlc", content)

    def test_desktop_conf_reims_branding(self):
        pcmanfm = self.custom_dir / "pcmanfm-qt-desktop.conf"
        lxqt_conf = self.custom_dir / "lxqt.conf"

        self.assertTrue(pcmanfm.exists())
        self.assertTrue(lxqt_conf.exists())

        self.assertIn("reims-wallpaper.svg", pcmanfm.read_text(encoding="utf-8"))
        self.assertIn("Flat-Dark", lxqt_conf.read_text(encoding="utf-8"))

    def test_remaster_script_dry_run(self):
        script = self.scripts_dir / "remaster_iso.sh"
        res = subprocess.run([str(script), "--dry-run"], capture_output=True, text=True)
        self.assertEqual(
            res.returncode,
            0,
            f"remaster_iso.sh --dry-run failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
        )
        self.assertIn("Script de remasterização testado com 100% de sucesso!", res.stdout)


if __name__ == "__main__":
    unittest.main()
