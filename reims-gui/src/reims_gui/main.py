#!/usr/bin/env python3
"""Main entry point for Reims Control Center."""

import argparse
import logging
import sys

from reims_gui.qt_compat import Qt, QtWidgets
QApplication = QtWidgets.QApplication

from reims_gui.core.ctl_client import ReimsCtlClient
from reims_gui.i18n.translator import Translator
from reims_gui.ui.main_window import MainWindow
from reims_gui.ui.theme import DARK_THEME_QSS


def main():
    parser = argparse.ArgumentParser(description="Reims Desktop GUI for reims-desktop-ctl")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock/demo mode without requiring reims-desktop-ctl or real KVM/Vulkan hardware",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        help="Force initial language (pt_BR, en_US, es_ES)",
    )
    parser.add_argument(
        "--binary",
        type=str,
        default=None,
        help="Custom path to reims-desktop-ctl binary",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # High-DPI attributes are handled automatically in Qt 6
    app = QApplication(sys.argv)
    app.setApplicationName("Reims Desktop")
    app.setOrganizationName("Reims Desktop")
    app.setStyleSheet(DARK_THEME_QSS)

    # Initialize translator
    if args.lang:
        Translator.get_instance().set_language(args.lang)

    client = ReimsCtlClient(binary_path=args.binary, mock=args.mock)
    window = MainWindow(client=client)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
