"""Unit tests for the "open last VM at startup" feature in MainWindow."""
from __future__ import annotations

import unittest

from reims_gui.core import prefs
from reims_gui.core.ctl_client import ReimsCtlClient
from reims_gui.core.models import VmStatus
from reims_gui.ui.main_window import MainWindow


def _ensure_qapp():
    from reims_gui.qt_compat import QT_BACKEND, QtWidgets
    if QT_BACKEND != "MockQt" and hasattr(QtWidgets, "QApplication"):
        app = QtWidgets.QApplication.instance()
        if not app:
            app = QtWidgets.QApplication([])
    return None


class PrefsEnvTestCase(unittest.TestCase):
    """Base that isolates prefs storage into a temporary XDG config dir."""

    def setUp(self):
        import os
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self._old_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self._tmp.name
        self.addCleanup(self._restore)

    def _restore(self):
        import os
        if self._old_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self._old_xdg
        self._tmp.cleanup()


class TestOpenLastVm(PrefsEnvTestCase):

    def setUp(self):
        super().setUp()
        _ensure_qapp()
        self.client = ReimsCtlClient(mock=True)

    def _window(self, open_last_vm: bool = False) -> MainWindow:
        window = MainWindow(client=self.client, open_last_vm=open_last_vm)
        self.addCleanup(window.close)
        return window

    def test_starting_vm_records_last_vm(self):
        window = self._window()
        window._handle_start_vm("macOS-Sequoia-Test")
        self.assertEqual(prefs.get_last_vm(), "macOS-Sequoia-Test")

    def test_policy_always_auto_starts_last_vm(self):
        prefs.set_last_vm("macOS-Sequoia-Test")
        prefs.set_last_vm_policy(prefs.POLICY_ALWAYS)
        window = self._window()
        window._maybe_open_last_vm()
        vms = {vm.name: vm for vm in self.client.list_vms()}
        self.assertEqual(vms["macOS-Sequoia-Test"].status, VmStatus.RUNNING)

    def test_open_last_vm_flag_forces_auto_start(self):
        prefs.set_last_vm("macOS-Sequoia-Test")
        prefs.set_last_vm_policy(prefs.POLICY_ASK)
        window = self._window(open_last_vm=True)
        # The flag must bypass the ask-prompt: no dialog callback wired here.
        calls = []
        window._prompt_open_last_vm = lambda name: calls.append(name) or "skip"
        window._maybe_open_last_vm()
        self.assertEqual(calls, [], "flag should auto-start without prompting")
        vms = {vm.name: vm for vm in self.client.list_vms()}
        self.assertEqual(vms["macOS-Sequoia-Test"].status, VmStatus.RUNNING)

    def test_policy_never_does_nothing(self):
        prefs.set_last_vm("macOS-Sequoia-Test")
        prefs.set_last_vm_policy(prefs.POLICY_NEVER)
        window = self._window()
        calls = []
        window._prompt_open_last_vm = lambda name: calls.append(name) or "skip"
        window._maybe_open_last_vm()
        self.assertEqual(calls, [])
        vms = {vm.name: vm for vm in self.client.list_vms()}
        self.assertEqual(vms["macOS-Sequoia-Test"].status, VmStatus.STOPPED)

    def test_no_last_vm_recorded_does_nothing(self):
        window = self._window()
        calls = []
        window._prompt_open_last_vm = lambda name: calls.append(name) or "skip"
        window._maybe_open_last_vm()
        self.assertEqual(calls, [])

    def test_last_vm_deleted_is_ignored(self):
        prefs.set_last_vm("VM-Que-Nao-Existe")
        prefs.set_last_vm_policy(prefs.POLICY_ALWAYS)
        window = self._window()
        calls = []
        window._prompt_open_last_vm = lambda name: calls.append(name) or "skip"
        window._maybe_open_last_vm()
        self.assertEqual(calls, [])

    def test_already_running_vm_is_not_restarted(self):
        prefs.set_last_vm("macOS-Tahoe-Dev")  # mock starts it RUNNING
        prefs.set_last_vm_policy(prefs.POLICY_ALWAYS)
        started = []
        original = self.client.start_vm
        self.client.start_vm = lambda name: started.append(name) or original(name)
        window = self._window()
        window._maybe_open_last_vm()
        self.assertEqual(started, [])

    def test_ask_policy_open_choice_starts_and_keeps_ask(self):
        prefs.set_last_vm("macOS-Sequoia-Test")
        prefs.set_last_vm_policy(prefs.POLICY_ASK)
        window = self._window()
        window._prompt_open_last_vm = lambda name: "open"
        window._maybe_open_last_vm()
        vms = {vm.name: vm for vm in self.client.list_vms()}
        self.assertEqual(vms["macOS-Sequoia-Test"].status, VmStatus.RUNNING)
        self.assertEqual(prefs.get_last_vm_policy(), prefs.POLICY_ASK)

    def test_ask_policy_remember_no_persists_never(self):
        prefs.set_last_vm("macOS-Sequoia-Test")
        prefs.set_last_vm_policy(prefs.POLICY_ASK)
        window = self._window()
        window._prompt_open_last_vm = lambda name: "never"
        window._maybe_open_last_vm()
        self.assertEqual(prefs.get_last_vm_policy(), prefs.POLICY_NEVER)
        vms = {vm.name: vm for vm in self.client.list_vms()}
        self.assertEqual(vms["macOS-Sequoia-Test"].status, VmStatus.STOPPED)

    def test_ask_policy_remember_yes_persists_always(self):
        prefs.set_last_vm("macOS-Sequoia-Test")
        prefs.set_last_vm_policy(prefs.POLICY_ASK)
        window = self._window()
        window._prompt_open_last_vm = lambda name: "always"
        window._maybe_open_last_vm()
        self.assertEqual(prefs.get_last_vm_policy(), prefs.POLICY_ALWAYS)
        vms = {vm.name: vm for vm in self.client.list_vms()}
        self.assertEqual(vms["macOS-Sequoia-Test"].status, VmStatus.RUNNING)


if __name__ == "__main__":
    unittest.main()
