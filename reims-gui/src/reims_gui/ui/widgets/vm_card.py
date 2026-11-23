from __future__ import annotations
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from reims_gui.core.models import VmInfo, VmStatus
from reims_gui.i18n.translator import t


class VmCard(QFrame):
    """Widget card representing a single macOS Virtual Machine."""

    def __init__(
        self,
        vm: VmInfo,
        on_start: Callable[[str], None],
        on_stop: Callable[[str], None],
        on_view: Callable[[str], None],
        on_delete: Callable[[str], None],
        parent=None,
    ):
        super().__init__(parent)
        self.vm = vm
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_view = on_view
        self.on_delete = on_delete

        self.setObjectName("vmCard")
        self._init_ui()
        self.update_data(vm)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Header Row: Title + Status Badge
        top_row = QHBoxLayout()
        title_box = QVBoxLayout()
        self.lbl_name = QLabel()
        self.lbl_name.setObjectName("vmCardTitle")
        self.lbl_meta = QLabel()
        self.lbl_meta.setObjectName("vmCardMeta")
        title_box.addWidget(self.lbl_name)
        title_box.addWidget(self.lbl_meta)
        top_row.addLayout(title_box)

        top_row.addStretch()
        self.lbl_status = QLabel()
        top_row.addWidget(self.lbl_status)
        main_layout.addLayout(top_row)

        # Specs Box
        spec_box = QFrame()
        spec_box.setObjectName("specGrid")
        grid = QGridLayout(spec_box)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)

        self.lbl_cpu_title = QLabel(t("vm.specs.vcpu"))
        self.lbl_cpu_title.setProperty("class", "spec-label")
        self.lbl_cpu_val = QLabel()
        self.lbl_cpu_val.setProperty("class", "spec-value")

        self.lbl_mem_title = QLabel(t("vm.specs.memory"))
        self.lbl_mem_title.setProperty("class", "spec-label")
        self.lbl_mem_val = QLabel()
        self.lbl_mem_val.setProperty("class", "spec-value")

        self.lbl_disk_title = QLabel(t("vm.specs.disk"))
        self.lbl_disk_title.setProperty("class", "spec-label")
        self.lbl_disk_val = QLabel()
        self.lbl_disk_val.setProperty("class", "spec-value")

        grid.addWidget(self.lbl_cpu_title, 0, 0)
        grid.addWidget(self.lbl_cpu_val, 1, 0)
        grid.addWidget(self.lbl_mem_title, 0, 1)
        grid.addWidget(self.lbl_mem_val, 1, 1)
        grid.addWidget(self.lbl_disk_title, 0, 2)
        grid.addWidget(self.lbl_disk_val, 1, 2)

        main_layout.addWidget(spec_box)

        # Action Buttons Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.btn_toggle = QPushButton()
        self.btn_toggle.clicked.connect(self._handle_toggle)
        actions_row.addWidget(self.btn_toggle)

        self.btn_view = QPushButton(t("vm.actions.view"))
        self.btn_view.clicked.connect(lambda: self.on_view(self.vm.name))
        actions_row.addWidget(self.btn_view)

        self.btn_delete = QPushButton(t("vm.actions.delete"))
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(lambda: self.on_delete(self.vm.name))
        actions_row.addWidget(self.btn_delete)

        main_layout.addLayout(actions_row)

    def update_data(self, vm: VmInfo):
        self.vm = vm
        self.lbl_name.setText(vm.name)
        gpu_display = vm.gpu_name or "reims-vgpu (Vulkan)"
        self.lbl_meta.setText(f"{vm.macos_version} • {gpu_display}")

        self.lbl_cpu_val.setText(f"{vm.cpus} {t('vm.specs.cores')}")
        self.lbl_mem_val.setText(f"{vm.memory_gib} GB")
        disk_str = f"{vm.disk_size_gb:.0f} GB" if vm.disk_size_gb else "Auto"
        self.lbl_disk_val.setText(disk_str)

        # Status badge & buttons logic
        if vm.status == VmStatus.RUNNING:
            self.lbl_status.setText(f"● {t('vm.status.running')}")
            self.lbl_status.setStyleSheet("background-color: rgba(34, 197, 94, 0.15); color: #22C55E; border: 1px solid rgba(34, 197, 94, 0.4); border-radius: 12px; padding: 3px 10px; font-size: 11px; font-weight: 600;")
            self.btn_toggle.setText(t("vm.actions.stop"))
            self.btn_toggle.setObjectName("dangerBtn")
            self.btn_toggle.setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.3);")
            self.btn_view.setEnabled(True)
            self.btn_delete.setEnabled(False)
        else:
            self.lbl_status.setText(f"○ {t('vm.status.stopped')}")
            self.lbl_status.setStyleSheet("background-color: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid rgba(148, 163, 184, 0.3); border-radius: 12px; padding: 3px 10px; font-size: 11px; font-weight: 600;")
            self.btn_toggle.setText(f"▶ {t('vm.actions.start')}")
            self.btn_toggle.setObjectName("primaryBtn")
            self.btn_toggle.setStyleSheet("background-color: #2563EB; color: #FFFFFF; border: 1px solid #1D4ED8;")
            self.btn_view.setEnabled(False)
            self.btn_delete.setEnabled(True)

    def _handle_toggle(self):
        if self.vm.status == VmStatus.RUNNING:
            self.on_stop(self.vm.name)
        else:
            self.on_start(self.vm.name)

    def retranslate(self):
        self.lbl_cpu_title.setText(t("vm.specs.vcpu"))
        self.lbl_mem_title.setText(t("vm.specs.memory"))
        self.lbl_disk_title.setText(t("vm.specs.disk"))
        self.btn_view.setText(t("vm.actions.view"))
        self.btn_delete.setText(t("vm.actions.delete"))
        self.update_data(self.vm)
