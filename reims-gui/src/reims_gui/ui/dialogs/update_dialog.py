"""Diálogo de Atualização do ReimsOS para a interface gráfica."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from reims_gui.qt_compat import Qt, QtCore, QtWidgets
QDialog = QtWidgets.QDialog
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QPushButton = QtWidgets.QPushButton
QProgressBar = QtWidgets.QProgressBar
QTextEdit = QtWidgets.QTextEdit
QCheckBox = QtWidgets.QCheckBox

from reims_gui.core.updater import ReleaseInfo, SystemUpdater
from reims_gui.i18n.translator import t

logger = logging.getLogger(__name__)


class UpdateDialog(QDialog):
    """Diálogo que exibe notas da versão e realiza download e instalação da atualização."""

    def __init__(
        self,
        release: ReleaseInfo,
        updater: SystemUpdater,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.release = release
        self.updater = updater
        self.setWindowTitle(t("update.dialog.title"))
        self.resize(520, 420)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Cabeçalho de Versão
        self.lbl_title = QLabel(t("update.dialog.title"))
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(self.lbl_title)

        info_text = t(
            "update.dialog.version_info",
            current=self.updater.current_version,
            latest=self.release.tag_name,
        )
        self.lbl_info = QLabel(info_text)
        self.lbl_info.setStyleSheet("font-size: 14px; color: #E2E8F0;")
        layout.addWidget(self.lbl_info)

        # 2. Notas da Versão (Changelog)
        self.lbl_notes_title = QLabel(t("update.dialog.release_notes"))
        self.lbl_notes_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #94A3B8;")
        layout.addWidget(self.lbl_notes_title)

        self.txt_notes = QTextEdit()
        self.txt_notes.setReadOnly(True)
        self.txt_notes.setPlainText(self.release.body or "Nenhuma nota de versão informada.")
        self.txt_notes.setStyleSheet(
            "background-color: #0F172A; color: #CBD5E1; border: 1px solid #334155; border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(self.txt_notes)

        # 3. Opções Adicionais
        self.chk_system_update = QCheckBox(t("update.dialog.chk_system_update"))
        self.chk_system_update.setStyleSheet("color: #94A3B8; font-size: 13px;")
        if hasattr(self.chk_system_update, "setChecked"):
            self.chk_system_update.setChecked(False)
        layout.addWidget(self.chk_system_update)

        # 4. Status e Barra de Progresso
        self.lbl_status = QLabel(t("update.dialog.status_ready"))
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 13px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #1E293B; border-radius: 4px; height: 12px; text-align: center; } "
            "QProgressBar::chunk { background-color: #2563EB; border-radius: 4px; }"
        )
        layout.addWidget(self.progress_bar)

        # 4. Botões de Ação
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(t("update.dialog.btn_cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_update = QPushButton(t("update.dialog.btn_update_now"))
        self.btn_update.setObjectName("primaryBtn")
        self.btn_update.setStyleSheet(
            "background-color: #2563EB; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;"
        )
        self.btn_update.clicked.connect(self._handle_update)
        btn_layout.addWidget(self.btn_update)

        layout.addLayout(btn_layout)

    def _handle_update(self) -> None:
        """Inicia o processo de download e aplicação da atualização."""
        self.btn_update.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText(t("update.dialog.status_downloading"))
        self.progress_bar.setValue(10)

        dest_dir = Path("/tmp/reims-update")

        def on_progress(downloaded: int, total: int, filename: str):
            if total > 0:
                pct = int(10 + (downloaded / total * 60))
                self.progress_bar.setValue(min(pct, 70))

        try:
            debs = self.updater.download_assets(
                self.release,
                dest_dir,
                progress_callback=on_progress,
            )
            self.lbl_status.setText(t("update.dialog.status_installing"))
            self.progress_bar.setValue(80)

            ok, msg = self.updater.install_debs(debs)
            if ok:
                is_chk = getattr(self.chk_system_update, "isChecked", lambda: False)
                if callable(is_chk) and is_chk():
                    self.lbl_status.setText(t("update.dialog.status_updating_system"))
                    self.progress_bar.setValue(90)
                    ok_sys, msg_sys = self.updater.update_system()
                    if not ok_sys:
                        logger.warning("Falha ao atualizar base do sistema: %s", msg_sys)

                self.progress_bar.setValue(100)
                self.lbl_status.setText(t("update.dialog.status_success"))
                self.lbl_status.setStyleSheet("color: #4ADE80; font-weight: bold;")
                self.btn_cancel.setText(t("update.dialog.btn_done"))
                self.btn_cancel.setEnabled(True)
                self.btn_update.setVisible(False)
            else:
                self.progress_bar.setValue(0)
                self.lbl_status.setText(t("update.dialog.status_error", err=msg))
                self.lbl_status.setStyleSheet("color: #F87171; font-weight: bold;")
                self.btn_update.setEnabled(True)
                self.btn_cancel.setEnabled(True)

        except Exception as e:
            logger.error("Erro ao aplicar atualização: %s", e)
            self.lbl_status.setText(t("update.dialog.status_error", err=str(e)))
            self.lbl_status.setStyleSheet("color: #F87171; font-weight: bold;")
            self.btn_update.setEnabled(True)
            self.btn_cancel.setEnabled(True)
