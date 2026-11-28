"""Unit tests for reims_gui.core.prefs (persistent user preferences)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from reims_gui.core import prefs


class PrefsEnvTestCase(unittest.TestCase):
    """Base that isolates prefs storage into a temporary XDG config dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self._tmp.name
        self.addCleanup(self._restore)

    def _restore(self):
        if self._old_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self._old_xdg
        self._tmp.cleanup()


class TestPrefs(PrefsEnvTestCase):

    def test_config_file_location(self):
        expected = Path(self._tmp.name) / "reims-desktop" / "prefs.json"
        self.assertEqual(prefs.config_file(), expected)

    def test_load_missing_file_returns_empty(self):
        self.assertEqual(prefs.load_prefs(), {})
        self.assertIsNone(prefs.get_last_vm())
        self.assertEqual(prefs.get_last_vm_policy(), prefs.POLICY_ASK)

    def test_save_and_load_roundtrip(self):
        prefs.set_last_vm("macOS-Tahoe")
        prefs.set_last_vm_policy(prefs.POLICY_ALWAYS)
        self.assertEqual(prefs.get_last_vm(), "macOS-Tahoe")
        self.assertEqual(prefs.get_last_vm_policy(), prefs.POLICY_ALWAYS)
        # Ensure the file is real JSON on disk
        with open(prefs.config_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data[prefs.KEY_LAST_VM], "macOS-Tahoe")

    def test_invalid_policy_is_rejected_and_sanitized(self):
        prefs.set_last_vm_policy("always")
        # Corrupt the file with an unknown policy value
        with open(prefs.config_file(), "w", encoding="utf-8") as f:
            json.dump({prefs.KEY_LAST_VM_POLICY: "sometimes"}, f)
        # Loading sanitizes it back to the default "ask"
        self.assertEqual(prefs.load_prefs()[prefs.KEY_LAST_VM_POLICY], prefs.POLICY_ASK)
        # And setting an invalid policy is refused
        prefs.set_last_vm_policy("sometimes")
        self.assertEqual(prefs.get_last_vm_policy(), prefs.POLICY_ASK)

    def test_corrupt_file_returns_empty(self):
        prefs.config_file().parent.mkdir(parents=True, exist_ok=True)
        with open(prefs.config_file(), "w", encoding="utf-8") as f:
            f.write("not json{")
        self.assertEqual(prefs.load_prefs(), {})


if __name__ == "__main__":
    unittest.main()
