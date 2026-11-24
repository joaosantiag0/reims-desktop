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

    def test_reims_desktop_ctl_cli_operations(self):
        ctl_script = self.repo_root / "packaging" / "templates" / "reims-vgpu" / "usr" / "bin" / "reims-desktop-ctl"
        self.assertTrue(ctl_script.exists())
        os.chmod(ctl_script, 0o755)

        # Test doctor
        res_doc = subprocess.run([str(ctl_script), "doctor"], capture_output=True, text=True)
        self.assertEqual(res_doc.returncode, 0)
        self.assertIn("KVM:", res_doc.stdout)

        # Test gpus
        res_gpu = subprocess.run([str(ctl_script), "gpus"], capture_output=True, text=True)
        self.assertEqual(res_gpu.returncode, 0)
        self.assertTrue("NVIDIA" in res_gpu.stdout or "Graphics" in res_gpu.stdout or "AMD" in res_gpu.stdout)

        # Test create VM
        with tempfile.TemporaryDirectory() as fake_home:
            env = dict(os.environ, HOME=fake_home)
            res_create = subprocess.run(
                [str(ctl_script), "create", "Test-macOS-VM", "--cpus=4", "--memory-mib=8192", "--disk-gb=50", "--macos=tahoe"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(res_create.returncode, 0, f"create failed: {res_create.stderr}")
            self.assertIn("[1/4]", res_create.stdout)
            self.assertIn("[4/4]", res_create.stdout)

            # Test list --json
            res_list = subprocess.run([str(ctl_script), "list", "--json"], capture_output=True, text=True, env=env)
            self.assertEqual(res_list.returncode, 0)
            import json
            vms = json.loads(res_list.stdout)
            self.assertEqual(len(vms), 1)
            self.assertEqual(vms[0]["name"], "Test-macOS-VM")
            self.assertEqual(vms[0]["config"]["cpus"], 4)

            # Test delete
            res_del = subprocess.run([str(ctl_script), "delete", "Test-macOS-VM"], capture_output=True, text=True, env=env)
            self.assertEqual(res_del.returncode, 0)

            res_list_after = subprocess.run([str(ctl_script), "list", "--json"], capture_output=True, text=True, env=env)
            vms_after = json.loads(res_list_after.stdout)
            self.assertEqual(len(vms_after), 0)


if __name__ == "__main__":
    unittest.main()
