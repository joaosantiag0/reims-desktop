"""Qt compatibility layer supporting PySide6, PyQt6, and PyQt5.

Permite que o Reims Control Center funcione de forma transparente tanto em ambientes
de desenvolvimento (macOS com PySide6) quanto no sistema operacional final (Ubuntu/Debian
com python3-pyqt6 ou python3-pyqt5). Suporta modo mock quando nenhum Qt está instalado.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

logger = logging.getLogger("reims_gui.qt_compat")

QT_BACKEND: str | None = None

# 1. Tenta PySide6
try:
    from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
    from PySide6.QtCore import Qt, QTimer, Signal, Slot  # type: ignore
    QT_BACKEND = "PySide6"
except ImportError:
    pass

# 2. Tenta PyQt6
if not QT_BACKEND:
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets  # type: ignore
        from PyQt6.QtCore import Qt, QTimer, pyqtSignal as Signal, pyqtSlot as Slot  # type: ignore
        QT_BACKEND = "PyQt6"
    except ImportError:
        pass

# 3. Tenta PyQt5
if not QT_BACKEND:
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
        from PyQt5.QtCore import Qt, QTimer, pyqtSignal as Signal, pyqtSlot as Slot  # type: ignore
        QT_BACKEND = "PyQt5"
    except ImportError:
        pass

# 4. Modo Mock / Stub para ambientes sem Qt (CI/CD ou ambiente de build puro)
if not QT_BACKEND:
    logger.warning("Nenhum backend Qt (PySide6, PyQt6, PyQt5) encontrado. Ativando modo Stub/Mock.")
    QT_BACKEND = "MockQt"

    class _MockMeta(type):
        def __getattr__(cls, name: str) -> Any:
            return _MockQtObject()
        def __call__(cls, *args: Any, **kwargs: Any) -> Any:
            return super().__call__(*args, **kwargs)

    class _MockStr(str):
        def __call__(self) -> str:
            return str(self)

    class _MockQtObject(metaclass=_MockMeta):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.text = _MockStr("")
            self.val = 0
        def setValue(self, val: int) -> None:
            self.val = val
        def value(self) -> int:
            return self.val
        def setText(self, text: str) -> None:
            self.text = _MockStr(text)
        def toPlainText(self) -> str:
            return str(self.text)
        def append(self, text: str) -> None:
            self.text = _MockStr((str(self.text) + "\n" + str(text)).strip())
        def connect(self, *args: Any, **kwargs: Any) -> Any:
            return self
        def emit(self, *args: Any, **kwargs: Any) -> Any:
            return self
        def __getattr__(self, name: str) -> Any:
            return _MockQtObject()
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return _MockQtObject()
        def __ge__(self, other: Any) -> bool:
            return True
        def __gt__(self, other: Any) -> bool:
            return True
        def __le__(self, other: Any) -> bool:
            return True
        def __lt__(self, other: Any) -> bool:
            return False
        def __eq__(self, other: Any) -> bool:
            return True
        def __bool__(self) -> bool:
            return True
        def __int__(self) -> int:
            return int(self.val)
        def findData(self, *args: Any, **kwargs: Any) -> int:
            return 0
        def windowTitle(self) -> str:
            return "Reims Control Center"

    class _MockQtCore:
        QObject = _MockQtObject
        QTimer = _MockQtObject
        QThread = _MockQtObject
        Signal = staticmethod(lambda *args, **kwargs: _MockQtObject())
        Slot = staticmethod(lambda *args, **kwargs: (lambda f: f))

    class _MockQtGui:
        QIcon = _MockQtObject
        QPixmap = _MockQtObject
        QFont = _MockQtObject
        QColor = _MockQtObject

    class _MockQtWidgets:
        QApplication = _MockQtObject
        QMainWindow = _MockQtObject
        QWidget = _MockQtObject
        QDialog = _MockQtObject
        QLabel = _MockQtObject
        QPushButton = _MockQtObject
        QVBoxLayout = _MockQtObject
        QHBoxLayout = _MockQtObject
        QGridLayout = _MockQtObject
        QFormLayout = _MockQtObject
        QFrame = _MockQtObject
        QScrollArea = _MockQtObject
        QLineEdit = _MockQtObject
        QSpinBox = _MockQtObject
        QSlider = _MockQtObject
        QComboBox = _MockQtObject
        QMessageBox = _MockQtObject
        QProgressBar = _MockQtObject
        QTextEdit = _MockQtObject
        QCheckBox = _MockQtObject

    QtCore = _MockQtCore()  # type: ignore
    QtGui = _MockQtGui()  # type: ignore
    QtWidgets = _MockQtWidgets()  # type: ignore
    QTimer = _MockQtObject  # type: ignore
    Signal = lambda *args, **kwargs: _MockQtObject()  # type: ignore
    Slot = lambda *args, **kwargs: (lambda f: f)  # type: ignore

    class _MockQt:
        class AlignmentFlag:
            AlignCenter = 0x0004 | 0x0080
            AlignLeft = 0x0001
            AlignRight = 0x0002
            AlignTop = 0x0020
            AlignBottom = 0x0040
        AlignCenter = AlignmentFlag.AlignCenter
        AlignLeft = AlignmentFlag.AlignLeft
        AlignRight = AlignmentFlag.AlignRight
        AlignTop = AlignmentFlag.AlignTop
        AlignBottom = AlignmentFlag.AlignBottom

        class Orientation:
            Horizontal = 1
            Vertical = 2
        Horizontal = Orientation.Horizontal
        Vertical = Orientation.Vertical

        class CursorShape:
            PointingHandCursor = 13
            ArrowCursor = 0
        PointingHandCursor = CursorShape.PointingHandCursor
        ArrowCursor = CursorShape.ArrowCursor

    Qt = _MockQt()  # type: ignore

else:
    logger.info(f"Usando backend Qt: {QT_BACKEND}")

    # Compatibilidade bidirecional de enums entre Qt5 e Qt6
    # Qt5 -> Qt6 enums
    if not hasattr(Qt, "AlignmentFlag"):
        class _AlignmentFlag:
            AlignCenter = getattr(Qt, "AlignCenter", 0x0004 | 0x0080)
            AlignLeft = getattr(Qt, "AlignLeft", 0x0001)
            AlignRight = getattr(Qt, "AlignRight", 0x0002)
            AlignTop = getattr(Qt, "AlignTop", 0x0020)
            AlignBottom = getattr(Qt, "AlignBottom", 0x0040)
        Qt.AlignmentFlag = _AlignmentFlag  # type: ignore

    if not hasattr(Qt, "Orientation"):
        class _Orientation:
            Horizontal = getattr(Qt, "Horizontal", 1)
            Vertical = getattr(Qt, "Vertical", 2)
        Qt.Orientation = _Orientation  # type: ignore

    if not hasattr(Qt, "CursorShape"):
        class _CursorShape:
            PointingHandCursor = getattr(Qt, "PointingHandCursor", 13)
            ArrowCursor = getattr(Qt, "ArrowCursor", 0)
        Qt.CursorShape = _CursorShape  # type: ignore

    # Qt6 -> Qt5 unscoped aliases
    if hasattr(Qt, "AlignmentFlag"):
        for attr in ("AlignCenter", "AlignLeft", "AlignRight", "AlignTop", "AlignBottom"):
            if not hasattr(Qt, attr) and hasattr(Qt.AlignmentFlag, attr):
                setattr(Qt, attr, getattr(Qt.AlignmentFlag, attr))

    if hasattr(Qt, "Orientation"):
        for attr in ("Horizontal", "Vertical"):
            if not hasattr(Qt, attr) and hasattr(Qt.Orientation, attr):
                setattr(Qt, attr, getattr(Qt.Orientation, attr))

    if hasattr(Qt, "CursorShape"):
        for attr in ("PointingHandCursor", "ArrowCursor"):
            if not hasattr(Qt, attr) and hasattr(Qt.CursorShape, attr):
                setattr(Qt, attr, getattr(Qt.CursorShape, attr))

# Re-exporta classes e utilitarios
__all__ = [
    "QT_BACKEND",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "Qt",
    "QTimer",
    "Signal",
    "Slot",
]
