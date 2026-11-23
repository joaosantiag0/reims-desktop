from __future__ import annotations
import os
import subprocess
import unittest
from pathlib import Path


class TestIsoBuilder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.config_dir = cls.repo_root / "iso-builder" / "config"
        cls.scripts_dir = cls.repo_root / "iso-builder" / "scripts"

        # Make script executable
        build_script = cls.scripts_dir / "build_iso.sh"
        if build_script.exists():
            os.chmod(build_script, 0o755)

    def test_packages_list_no_bloatware(self):
        pkg_file = self.config_dir / "packages.list"
        self.assertTrue(pkg_file.exists())

        bloat_candidates = [
            "libreoffice",
            "thunderbird",
            "vlc",
            "totem",
            "rhythmbox",
            "gnome-games",
            "aisleriot",
            "snapd",
        ]

        with open(pkg_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        for bloat in bloat_candidates:
            self.assertFalse(
                any(bloat in pkg for pkg in lines),
                f"Bloatware package '{bloat}' found in minimal packages.list",
            )

    def test_packages_list_essential_components(self):
        pkg_file = self.config_dir / "packages.list"
        with open(pkg_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        essential = [
            "linux-firmware",
            "libvulkan1",
            "mesa-vulkan-drivers",
            "network-manager",
            "bluez",
            "blueman",
            "pipewire",
            "wireplumber",
            "lxqt-core",
            "calamares",
            "qemu-system-x86",
        ]

        for pkg in essential:
            self.assertIn(
                pkg,
                lines,
                f"Essential package '{pkg}' missing from packages.list",
            )

    def test_calamares_settings_validity(self):
        settings_file = self.config_dir / "calamares" / "settings.conf"
        self.assertTrue(settings_file.exists())
        content = settings_file.read_text(encoding="utf-8")

        self.assertIn("branding: reims", content)
        self.assertIn("welcome", content)
        self.assertIn("locale", content)
        self.assertIn("keyboard", content)
        self.assertIn("partition", content)
        self.assertIn("contextualprocess", content)

    def test_calamares_contextual_process_groups(self):
        ctx_file = self.config_dir / "calamares" / "modules" / "contextualprocess.conf"
        self.assertTrue(ctx_file.exists())
        content = ctx_file.read_text(encoding="utf-8")

        self.assertIn("kvm", content)
        self.assertIn("render", content)

    def test_iso_builder_dry_run(self):
        script = self.scripts_dir / "build_iso.sh"
        res = subprocess.run([str(script), "--dry-run"], capture_output=True, text=True)
        self.assertEqual(
            res.returncode,
            0,
            f"build_iso.sh --dry-run failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
        )
        self.assertIn("Validação do pipeline de ISO concluída com 100% de sucesso!", res.stdout)


if __name__ == "__main__":
    unittest.main()
