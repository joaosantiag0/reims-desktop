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
                self.assertTrue(any("reims-desktop-archive-keyring.gpg" in n for n in names))
                self.assertTrue(any("usr/bin/reims-desktop-update" in n for n in names))
                self.assertTrue(any("usr/bin/reims-boot-theme-apply" in n for n in names))
                self.assertTrue(any("usr/bin/reims-clean-bloatware" in n for n in names))
                self.assertTrue(any("usr/bin/reims-update" in n for n in names))
                self.assertTrue(any("themes/reims/theme.txt" in n for n in names))
                self.assertTrue(any("themes/reims/background.png" in n for n in names))

                # O source apt deve ser assinado (sem [trusted=yes])
                for n in names:
                    if n.endswith("reims.list"):
                        member = tar.extractfile(tar.getmember(n))
                        content = member.read().decode("utf-8") if member else ""
                        self.assertIn("signed-by", content)
                        self.assertNotIn("trusted=yes", content)
                        self.assertIn("noble main", content)

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

    def test_build_version_override(self):
        """REIMS_VERSION deve trocar Version do control e o nome do .deb."""
        self.addCleanup(self._remove_test_artifacts)
        env = dict(os.environ, REIMS_VERSION="0.1.1+test.20261124")
        res = subprocess.run(
            [str(self.scripts_dir / "build_core_deb.sh")],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(res.returncode, 0, f"build_core_deb.sh failed: {res.stderr}")

        deb = self.dist_dir / "reims-core_0.1.1+test.20261124_all.deb"
        self.assertTrue(deb.exists(), "Version-overridden deb was not created")

        members = self._extract_deb_members(deb)
        with tempfile.TemporaryDirectory() as tmp:
            ctrl_tar = Path(tmp) / "control.tar.gz"
            ctrl_tar.write_bytes(members["control.tar.gz"])
            with tarfile.open(ctrl_tar, "r:gz") as tar:
                member = tar.extractfile("./control") or tar.extractfile("./DEBIAN/control")
                control = member.read().decode("utf-8") if member else ""
                self.assertIn("Version: 0.1.1+test.20261124", control)

    def test_firstboot_setup_packaging_and_guard(self):
        """First-boot: scripts + autostart no deb; flag guarda re-execução."""
        cmd = [str(self.scripts_dir / "build_core_deb.sh")]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"build_core_deb.sh failed: {res.stderr}")

        core_deb = self.dist_dir / "reims-core_0.1.0_all.deb"
        self.assertTrue(core_deb.exists())

        members = self._extract_deb_members(core_deb)
        with tempfile.TemporaryDirectory() as tmp:
            data_tar = Path(tmp) / "data.tar.gz"
            data_tar.write_bytes(members["data.tar.gz"])
            with tarfile.open(data_tar, "r:gz") as tar:
                names = tar.getnames()
                self.assertTrue(any("usr/bin/reims-firstboot-setup" in n for n in names))
                self.assertTrue(any("usr/bin/reims-firstboot-user" in n for n in names))
                self.assertTrue(any("autostart/reims-firstboot.desktop" in n for n in names))

        # Guard do flag: com firstboot-done presente, sai 0 sem tocar em rede/dpkg
        setup = self.repo_root / "packaging" / "templates" / "reims-core" / "usr" / "bin" / "reims-firstboot-setup"
        os.chmod(setup, 0o755)
        with tempfile.TemporaryDirectory() as tmp:
            flag_dir = Path(tmp) / "state"
            flag_dir.mkdir()
            (flag_dir / "firstboot-done").touch()
            env = dict(os.environ, REIMS_STATE_DIR=str(flag_dir))
            res = subprocess.run([str(setup)], capture_output=True, text=True, env=env)
            self.assertEqual(res.returncode, 0, f"setup failed: {res.stderr}")
            self.assertIn("já concluído", res.stdout)

        # Helper de sessão também respeita o flag (sai sem pkexec/nmcli)
        helper = self.repo_root / "packaging" / "templates" / "reims-core" / "usr" / "bin" / "reims-firstboot-user"
        os.chmod(helper, 0o755)
        with tempfile.TemporaryDirectory() as tmp:
            flag_dir = Path(tmp) / "state"
            flag_dir.mkdir()
            (flag_dir / "firstboot-done").touch()
            env = dict(os.environ, REIMS_STATE_DIR=str(flag_dir))
            res = subprocess.run([str(helper)], capture_output=True, text=True, env=env)
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout, "")

    def _remove_test_artifacts(self):
        """Remove debs gerados por testes (não podem vazar para releases)."""
        if self.dist_dir.is_dir():
            for deb in self.dist_dir.glob("*+test.*.deb"):
                deb.unlink(missing_ok=True)

    def test_generate_apt_repo_metadata(self):
        """generate_apt_repo.py deve produzir dists/pool com Packages por arquitetura."""
        import sys

        sys.path.insert(0, str(self.repo_root / "scripts"))
        try:
            from generate_apt_repo import generate_apt_repo
        finally:
            sys.path.pop(0)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "repo"
            if not all(
                (self.dist_dir / n).exists()
                for n in ("reims-core_0.1.0_all.deb", "reims-gui_0.1.0_all.deb", "reims-vgpu_0.1.0_amd64.deb")
            ):
                res = subprocess.run([str(self.scripts_dir / "build_all.sh")], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, f"build_all.sh failed: {res.stderr}")
            generate_apt_repo(self.dist_dir, out_dir)

            # Pool com todos os debs
            pool = out_dir / "pool" / "main"
            for name in ("reims-core_0.1.0_all.deb", "reims-gui_0.1.0_all.deb", "reims-vgpu_0.1.0_amd64.deb"):
                self.assertTrue((pool / name).exists(), f"{name} missing from pool")

            # Packages por arquitetura
            pkg_all = (out_dir / "dists" / "noble" / "main" / "binary-all" / "Packages").read_text()
            self.assertIn("Package: reims-core", pkg_all)
            self.assertIn("Package: reims-gui", pkg_all)
            self.assertNotIn("Package: reims-vgpu", pkg_all)  # vgpu é amd64, vai no índice amd64

            pkg_amd64 = (out_dir / "dists" / "noble" / "main" / "binary-amd64" / "Packages").read_text()
            self.assertIn("Package: reims-vgpu", pkg_amd64)
            self.assertIn("Package: reims-core", pkg_amd64)  # all entra no amd64 também

            # Release com checksums dos índices
            release = (out_dir / "dists" / "noble" / "Release").read_text()
            self.assertIn("Suite: noble", release)
            self.assertIn("SHA256:", release)
            self.assertIn("main/binary-amd64/Packages", release)

            # Landing page instrui assinatura, não trusted=yes
            index_html = (out_dir / "index.html").read_text()
            self.assertIn("signed-by=/usr/share/keyrings/reims-desktop-archive-keyring.gpg", index_html)
            self.assertNotIn("trusted=yes", index_html)


if __name__ == "__main__":
    unittest.main()
