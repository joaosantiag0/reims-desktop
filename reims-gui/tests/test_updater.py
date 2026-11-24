from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reims_gui.core.updater import ReleaseAsset, ReleaseInfo, SystemUpdater
from reims_gui.ui.dialogs.update_dialog import UpdateDialog


class TestSystemUpdater(unittest.TestCase):
    """Testes unitários para o sistema de atualização do ReimsOS."""

    def setUp(self):
        self.updater = SystemUpdater(repo="steelbrain/reims-os", current_version="0.1.0")

    def test_version_parsing(self):
        self.assertEqual(SystemUpdater.parse_version("0.1.0"), (0, 1, 0))
        self.assertEqual(SystemUpdater.parse_version("v0.2.0"), (0, 2, 0))
        self.assertEqual(SystemUpdater.parse_version("V1.4.12"), (1, 4, 12))
        self.assertEqual(SystemUpdater.parse_version("invalid"), (0, 0, 0))

    def test_version_comparison(self):
        self.assertTrue(self.updater.is_newer("0.2.0", "0.1.0"))
        self.assertTrue(self.updater.is_newer("v1.0.0", "0.9.9"))
        self.assertFalse(self.updater.is_newer("0.1.0", "0.1.0"))
        self.assertFalse(self.updater.is_newer("0.0.9", "0.1.0"))

    def test_mock_check_for_updates(self):
        os.environ["REIMS_MOCK_UPDATER"] = "1"
        os.environ["REIMS_MOCK_TAG"] = "v0.2.0"
        try:
            release = self.updater.check_for_updates()
            self.assertIsNotNone(release)
            self.assertEqual(release.tag_name, "v0.2.0")
            self.assertEqual(release.version, "0.2.0")
            self.assertGreater(len(release.deb_assets), 0)
            self.assertTrue(all(a.name.endswith(".deb") for a in release.deb_assets))
        finally:
            os.environ.pop("REIMS_MOCK_UPDATER", None)
            os.environ.pop("REIMS_MOCK_TAG", None)

    def test_mock_download_assets(self):
        os.environ["REIMS_MOCK_UPDATER"] = "1"
        try:
            release = self.updater.check_for_updates()
            self.assertIsNotNone(release)

            progress_calls = []
            def progress(d, t, name):
                progress_calls.append((d, t, name))

            with tempfile.TemporaryDirectory() as tmpdir:
                debs = self.updater.download_assets(release, tmpdir, progress_callback=progress)
                self.assertEqual(len(debs), len(release.deb_assets))
                for deb in debs:
                    self.assertTrue(deb.exists())
                    self.assertGreater(deb.stat().st_size, 0)
                self.assertGreater(len(progress_calls), 0)
        finally:
            os.environ.pop("REIMS_MOCK_UPDATER", None)

    def test_mock_install_debs(self):
        os.environ["REIMS_MOCK_UPDATER"] = "1"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                fake_deb = Path(tmpdir) / "reims-core_0.2.0_all.deb"
                fake_deb.write_bytes(b"TEST")
                ok, msg = self.updater.install_debs([fake_deb], dry_run=True)
                self.assertTrue(ok)
                self.assertIn("Simulação", msg)
        finally:
            os.environ.pop("REIMS_MOCK_UPDATER", None)

    def test_mock_update_from_git(self):
        os.environ["REIMS_MOCK_UPDATER"] = "1"
        try:
            ok, msg = self.updater.update_from_git(dry_run=True)
            self.assertTrue(ok)
            self.assertIn("Simulação", msg)
        finally:
            os.environ.pop("REIMS_MOCK_UPDATER", None)

    def test_mock_update_system(self):
        os.environ["REIMS_MOCK_UPDATER"] = "1"
        try:
            ok, msg = self.updater.update_system(dry_run=True)
            self.assertTrue(ok)
            self.assertIn("Simulação", msg)
        finally:
            os.environ.pop("REIMS_MOCK_UPDATER", None)

    def test_cli_reims_update(self):
        repo_root = Path(__file__).resolve().parent.parent.parent
        cli_desktop_update = repo_root / "packaging" / "templates" / "reims-core" / "usr" / "bin" / "reims-desktop-update"
        cli_update = repo_root / "packaging" / "templates" / "reims-core" / "usr" / "bin" / "reims-update"
        self.assertTrue(cli_desktop_update.exists())
        self.assertTrue(cli_update.exists())

        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root / "reims-gui" / "src")

        # 1. Test --version on reims-desktop-update
        res_ver = subprocess.run([sys.executable, str(cli_desktop_update), "--version"], capture_output=True, text=True, env=env)
        self.assertEqual(res_ver.returncode, 0)
        self.assertTrue(
            "Reims Desktop versão instalada" in res_ver.stdout or "Reims Desktop installed version" in res_ver.stdout,
            f"Unexpected output: {res_ver.stdout}",
        )

        # 2. Test --mock --check on reims-desktop-update
        res_check = subprocess.run([sys.executable, str(cli_desktop_update), "--mock", "--check"], capture_output=True, text=True, env=env)
        self.assertEqual(res_check.returncode, 0)
        self.assertTrue(
            "Nova versão encontrada" in res_check.stdout or "New version found" in res_check.stdout,
            f"Unexpected output: {res_check.stdout}",
        )

        # 3. Test --mock --dry-run --yes on reims-desktop-update
        res_run = subprocess.run([sys.executable, str(cli_desktop_update), "--mock", "--dry-run", "--yes"], capture_output=True, text=True, env=env)
        self.assertEqual(res_run.returncode, 0)
        self.assertTrue(
            "Atualização do Reims Desktop concluída" in res_run.stdout or "Reims Desktop update completed" in res_run.stdout,
            f"Unexpected output: {res_run.stdout}",
        )

        # 4. Test --mock --git --dry-run on reims-desktop-update
        res_git = subprocess.run([sys.executable, str(cli_desktop_update), "--mock", "--git", "--dry-run"], capture_output=True, text=True, env=env)
        self.assertEqual(res_git.returncode, 0)
        self.assertTrue(
            "Simulação de atualização via git" in res_git.stdout or "git" in res_git.stdout.lower(),
            f"Unexpected output: {res_git.stdout}",
        )

        # 5. Test --mock --git --branch development --dry-run
        res_branch = subprocess.run([sys.executable, str(cli_desktop_update), "--mock", "--git", "--branch", "development", "--dry-run"], capture_output=True, text=True, env=env)
        self.assertEqual(res_branch.returncode, 0)
        self.assertIn("development", res_branch.stdout)

        # 6. Test --mock --system --dry-run
        res_sys = subprocess.run([sys.executable, str(cli_desktop_update), "--mock", "--system", "--dry-run"], capture_output=True, text=True, env=env)
        self.assertEqual(res_sys.returncode, 0)
        self.assertIn("Simulação", res_sys.stdout)

        # 7. Test --mock --full --dry-run --yes
        res_full = subprocess.run([sys.executable, str(cli_desktop_update), "--mock", "--full", "--dry-run", "--yes"], capture_output=True, text=True, env=env)
        self.assertEqual(res_full.returncode, 0)
        self.assertIn("Simulação", res_full.stdout)

        # 8. Test wrapper reims-update
        res_wrap = subprocess.run([str(cli_update), "--version"], capture_output=True, text=True, env=env)
        self.assertEqual(res_wrap.returncode, 0)
        self.assertIn("Reims Desktop", res_wrap.stdout)

    def test_update_dialog_mock(self):
        os.environ["REIMS_MOCK_UPDATER"] = "1"
        try:
            from reims_gui.qt_compat import QT_BACKEND, QtWidgets
            if QT_BACKEND != "MockQt" and hasattr(QtWidgets, "QApplication"):
                app = QtWidgets.QApplication.instance()
                if not app:
                    app = QtWidgets.QApplication([])

            release = self.updater.check_for_updates()
            self.assertIsNotNone(release)
            dlg = UpdateDialog(release=release, updater=self.updater)
            self.assertIsNotNone(dlg)
            # Simula clique no botão de atualizar
            dlg._handle_update()
            status_text = dlg.lbl_status.text() if callable(getattr(dlg.lbl_status, "text", None)) else dlg.lbl_status.text
            self.assertIn("sucesso", str(status_text).lower())

            # Testa com checkbox de atualização do sistema marcado
            if hasattr(dlg.chk_system_update, "setChecked"):
                dlg.chk_system_update.setChecked(True)
            dlg._handle_update()
            status_text2 = dlg.lbl_status.text() if callable(getattr(dlg.lbl_status, "text", None)) else dlg.lbl_status.text
            self.assertIn("sucesso", str(status_text2).lower())
            if hasattr(dlg, "close"):
                dlg.close()
        finally:
            os.environ.pop("REIMS_MOCK_UPDATER", None)


if __name__ == "__main__":
    unittest.main()
