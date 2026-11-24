"""Diálogo de Progresso e Criação de Máquina Virtual para o Reims Desktop."""
from __future__ import annotations

import logging
from typing import Optional

from reims_gui.core.ctl_client import ReimsCtlClient
from reims_gui.core.models import NewVmRequest
from reims_gui.i18n.translator import t
from reims_gui.qt_compat import QT_BACKEND, QtCore, QtWidgets, Signal

QDialog = QtWidgets.QDialog
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QPushButton = QtWidgets.QPushButton
QProgressBar = QtWidgets.QProgressBar
QTextEdit = QtWidgets.QTextEdit

logger = logging.getLogger(__name__)


class VmCreationWorker(QtCore.QThread):
    """Thread em segundo plano que executa o processo de criação da VM sem travar a interface."""

    progress_signal = Signal(int, str, str)  # (percentual, mensagem_etapa, linha_log)
    finished_signal = Signal(bool, str)       # (sucesso, mensagem_final)

    def __init__(self, client: ReimsCtlClient, req: NewVmRequest, parent=None):
        super().__init__(parent)
        self.client = client
        self.req = req

    def run(self):
        def on_progress(pct: int, msg: str, log: str):
            if hasattr(self.progress_signal, "emit"):
                self.progress_signal.emit(pct, msg, log)

        try:
            success = self.client.create_vm(self.req, progress_callback=on_progress)
            if hasattr(self.finished_signal, "emit"):
                self.finished_signal.emit(success, "OK" if success else "Falha ao criar máquina virtual")
        except Exception as e:
            logger.error("Exceção na thread de criação de VM: %s", e)
            if hasattr(self.finished_signal, "emit"):
                self.finished_signal.emit(False, str(e))


class VmCreationDialog(QDialog):
    """Diálogo modal exibindo barra de progresso, status detalhado e logs em tempo real da criação da VM."""

    def __init__(self, req: NewVmRequest, client: ReimsCtlClient, parent=None):
        super().__init__(parent)
        self.req = req
        self.client = client
        self.success = False

        self.setWindowTitle(t("wizard.creation.title", name=self.req.name))
        self.resize(560, 440)
        self.setMinimumSize(500, 400)
        self.setStyleSheet("background-color: #121418; color: #F1F5F9;")

        self._init_ui()
        self._start_worker()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        # 1. Cabeçalho
        self.lbl_title = QLabel(t("wizard.creation.title", name=self.req.name))
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38BDF8;")
        layout.addWidget(self.lbl_title)

        # Informações de especificações da VM sendo provisionada
        gpu_name = self.req.gpu.name if self.req.gpu else "Auto"
        spec_text = f"{self.req.cpus} vCPUs • {self.req.memory_mib // 1024} GB RAM • {self.req.disk_size_gb} GB Disco • GPU: {gpu_name}"
        self.lbl_specs = QLabel(spec_text)
        self.lbl_specs.setStyleSheet("font-size: 13px; color: #94A3B8; font-weight: 500;")
        layout.addWidget(self.lbl_specs)

        # 2. Status atual
        self.lbl_status = QLabel(t("wizard.creation.status_starting"))
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: 600; color: #E2E8F0; margin-top: 4px;")
        layout.addWidget(self.lbl_status)

        # 3. Barra de Progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(5)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #1E293B; border: 1px solid #334155; border-radius: 6px; height: 16px; text-align: center; color: white; font-weight: bold; font-size: 11px; } "
            "QProgressBar::chunk { background-color: #2563EB; border-radius: 5px; }"
        )
        layout.addWidget(self.progress_bar)

        # 4. Logs em Tempo Real
        self.lbl_logs = QLabel(t("wizard.creation.logs_label"))
        self.lbl_logs.setStyleSheet("font-size: 12px; font-weight: bold; color: #64748B; margin-top: 4px;")
        layout.addWidget(self.lbl_logs)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet(
            "background-color: #0B0F17; color: #38BDF8; border: 1px solid #1E293B; "
            "border-radius: 6px; padding: 10px; font-family: monospace; font-size: 12px; line-height: 1.4;"
        )
        layout.addWidget(self.txt_logs)

        # 5. Botões de Ação
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(t("wizard.creation.btn_cancel"))
        self.btn_cancel.setStyleSheet(
            "background-color: #1E293B; color: #E2E8F0; border: 1px solid #334155; "
            "border-radius: 6px; padding: 8px 16px; font-weight: 500;"
        )
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_done = QPushButton(t("wizard.creation.btn_done"))
        self.btn_done.setObjectName("primaryBtn")
        self.btn_done.setStyleSheet(
            "background-color: #10B981; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px; border: none;"
        )
        self.btn_done.setEnabled(False)
        self.btn_done.setVisible(False)
        self.btn_done.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_done)

        layout.addLayout(btn_layout)

    def _start_worker(self):
        self.worker = VmCreationWorker(client=self.client, req=self.req, parent=self)

        if QT_BACKEND != "MockQt" and hasattr(self.worker, "progress_signal") and hasattr(self.worker.progress_signal, "connect"):
            self.worker.progress_signal.connect(self._on_progress)
            self.worker.finished_signal.connect(self._on_finished)
            self.worker.start()
        else:
            # Em modo MockQt ou testes sem event loop de threads, executa síncrono
            self.worker.progress_signal = type("SignalStub", (), {"emit": self._on_progress})()
            self.worker.finished_signal = type("SignalStub", (), {"emit": self._on_finished})()
            self.worker.run()

    def _on_progress(self, percent: int, status_msg: str, log_line: str):
        if hasattr(self.progress_bar, "setValue"):
            self.progress_bar.setValue(percent)
        if hasattr(self.lbl_status, "setText"):
            self.lbl_status.setText(status_msg)
        if hasattr(self.txt_logs, "append"):
            self.txt_logs.append(log_line)

    def _on_finished(self, success: bool, message: str):
        self.success = success
        if success:
            if hasattr(self.progress_bar, "setValue"):
                self.progress_bar.setValue(100)
                self.progress_bar.setStyleSheet(
                    "QProgressBar { background-color: #1E293B; border-radius: 6px; height: 14px; text-align: center; } "
                    "QProgressBar::chunk { background-color: #10B981; border-radius: 6px; }"
                )
            if hasattr(self.lbl_status, "setText"):
                self.lbl_status.setText(t("wizard.creation.step_done"))
                self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #34D399;")
            if hasattr(self.btn_done, "setVisible"):
                self.btn_done.setVisible(True)
                self.btn_done.setEnabled(True)
            if hasattr(self.btn_cancel, "setVisible"):
                self.btn_cancel.setVisible(False)
        else:
            if hasattr(self.progress_bar, "setStyleSheet"):
                self.progress_bar.setStyleSheet(
                    "QProgressBar { background-color: #1E293B; border-radius: 6px; height: 14px; text-align: center; } "
                    "QProgressBar::chunk { background-color: #EF4444; border-radius: 6px; }"
                )
            if hasattr(self.lbl_status, "setText"):
                self.lbl_status.setText(t("wizard.creation.step_error", err=message))
                self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #F87171;")
            if hasattr(self.btn_cancel, "setText"):
                self.btn_cancel.setText(t("wizard.creation.btn_close"))
                self.btn_cancel.setEnabled(True)
