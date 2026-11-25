"""Unit tests for VM creation dialog, progress reporting, and worker thread."""
from __future__ import annotations

import unittest
from reims_gui.core.ctl_client import ReimsCtlClient
from reims_gui.core.models import GpuDevice, NewVmRequest
from reims_gui.qt_compat import QT_BACKEND, QtWidgets
from reims_gui.ui.dialogs.vm_creation_dialog import VmCreationDialog, VmCreationWorker


class TestVmCreation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if QT_BACKEND != "MockQt" and hasattr(QtWidgets, "QApplication"):
            app = QtWidgets.QApplication.instance()
            if not app:
                cls.app = QtWidgets.QApplication([])
            else:
                cls.app = app
        else:
            cls.app = None

    def test_client_create_vm_with_progress(self):
        client = ReimsCtlClient(mock=True)
        req = NewVmRequest(
            name="macOS-Progress-Test",
            macos_release="tahoe",
            cpus=6,
            memory_mib=16384,
            disk_size_gb=100,
            gpu=GpuDevice(name="NVIDIA RTX 3060", vendor_id=0x10DE, device_id=0x2520),
        )

        progress_events = []

        def callback(pct: int, msg: str, log: str):
            progress_events.append((pct, msg, log))

        success = client.create_vm(req, progress_callback=callback)
        self.assertTrue(success)
        self.assertGreaterEqual(len(progress_events), 4)

        # Check milestones: 25%, 50%, 75%, 100%
        percentages = [p[0] for p in progress_events]
        self.assertIn(25, percentages)
        self.assertIn(50, percentages)
        self.assertIn(75, percentages)
        self.assertIn(100, percentages)

        # Verify VM is in list
        vms = client.list_vms()
        created_vm = next((v for v in vms if v.name == "macOS-Progress-Test"), None)
        self.assertIsNotNone(created_vm)
        self.assertEqual(created_vm.cpus, 6)
        self.assertEqual(created_vm.disk_size_gb, 100.0)

    def test_vm_creation_dialog_mock_execution(self):
        import time

        client = ReimsCtlClient(mock=True)
        req = NewVmRequest(
            name="macOS-Dialog-Test",
            macos_release="sequoia",
            cpus=4,
            memory_mib=8192,
            disk_size_gb=80,
            gpu=None,
        )

        dlg = VmCreationDialog(req=req, client=client)
        self.assertIsNotNone(dlg)

        # Com backend Qt real, o worker roda em QThread assíncrono: processa
        # o event loop até o worker terminar (MockQt executa síncrono)
        app = QtWidgets.QApplication.instance() if QT_BACKEND != "MockQt" else None
        if app is not None and hasattr(dlg, "worker"):
            dlg.worker.wait(5000)
            for _ in range(100):
                if dlg.success:
                    break
                app.processEvents()
                time.sleep(0.02)

        # In mock mode, worker runs immediately and sets success=True
        self.assertTrue(dlg.success)
        if hasattr(dlg.progress_bar, "value"):
            val = dlg.progress_bar.value() if callable(dlg.progress_bar.value) else dlg.progress_bar.value
            self.assertEqual(int(val), 100)

        # Verify text log contains entries
        if hasattr(dlg.txt_logs, "toPlainText"):
            log_text = dlg.txt_logs.toPlainText()
            self.assertIn("macOS-Dialog-Test", log_text)

        # Verify dialog accept
        if hasattr(dlg, "accept"):
            dlg.accept()


if __name__ == "__main__":
    unittest.main()
