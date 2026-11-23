from __future__ import annotations
import logging
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from reims_gui.core.ctl_client import ReimsCtlClient
from reims_gui.core.models import DoctorHealth, GpuDevice, VmInfo
from reims_gui.i18n.translator import Translator, t
from reims_gui.ui.dialogs.new_vm_dialog import NewVmDialog
from reims_gui.ui.widgets.doctor_bar import DoctorBar
from reims_gui.ui.widgets.vm_card import VmCard

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main Application Window for Reims Control Center."""

    def __init__(self, client: ReimsCtlClient, parent=None):
        super().__init__(parent)
        self.client = client
        self.translator = Translator.get_instance()
        self.cards: List[VmCard] = []

        self.setWindowTitle(t("app.title"))
        self.resize(880, 620)
        self.setMinimumSize(700, 500)

        self._init_ui()
        self.translator.subscribe(self._on_language_changed)

        # Initial data load
        self.refresh_data()

        # Periodic refresh timer (every 4 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(4000)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Header
        header_frame = QFrame()
        header_frame.setObjectName("appHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(18, 12, 18, 12)

        # Brand / Logo
        brand_box = QVBoxLayout()
        brand_box.setSpacing(2)
        self.lbl_brand_title = QLabel(t("app.title"))
        self.lbl_brand_title.setObjectName("brandTitle")
        self.lbl_brand_subtitle = QLabel(t("app.subtitle"))
        self.lbl_brand_subtitle.setObjectName("brandSubtitle")
        brand_box.addWidget(self.lbl_brand_title)
        brand_box.addWidget(self.lbl_brand_subtitle)
        header_layout.addLayout(brand_box)

        header_layout.addStretch()

        # Language Selector
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItem("🇧🇷 Português (BR)", "pt_BR")
        self.cmb_lang.addItem("🇺🇸 English (US)", "en_US")
        self.cmb_lang.addItem("🇪🇸 Español", "es_ES")

        # Set active index based on current language
        curr_idx = self.cmb_lang.findData(self.translator.current_language)
        if curr_idx >= 0:
            self.cmb_lang.setCurrentIndex(curr_idx)
        self.cmb_lang.currentIndexChanged.connect(self._handle_language_selection)
        header_layout.addWidget(self.cmb_lang)

        # Refresh Button
        self.btn_refresh = QPushButton(t("header.refresh"))
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.btn_refresh)

        # New VM Button
        self.btn_new_vm = QPushButton(t("header.new_vm"))
        self.btn_new_vm.setObjectName("primaryBtn")
        self.btn_new_vm.clicked.connect(self._handle_new_vm)
        header_layout.addWidget(self.btn_new_vm)

        root_layout.addWidget(header_frame)

        # 2. Main Content Area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(16)

        # Doctor Bar
        self.doctor_bar = DoctorBar()
        content_layout.addWidget(self.doctor_bar)

        # Scroll Area for VMs
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.vm_grid = QGridLayout(self.scroll_content)
        self.vm_grid.setContentsMargins(0, 0, 0, 0)
        self.vm_grid.setSpacing(14)

        # Empty State Widget
        self.empty_widget = QFrame()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_title = QLabel(t("vm.empty.title"))
        self.lbl_empty_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #94A3B8; margin-bottom: 8px;")
        self.lbl_empty_desc = QLabel(t("vm.empty.desc"))
        self.lbl_empty_desc.setStyleSheet("color: #64748B; font-size: 13px; max-width: 480px;")
        self.lbl_empty_desc.setWordWrap(True)
        self.lbl_empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.lbl_empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.lbl_empty_desc, alignment=Qt.AlignmentFlag.AlignCenter)

        self.scroll_area.setWidget(self.scroll_content)
        content_layout.addWidget(self.scroll_area)

        root_layout.addWidget(content_widget)

    def refresh_data(self):
        # 1. Update Doctor Health
        health = self.client.run_doctor()
        self.doctor_bar.update_health(health)

        # 2. Update VMs
        vms = self.client.list_vms()
        self._render_vms(vms)

    def _render_vms(self, vms: List[VmInfo]):
        # Clear existing items in grid
        for card in self.cards:
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        self.empty_widget.setParent(None)

        if not vms:
            self.vm_grid.addWidget(self.empty_widget, 0, 0, Qt.AlignmentFlag.AlignCenter)
            return

        cols = 2
        for i, vm in enumerate(vms):
            card = VmCard(
                vm=vm,
                on_start=self._handle_start_vm,
                on_stop=self._handle_stop_vm,
                on_view=self._handle_view_vm,
                on_delete=self._handle_delete_vm,
            )
            self.cards.append(card)
            row = i // cols
            col = i % cols
            self.vm_grid.addWidget(card, row, col)

    def _handle_start_vm(self, name: str):
        success = self.client.start_vm(name)
        if success:
            self.refresh_data()

    def _handle_stop_vm(self, name: str):
        success = self.client.stop_vm(name)
        if success:
            self.refresh_data()

    def _handle_view_vm(self, name: str):
        logger.info(f"Opening view for VM: {name}")

    def _handle_delete_vm(self, name: str):
        confirm = QMessageBox.question(
            self,
            t("dialog.confirm_delete_title"),
            t("dialog.confirm_delete", name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.client.delete_vm(name)
            self.refresh_data()

    def _handle_new_vm(self):
        gpus = self.client.list_gpus()
        dlg = NewVmDialog(available_gpus=gpus, parent=self)
        if dlg.exec():
            req = dlg.get_request()
            self.client.create_vm(req)
            self.refresh_data()

    def _handle_language_selection(self, index: int):
        lang_code = self.cmb_lang.itemData(index)
        if lang_code:
            self.translator.set_language(lang_code)

    def _on_language_changed(self, lang_code: str):
        self.setWindowTitle(t("app.title"))
        self.lbl_brand_title.setText(t("app.title"))
        self.lbl_brand_subtitle.setText(t("app.subtitle"))
        self.btn_refresh.setText(t("header.refresh"))
        self.btn_new_vm.setText(t("header.new_vm"))
        self.lbl_empty_title.setText(t("vm.empty.title"))
        self.lbl_empty_desc.setText(t("vm.empty.desc"))
        self.doctor_bar.retranslate()
        for card in self.cards:
            card.retranslate()
