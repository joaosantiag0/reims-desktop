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
        wp_png = self.custom_dir / "reims-wallpaper.png"
        self.assertTrue(wp.exists(), "wallpaper.svg not found")
        self.assertTrue(wp_png.exists(), "reims-wallpaper.png not found")
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

    def test_installer_prompt_and_boot_logo_exist(self):
        prompt_py = self.custom_dir / "reims-installer-prompt.py"
        logo_png = self.custom_dir / "reims-logo.png"

        self.assertTrue(prompt_py.exists(), "reims-installer-prompt.py not found")
        self.assertTrue(logo_png.exists(), "reims-logo.png not found")
        self.assertGreater(logo_png.stat().st_size, 1000)

        content = prompt_py.read_text(encoding="utf-8")
        self.assertIn("#!/usr/bin/env python3", content)
        self.assertIn("ReimsInstallerPromptWindow", content)
        self.assertIn("Experimentar Reims Desktop (Live CD)", content)
        self.assertIn("Instalar o Reims Desktop", content)

    def test_touchpad_config_exists(self):
        conf = self.custom_dir / "90-touchpad.conf"
        sh = self.custom_dir / "reims-touchpad.sh"
        desktop = self.custom_dir / "reims-touchpad.desktop"

        self.assertTrue(conf.exists(), "90-touchpad.conf not found")
        self.assertTrue(sh.exists(), "reims-touchpad.sh not found")
        self.assertTrue(desktop.exists(), "reims-touchpad.desktop not found")

        conf_content = conf.read_text(encoding="utf-8")
        self.assertIn('Option "Tapping" "True"', conf_content)
        self.assertIn('Option "ClickMethod" "clickfinger"', conf_content)

        sh_content = sh.read_text(encoding="utf-8")
        self.assertIn("xinput set-prop", sh_content)
        self.assertIn("libinput Tapping Enabled", sh_content)

    def test_calamares_reims_branding_and_desktop_installer(self):
        calamares_desc = self.repo_root / "iso-builder" / "config" / "calamares" / "branding" / "reims" / "branding.desc"
        self.assertTrue(calamares_desc.exists(), "branding.desc for reims not found")
        content = calamares_desc.read_text(encoding="utf-8")
        self.assertIn('slideshow:', content)
        self.assertIn('"show.qml"', content)
        self.assertIn("slideshowAPI:", content)
        self.assertIn("productName:", content)
        self.assertIn("Reims Desktop", content)

        script = self.scripts_dir / "remaster_iso.sh"
        script_content = script.read_text(encoding="utf-8")
        self.assertIn("lubuntu-calamares.desktop", script_content)
        self.assertIn("Install Reims Desktop", script_content)
        self.assertIn("rm -f \"${SKEL_DIR}/Desktop/install-reims.desktop\"", script_content)
        self.assertIn("pkgselect", script_content)
        self.assertIn('cp -v "${CONFIG_DIR}/calamares/settings.conf"', script_content)

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
