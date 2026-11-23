"""Testes unitários para a camada de compatibilidade Qt (qt_compat)."""
from __future__ import annotations

import unittest
from reims_gui.qt_compat import QT_BACKEND, Qt, QTimer, QtCore, QtGui, QtWidgets


class TestQtCompat(unittest.TestCase):
    """Verifica se o backend Qt ativo fornece todos os símbolos e enums necessários."""

    def test_backend_detected(self):
        self.assertIn(QT_BACKEND, ["PySide6", "PyQt6", "PyQt5", "MockQt"])

    def test_core_classes_exported(self):
        self.assertTrue(hasattr(QtCore, "QObject"))
        self.assertTrue(hasattr(QtWidgets, "QWidget"))
        self.assertTrue(hasattr(QtWidgets, "QMainWindow"))
        self.assertTrue(hasattr(QtWidgets, "QApplication"))

    def test_enum_compatibility(self):
        # Alignment flags
        self.assertTrue(hasattr(Qt, "AlignCenter"))
        self.assertTrue(hasattr(Qt, "AlignmentFlag"))
        self.assertTrue(hasattr(Qt.AlignmentFlag, "AlignCenter"))

        # Orientation flags
        self.assertTrue(hasattr(Qt, "Horizontal"))
        self.assertTrue(hasattr(Qt, "Orientation"))
        self.assertTrue(hasattr(Qt.Orientation, "Horizontal"))

        # Cursor flags
        self.assertTrue(hasattr(Qt, "PointingHandCursor"))
        self.assertTrue(hasattr(Qt, "CursorShape"))
        self.assertTrue(hasattr(Qt.CursorShape, "PointingHandCursor"))


if __name__ == "__main__":
    unittest.main()
