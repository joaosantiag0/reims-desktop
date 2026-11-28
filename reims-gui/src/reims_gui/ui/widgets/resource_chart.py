"""Live CPU/RAM usage charts for the Reims Control Center.

Dois mini-gráficos de área (estilo monitor de sistema) desenhados com QPainter,
sem dependências externas de Qt Charts. `UsageChart` guarda o histórico e
desenha; `ResourceMonitorBar` agrupa CPU + RAM e é embutido na janela principal.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Optional

from reims_gui.qt_compat import QtCore, QtGui, Qt, QTimer, QtWidgets
QFrame = QtWidgets.QFrame
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QWidget = QtWidgets.QWidget

from reims_gui.core.system_stats import SystemSample, SystemStatsSampler
from reims_gui.i18n.translator import t

HISTORY_SIZE = 60  # ~4 min de histórico com o timer de 4 s


class UsageChart(QWidget):
    """Área de gráfico rolante 0-100% para uma métrica (CPU ou RAM)."""

    def __init__(self, color: str, label: str = "", parent=None):
        super().__init__(parent)
        self._color = QtGui.QColor(color)
        self._history: Deque[float] = deque(maxlen=HISTORY_SIZE)
        self._last_value: float = 0.0
        self._label = label
        self.setMinimumHeight(46)
        self.setMinimumWidth(120)

    @property
    def last_value(self) -> float:
        return self._last_value

    @property
    def point_count(self) -> int:
        return len(self._history)

    def set_label(self, label: str) -> None:
        self._label = label
        self.update()

    def set_value(self, value: float) -> None:
        self._last_value = max(0.0, min(100.0, float(value)))
        self._history.append(self._last_value)
        self.update()

    def clear(self) -> None:
        self._history.clear()
        self._last_value = 0.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        painter = QtGui.QPainter(self)
        try:
            w, h = self.width(), self.height()
            if w <= 2 or h <= 2:
                return

            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

            # Grade a 0 / 50 / 100%
            pen = QtGui.QPen(QtGui.QColor(148, 163, 184, 40))
            pen.setWidthF(1.0)
            painter.setPen(pen)
            for frac in (0.0, 0.5, 1.0):
                y = h - 1 - frac * (h - 2)
                painter.drawLine(0, int(y), w, int(y))

            points = list(self._history)
            if points:
                self._draw_series(painter, points, w, h)

            # Valor atual no canto
            painter.setPen(QtGui.QPen(QtGui.QColor(241, 245, 249)))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(
                QtCore.QRect(4, 2, w - 8, 12),
                int(Qt.AlignmentFlag.AlignRight),
                f"{self._label} {self._last_value:.0f}%",
            )
        finally:
            painter.end()

    def _draw_series(self, painter: QtGui.QPainter, points, w: int, h: int) -> None:
        n = len(points)
        # Alinhar à direita: histórico cresce da direita? Não — o mais novo é o
        # último ponto e entra pela direita, estilo monitor de sistema.
        usable = max(n - 1, 1)
        step = (w - 2) / HISTORY_SIZE

        def xy(i: int, v: float):
            x = w - 1 - (n - 1 - i) * step
            y = h - 1 - (v / 100.0) * (h - 2)
            return x, y

        path = QtGui.QPainterPath()
        first_x, first_y = xy(0, points[0])
        path.moveTo(first_x, first_y)
        for i, v in enumerate(points[1:], start=1):
            path.lineTo(*xy(i, v))

        # Área preenchida
        fill_path = QtGui.QPainterPath(path)
        fill_path.lineTo(first_x + (n - 1) * step, h - 1)
        fill_path.lineTo(first_x, h - 1)
        fill_path.closeSubpath()

        gradient = QtGui.QLinearGradient(0, 0, 0, h)
        top = QtGui.QColor(self._color)
        top.setAlpha(140)
        bottom = QtGui.QColor(self._color)
        bottom.setAlpha(20)
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(1.0, bottom)

        painter.setPen(QtGui.QPen(QtCore.Qt.PenStyle.NoPen))
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawPath(fill_path)

        # Linha do valor
        pen = QtGui.QPen(self._color)
        pen.setWidthF(1.6)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


class ResourceMonitorBar(QFrame):
    """Painel "Uso do Host": gráficos ao vivo de CPU e RAM."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resourceBar")
        self.sampler = SystemStatsSampler()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet(
            "font-weight: 700; color: #FFFFFF; font-size: 12px;"
        )
        layout.addWidget(self.lbl_title)

        self.chart_cpu = UsageChart("#3B82F6", "CPU")
        self.chart_ram = UsageChart("#8B5CF6", "RAM")
        layout.addWidget(self.chart_cpu, 1)
        layout.addWidget(self.chart_ram, 1)

        self.lbl_ram_detail = QLabel()
        self.lbl_ram_detail.setStyleSheet(
            "color: #94A3B8; font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(self.lbl_ram_detail)

        self.retranslate()

    def refresh(self) -> None:
        """Amostra o host e atualiza os gráficos (best-effort)."""
        sample: Optional[SystemSample] = self.sampler.sample()
        self.update_sample(sample)

    def update_sample(self, sample: Optional[SystemSample]) -> None:
        if sample is None:
            return
        self.chart_cpu.set_value(sample.cpu_percent)
        self.chart_ram.set_value(sample.ram_percent)
        self.lbl_ram_detail.setText(
            f"{sample.ram_used_gb:.1f} / {sample.ram_total_gb:.1f} GB"
        )

    def retranslate(self) -> None:
        self.lbl_title.setText(f"{t('resources.title')}:")

        self.chart_cpu.set_label(t("resources.cpu"))
        self.chart_ram.set_label(t("resources.ram"))
