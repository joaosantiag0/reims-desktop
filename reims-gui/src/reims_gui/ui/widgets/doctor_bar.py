from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
)

from reims_gui.core.models import DoctorHealth
from reims_gui.i18n.translator import t


class DoctorBar(QWidget):
    """Horizontal banner showing real-time virtualization and host health."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("doctorBar")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(18)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-weight: 700; color: #FFFFFF; font-size: 12px;")
        layout.addWidget(self.lbl_title)

        self.lbl_kvm = QLabel()
        self.lbl_udmabuf = QLabel()
        self.lbl_vulkan = QLabel()
        self.lbl_qemu = QLabel()

        for lbl in (self.lbl_kvm, self.lbl_udmabuf, self.lbl_vulkan, self.lbl_qemu):
            layout.addWidget(lbl)

        layout.addStretch()
        self.retranslate()

    def update_health(self, health: DoctorHealth):
        self._set_item_status(self.lbl_kvm, "KVM", health.kvm_ok)
        self._set_item_status(self.lbl_udmabuf, "udmabuf", health.udmabuf_ok)
        self._set_item_status(self.lbl_vulkan, "Vulkan", health.vulkan_ok)
        self._set_item_status(self.lbl_qemu, "QEMU vGPU", health.qemu_ok)

    def _set_item_status(self, label: QLabel, name: str, is_ok: bool):
        if is_ok:
            label.setText(f"✓ {name}")
            label.setProperty("class", "doctor-item-ok")
            label.setStyleSheet("color: #22C55E; font-weight: 600; font-size: 12px;")
        else:
            label.setText(f"✗ {name}")
            label.setProperty("class", "doctor-item-warn")
            label.setStyleSheet("color: #EF4444; font-weight: 600; font-size: 12px;")

    def retranslate(self):
        self.lbl_title.setText(f"{t('doctor.title')}:")
