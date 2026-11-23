from __future__ import annotations
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


class TestReimsBinariesPackaging(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.scripts_dir = cls.repo_root / "packaging" / "scripts"
        cls.dist_dir = cls.repo_root / "dist"

        for script in cls.scripts_dir.glob("*.sh"):
            os.chmod(script, 0o755)

    def test_build_reims_binaries_mock(self):
        cmd = [str(self.scripts_dir / "build_reims_binaries.sh"), "--mock"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"build_reims_binaries.sh failed: {res.stderr}")

        vgpu_deb = self.dist_dir / "reims-vgpu_0.1.0_amd64.deb"
        self.assertTrue(vgpu_deb.exists(), "reims-vgpu deb was not created")

        # Inspect data.tar.gz inside deb
        with open(vgpu_deb, "rb") as f:
            magic = f.read(8)
            self.assertEqual(magic, b"!<arch>\n")

            data_tar_bytes = None
            while True:
                hdr = f.read(60)
                if not hdr or len(hdr) < 60:
                    break
                name = hdr[0:16].decode("ascii").strip()
                size = int(hdr[48:58].decode("ascii").strip())
                data = f.read(size)
                if name == "data.tar.gz":
                    data_tar_bytes = data
                    break
                if size % 2 != 0:
                    f.read(1)

        self.assertIsNotNone(data_tar_bytes, "Missing data.tar.gz in reims-vgpu deb")

        with tempfile.TemporaryDirectory() as tmp:
            tar_path = Path(tmp) / "data.tar.gz"
            tar_path.write_bytes(data_tar_bytes)
            with tarfile.open(tar_path, "r:gz") as tar:
                names = tar.getnames()
                self.assertTrue(any("usr/bin/reims-ctl" in n for n in names))
                self.assertTrue(any("usr/bin/reims-util" in n for n in names))
                self.assertTrue(any("usr/lib/reims/qemu-system-x86_64" in n for n in names))


if __name__ == "__main__":
    unittest.main()
