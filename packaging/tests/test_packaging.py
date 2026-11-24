from __future__ import annotations
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


class TestDebianPackaging(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.scripts_dir = cls.repo_root / "packaging" / "scripts"
        cls.dist_dir = cls.repo_root / "dist"

        # Ensure scripts are executable
        for script in cls.scripts_dir.glob("*.sh"):
            os.chmod(script, 0o755)
        for py_script in cls.scripts_dir.glob("*.py"):
            os.chmod(py_script, 0o755)

    def _extract_deb_members(self, deb_path: Path):
        """Extracts ar members from a .deb file."""
        members = {}
        with open(deb_path, "rb") as f:
            magic = f.read(8)
            self.assertEqual(magic, b"!<arch>\n", "Not a valid ar archive")

            while True:
                hdr = f.read(60)
                if not hdr or len(hdr) < 60:
                    break
                name = hdr[0:16].decode("ascii").strip()
                size = int(hdr[48:58].decode("ascii").strip())
                data = f.read(size)
                members[name] = data
                # Pad byte if size is odd
                if size % 2 != 0:
                    f.read(1)

        return members

    def test_build_core_package(self):
        cmd = [str(self.scripts_dir / "build_core_deb.sh")]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"build_core_deb.sh failed: {res.stderr}")

        core_deb = self.dist_dir / "reims-core_0.1.0_all.deb"
        self.assertTrue(core_deb.exists(), "Core deb was not created")

        members = self._extract_deb_members(core_deb)
        self.assertIn("debian-binary", members)
        self.assertIn("control.tar.gz", members)
        self.assertIn("data.tar.gz", members)
        self.assertEqual(members["debian-binary"], b"2.0\n")

        # Inspect data.tar.gz contents
        with tempfile.TemporaryDirectory() as tmp:
            data_tar = Path(tmp) / "data.tar.gz"
            data_tar.write_bytes(members["data.tar.gz"])
            with tarfile.open(data_tar, "r:gz") as tar:
                names = tar.getnames()
                self.assertTrue(any("reims.conf" in n for n in names))
                self.assertTrue(any("99-reims.rules" in n for n in names))
                self.assertTrue(any("reims.list" in n for n in names))
                self.assertTrue(any("usr/bin/reims-desktop-update" in n for n in names))
                self.assertTrue(any("usr/bin/reims-boot-theme-apply" in n for n in names))
                self.assertTrue(any("usr/bin/reims-clean-bloatware" in n for n in names))
                self.assertTrue(any("usr/bin/reims-update" in n for n in names))
                self.assertTrue(any("themes/reims/theme.txt" in n for n in names))
                self.assertTrue(any("themes/reims/background.png" in n for n in names))

    def test_build_gui_package(self):
        cmd = [str(self.scripts_dir / "build_gui_deb.sh")]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"build_gui_deb.sh failed: {res.stderr}")

        gui_deb = self.dist_dir / "reims-gui_0.1.0_all.deb"
        self.assertTrue(gui_deb.exists(), "GUI deb was not created")

        members = self._extract_deb_members(gui_deb)
        self.assertIn("debian-binary", members)
        self.assertIn("control.tar.gz", members)
        self.assertIn("data.tar.gz", members)

        # Inspect data.tar.gz contents
        with tempfile.TemporaryDirectory() as tmp:
            data_tar = Path(tmp) / "data.tar.gz"
            data_tar.write_bytes(members["data.tar.gz"])
            with tarfile.open(data_tar, "r:gz") as tar:
                names = tar.getnames()
                self.assertTrue(any("reims-desktop.desktop" in n for n in names))
                self.assertTrue(any("reims-desktop.svg" in n for n in names))
                self.assertTrue(any("reims-desktop.png" in n for n in names))
                self.assertTrue(any("usr/bin/reims-desktop" in n for n in names))
                self.assertTrue(any("usr/bin/reims-gui" in n for n in names))
                self.assertTrue(any("dist-packages/reims_gui" in n for n in names))

    def test_build_all_runner(self):
        cmd = [str(self.scripts_dir / "build_all.sh")]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"build_all.sh failed: {res.stderr}")
        self.assertIn("reims-core_0.1.0_all.deb", res.stdout)
        self.assertIn("reims-gui_0.1.0_all.deb", res.stdout)
        self.assertIn("reims-vgpu_0.1.0_amd64.deb", res.stdout)

        vgpu_deb = self.dist_dir / "reims-vgpu_0.1.0_amd64.deb"
        self.assertTrue(vgpu_deb.exists())
        members = self._extract_deb_members(vgpu_deb)
        with tempfile.TemporaryDirectory() as tmp:
            data_tar = Path(tmp) / "data.tar.gz"
            data_tar.write_bytes(members["data.tar.gz"])
            with tarfile.open(data_tar, "r:gz") as tar:
                names = tar.getnames()
                self.assertTrue(any("usr/bin/reims-desktop-ctl" in n for n in names))
                self.assertTrue(any("usr/bin/reims-ctl" in n for n in names))


if __name__ == "__main__":
    unittest.main()
