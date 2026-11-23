from __future__ import annotations
from typing import List, Optional

from reims_gui.qt_compat import Qt, QtWidgets
QComboBox = QtWidgets.QComboBox
QDialog = QtWidgets.QDialog
QFormLayout = QtWidgets.QFormLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QPushButton = QtWidgets.QPushButton
QSlider = QtWidgets.QSlider
QSpinBox = QtWidgets.QSpinBox
QVBoxLayout = QtWidgets.QVBoxLayout

from reims_gui.core.models import GpuDevice, NewVmRequest
from reims_gui.i18n.translator import t


class NewVmDialog(QDialog):
    """Dialog wizard to create and configure a new macOS Virtual Machine."""

    def __init__(self, available_gpus: List[GpuDevice], parent=None):
        super().__init__(parent)
        self.available_gpus = available_gpus
        self.setWindowTitle(t("wizard.title"))
        self.setMinimumWidth(440)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_lbl = QLabel(t("wizard.title"))
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setVerticalSpacing(14)
        form.setHorizontalSpacing(16)

        # Name
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("ex: macOS-Tahoe-Work")
        self.txt_name.setText("macOS-Tahoe")
        form.addRow(t("wizard.field.name"), self.txt_name)

        # macOS Version
        self.cmb_version = QComboBox()
        self.cmb_version.addItems([
            "macOS 26 Tahoe (Mais Recente)",
            "macOS 15 Sequoia",
            "macOS 14 Sonoma",
        ])
        form.addRow(t("wizard.field.release"), self.cmb_version)

        # CPU Cores
        cpu_layout = QHBoxLayout()
        self.slider_cpu = QSlider(Qt.Orientation.Horizontal)
        self.slider_cpu.setRange(2, 16)
        self.slider_cpu.setValue(6)
        self.lbl_cpu_val = QLabel("6 Cores")
        self.lbl_cpu_val.setStyleSheet("font-weight: 600; min-width: 60px;")
        self.slider_cpu.valueChanged.connect(lambda v: self.lbl_cpu_val.setText(f"{v} Cores"))
        cpu_layout.addWidget(self.slider_cpu)
        cpu_layout.addWidget(self.lbl_cpu_val)
        form.addRow(t("wizard.field.cpus"), cpu_layout)

        # RAM Memory
        ram_layout = QHBoxLayout()
        self.slider_ram = QSlider(Qt.Orientation.Horizontal)
        self.slider_ram.setRange(4, 32)
        self.slider_ram.setValue(16)
        self.lbl_ram_val = QLabel("16 GB")
        self.lbl_ram_val.setStyleSheet("font-weight: 600; min-width: 60px;")
        self.slider_ram.valueChanged.connect(lambda v: self.lbl_ram_val.setText(f"{v} GB"))
        ram_layout.addWidget(self.slider_ram)
        ram_layout.addWidget(self.lbl_ram_val)
        form.addRow(t("wizard.field.memory"), ram_layout)

        # Disk Size
        self.spin_disk = QSpinBox()
        self.spin_disk.setRange(40, 500)
        self.spin_disk.setValue(100)
        self.spin_disk.setSuffix(" GB")
        form.addRow(t("wizard.field.disk"), self.spin_disk)

        # Physical GPU
        self.cmb_gpu = QComboBox()
        if self.available_gpus:
            for gpu in self.available_gpus:
                prefix = "★ [Padrão] " if gpu.is_default else ""
                self.cmb_gpu.addItem(f"{prefix}{gpu.name}", gpu)
        else:
            self.cmb_gpu.addItem("Auto / Lavapipe")
        form.addRow(t("wizard.field.gpu"), self.cmb_gpu)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(t("wizard.btn.cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_create = QPushButton(t("wizard.btn.create"))
        self.btn_create.setObjectName("primaryBtn")
        self.btn_create.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_create)

        layout.addLayout(btn_layout)

    def get_request(self) -> NewVmRequest:
        selected_gpu = self.cmb_gpu.currentData()
        # Parse version string
        ver_text = self.cmb_version.currentText()
        if "26" in ver_text or "Tahoe" in ver_text:
            release_id = "tahoe"
        elif "15" in ver_text or "Sequoia" in ver_text:
            release_id = "sequoia"
        else:
            release_id = "sonoma"

        return NewVmRequest(
            name=self.txt_name.text().strip() or "macOS-VM",
            macos_release=release_id,
            cpus=self.slider_cpu.value(),
            memory_mib=self.slider_ram.value() * 1024,
            disk_size_gb=self.spin_disk.value(),
            gpu=selected_gpu if isinstance(selected_gpu, GpuDevice) else None,
            use_online_installer=True,
        )
