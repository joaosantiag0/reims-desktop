"""Unit tests for MainWindow and UI initialization."""
from __future__ import annotations

import unittest
from pathlib import Path
from reims_gui.core.ctl_client import ReimsCtlClient
from reims_gui.ui.main_window import MainWindow


class TestMainWindow(unittest.TestCase):

    def test_main_window_init_and_icon(self):
        from reims_gui.qt_compat import QT_BACKEND, QtWidgets
        if QT_BACKEND != "MockQt" and hasattr(QtWidgets, "QApplication"):
            app = QtWidgets.QApplication.instance()
            if not app:
                app = QtWidgets.QApplication([])

        client = ReimsCtlClient(mock=True)
        window = MainWindow(client=client)
        self.assertIsNotNone(window)
        title = window.windowTitle() if callable(getattr(window, "windowTitle", None)) else window.windowTitle
        self.assertIn("Reims", str(title))
        if hasattr(window, "close"):
            window.close()

        icon_path = Path(__file__).resolve().parent.parent / "src" / "reims_gui" / "assets" / "reims-logo.png"
        self.assertTrue(icon_path.exists(), "reims-logo.png asset must exist in reims_gui/assets")


if __name__ == "__main__":
    unittest.main()
