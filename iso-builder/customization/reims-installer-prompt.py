#!/usr/bin/env python3
"""ReimsOS Live CD & Installer Welcome Prompt.

Substitui o lubuntu-installer-prompt padrao por uma interface moderna,
com tema escuro do ReimsOS, suporte a i18n (pt_BR, en_US, es_ES) e opcoes claras
para experimentar o Live CD ou iniciar o instalador grafico Calamares.
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from typing import Any, Callable

# Multi-toolkit Qt import fallback
QT_AVAILABLE = False
try:
    from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
    from PySide6.QtCore import Qt, Signal  # type: ignore
    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
        from PyQt5.QtCore import Qt, pyqtSignal as Signal  # type: ignore
        QT_AVAILABLE = True
    except ImportError:
        try:
            from PyQt6 import QtCore, QtGui, QtWidgets  # type: ignore
            from PyQt6.QtCore import Qt, pyqtSignal as Signal  # type: ignore
            QT_AVAILABLE = True
        except ImportError:
            QT_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("reims-installer-prompt")

TRANSLATIONS: dict[str, dict[str, str]] = {
    "pt_BR": {
        "title": "ReimsOS 24.04 LTS",
        "subtitle": "Sistema Operacional Otimizado para Desempenho e Virtualização de GPU",
        "heading": "Bem-vindo ao ReimsOS! O que você deseja fazer?",
        "lang_label": "Idioma:",
        "card_live_title": "Experimentar ReimsOS (Live CD)",
        "card_live_badge": "Modo de Teste",
        "card_live_desc": (
            "Inicie a sessão gráfica do ReimsOS diretamente na memória RAM.\n"
            "Nenhuma modificação será feita nos seus discos. Você poderá testar "
            "suas GPUs, redes Wi-Fi e utilizar o Reims Control Center."
        ),
        "btn_live": "Experimentar ReimsOS (Live CD)",
        "card_install_title": "Instalar o ReimsOS",
        "card_install_badge": "Instalação no Disco",
        "card_install_desc": (
            "Abra o assistente gráfico de instalação (Calamares) para particionar seu "
            "disco rígido/NVMe, configurar seu usuário e instalar o ReimsOS "
            "com aceleração de GPU e KVM completa."
        ),
        "btn_install": "Instalar o ReimsOS",
        "status_ready": "Selecione uma opção para continuar.",
        "status_running": "Iniciando assistente de instalação Calamares...",
    },
    "en_US": {
        "title": "ReimsOS 24.04 LTS",
        "subtitle": "Performance-Optimized OS with Native GPU Virtualization",
        "heading": "Welcome to ReimsOS! What would you like to do?",
        "lang_label": "Language:",
        "card_live_title": "Try ReimsOS (Live CD)",
        "card_live_badge": "Live Test Mode",
        "card_live_desc": (
            "Launch the ReimsOS desktop session directly in RAM.\n"
            "No changes will be made to your system disks. Explore the desktop, "
            "verify GPU and network hardware, and test Reims Control Center."
        ),
        "btn_live": "Try ReimsOS (Live CD)",
        "card_install_title": "Install ReimsOS",
        "card_install_badge": "Full Installation",
        "card_install_desc": (
            "Launch the Calamares graphical installer to partition your "
            "disk/NVMe, configure your user account, and install ReimsOS "
            "with full GPU and KVM acceleration."
        ),
        "btn_install": "Install ReimsOS",
        "status_ready": "Select an option to proceed.",
        "status_running": "Starting Calamares installation wizard...",
    },
    "es_ES": {
        "title": "ReimsOS 24.04 LTS",
        "subtitle": "Sistema Operativo Optimizado para Rendimiento y Virtualización de GPU",
        "heading": "¡Bienvenido a ReimsOS! ¿Qué desea hacer?",
        "lang_label": "Idioma:",
        "card_live_title": "Probar ReimsOS (Live CD)",
        "card_live_badge": "Modo de Prueba",
        "card_live_desc": (
            "Inicie la sesión de escritorio de ReimsOS directamente en la memoria RAM.\n"
            "No se realizará ningún cambio en sus discos. Explore el sistema, "
            "compruebe sus GPUs y pruebe el Reims Control Center."
        ),
        "btn_live": "Probar ReimsOS (Live CD)",
        "card_install_title": "Instalar ReimsOS",
        "card_install_badge": "Instalación en Disco",
        "card_install_desc": (
            "Abra el asistente gráfico de instalación (Calamares) para particionar su "
            "disco/NVMe, configurar su cuenta de usuario e instalar ReimsOS "
            "con aceleración completa de GPU y KVM."
        ),
        "btn_install": "Instalar ReimsOS",
        "status_ready": "Seleccione una opción para continuar.",
        "status_running": "Iniciando instalador Calamares...",
    },
}

DARK_STYLESHEET = """
QMainWindow, QWidget#centralWidget {
    background-color: #121418;
    color: #F1F5F9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

#headerBox {
    background-color: #1A1D24;
    border-bottom: 1px solid #2B303B;
    padding: 16px 24px;
}

#titleLabel {
    font-size: 20px;
    font-weight: 700;
    color: #FFFFFF;
}

#subtitleLabel {
    font-size: 12px;
    color: #94A3B8;
}

#headingLabel {
    font-size: 14px;
    font-weight: 600;
    color: #CBD5E1;
    margin-top: 10px;
    margin-bottom: 4px;
}

#langLabel {
    font-size: 12px;
    color: #94A3B8;
}

QComboBox {
    background-color: #222631;
    color: #F1F5F9;
    border: 1px solid #3B4252;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #222631;
    color: #F1F5F9;
    selection-background-color: #2563EB;
}

QFrame.cardFrame {
    background-color: #1A1D24;
    border: 1px solid #2B303B;
    border-radius: 12px;
    padding: 20px;
}

QFrame.cardFrame:hover {
    border: 1px solid #3B82F6;
}

QLabel.cardTitle {
    font-size: 16px;
    font-weight: 700;
    color: #FFFFFF;
}

QLabel.cardBadge {
    font-size: 11px;
    font-weight: 600;
    color: #38BDF8;
    background-color: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 4px;
    padding: 2px 6px;
}

QLabel.cardDesc {
    font-size: 12px;
    color: #94A3B8;
    line-height: 18px;
}

QPushButton.btnPrimary {
    background-color: #2563EB;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 12px 18px;
}

QPushButton.btnPrimary:hover {
    background-color: #3B82F6;
}

QPushButton.btnPrimary:pressed {
    background-color: #1D4ED8;
}

QPushButton.btnSecondary {
    background-color: #374151;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 12px 18px;
}

QPushButton.btnSecondary:hover {
    background-color: #4B5563;
}

QPushButton.btnSecondary:pressed {
    background-color: #1F2937;
}

#statusLabel {
    font-size: 11px;
    color: #64748B;
}
"""

def detect_locale() -> str:
    lang = os.environ.get("LANG", "") or os.environ.get("LC_ALL", "")
    if "pt" in lang.lower():
        return "pt_BR"
    elif "es" in lang.lower():
        return "es_ES"
    return "en_US"


if QT_AVAILABLE:
    class ReimsInstallerPromptWindow(QtWidgets.QMainWindow):
        """Janela principal do assistente de boas-vindas do ReimsOS."""

        def __init__(
            self,
            mock: bool = False,
            on_live_action: Callable[[], None] | None = None,
            on_install_action: Callable[[], None] | None = None,
        ) -> None:
            super().__init__()
            self.mock = mock
            self.on_live_action = on_live_action
            self.on_install_action = on_install_action
            self.current_locale = detect_locale()

            self.setWindowTitle("ReimsOS 24.04 LTS")
            self.setMinimumSize(820, 520)
            self.resize(860, 540)
            self.setStyleSheet(DARK_STYLESHEET)

            self._setup_ui()
            self._update_texts()

        def _setup_ui(self) -> None:
            central = QtWidgets.QWidget(self)
            central.setObjectName("centralWidget")
            self.setCentralWidget(central)

            main_layout = QtWidgets.QVBoxLayout(central)
            main_layout.setContentsMargins(0, 0, 0, 16)
            main_layout.setSpacing(16)

            # Header
            header = QtWidgets.QWidget()
            header.setObjectName("headerBox")
            header_layout = QtWidgets.QHBoxLayout(header)
            header_layout.setContentsMargins(16, 12, 16, 12)

            # Logo & Titles
            title_vbox = QtWidgets.QVBoxLayout()
            self.lbl_title = QtWidgets.QLabel("ReimsOS 24.04 LTS")
            self.lbl_title.setObjectName("titleLabel")
            self.lbl_subtitle = QtWidgets.QLabel()
            self.lbl_subtitle.setObjectName("subtitleLabel")
            title_vbox.addWidget(self.lbl_title)
            title_vbox.addWidget(self.lbl_subtitle)
            header_layout.addLayout(title_vbox, stretch=1)

            # Language selector
            lang_hbox = QtWidgets.QHBoxLayout()
            self.lbl_lang = QtWidgets.QLabel("Idioma:")
            self.lbl_lang.setObjectName("langLabel")
            self.cb_lang = QtWidgets.QComboBox()
            self.cb_lang.addItem("Português (Brasil)", "pt_BR")
            self.cb_lang.addItem("English (US)", "en_US")
            self.cb_lang.addItem("Español", "es_ES")

            idx = self.cb_lang.findData(self.current_locale)
            if idx >= 0:
                self.cb_lang.setCurrentIndex(idx)
            self.cb_lang.currentIndexChanged.connect(self._on_lang_changed)

            lang_hbox.addWidget(self.lbl_lang)
            lang_hbox.addWidget(self.cb_lang)
            header_layout.addLayout(lang_hbox)
            main_layout.addWidget(header)

            # Heading
            body_layout = QtWidgets.QVBoxLayout()
            body_layout.setContentsMargins(28, 0, 28, 0)
            body_layout.setSpacing(16)

            self.lbl_heading = QtWidgets.QLabel()
            self.lbl_heading.setObjectName("headingLabel")
            body_layout.addWidget(self.lbl_heading)

            # Cards Layout (Horizontal)
            cards_layout = QtWidgets.QHBoxLayout()
            cards_layout.setSpacing(20)

            # Card 1: Live CD
            self.card_live = QtWidgets.QFrame()
            self.card_live.setProperty("class", "cardFrame")
            card_live_vbox = QtWidgets.QVBoxLayout(self.card_live)
            card_live_vbox.setSpacing(12)

            live_title_hbox = QtWidgets.QHBoxLayout()
            self.lbl_card_live_title = QtWidgets.QLabel()
            self.lbl_card_live_title.setProperty("class", "cardTitle")
            self.lbl_card_live_badge = QtWidgets.QLabel()
            self.lbl_card_live_badge.setProperty("class", "cardBadge")
            live_title_hbox.addWidget(self.lbl_card_live_title)
            live_title_hbox.addStretch(1)
            live_title_hbox.addWidget(self.lbl_card_live_badge)
            card_live_vbox.addLayout(live_title_hbox)

            self.lbl_card_live_desc = QtWidgets.QLabel()
            self.lbl_card_live_desc.setProperty("class", "cardDesc")
            self.lbl_card_live_desc.setWordWrap(True)
            card_live_vbox.addWidget(self.lbl_card_live_desc, stretch=1)

            self.btn_live = QtWidgets.QPushButton()
            self.btn_live.setProperty("class", "btnSecondary")
            self.btn_live.setCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, 'CursorShape') else Qt.PointingHandCursor)
            self.btn_live.clicked.connect(self.handle_live_clicked)
            card_live_vbox.addWidget(self.btn_live)

            cards_layout.addWidget(self.card_live, stretch=1)

            # Card 2: Install
            self.card_install = QtWidgets.QFrame()
            self.card_install.setProperty("class", "cardFrame")
            card_install_vbox = QtWidgets.QVBoxLayout(self.card_install)
            card_install_vbox.setSpacing(12)

            inst_title_hbox = QtWidgets.QHBoxLayout()
            self.lbl_card_inst_title = QtWidgets.QLabel()
            self.lbl_card_inst_title.setProperty("class", "cardTitle")
            self.lbl_card_inst_badge = QtWidgets.QLabel()
            self.lbl_card_inst_badge.setProperty("class", "cardBadge")
            inst_title_hbox.addWidget(self.lbl_card_inst_title)
            inst_title_hbox.addStretch(1)
            inst_title_hbox.addWidget(self.lbl_card_inst_badge)
            card_install_vbox.addLayout(inst_title_hbox)

            self.lbl_card_inst_desc = QtWidgets.QLabel()
            self.lbl_card_inst_desc.setProperty("class", "cardDesc")
            self.lbl_card_inst_desc.setWordWrap(True)
            card_install_vbox.addWidget(self.lbl_card_inst_desc, stretch=1)

            self.btn_install = QtWidgets.QPushButton()
            self.btn_install.setProperty("class", "btnPrimary")
            self.btn_install.setCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, 'CursorShape') else Qt.PointingHandCursor)
            self.btn_install.clicked.connect(self.handle_install_clicked)
            card_install_vbox.addWidget(self.btn_install)

            cards_layout.addWidget(self.card_install, stretch=1)
            body_layout.addLayout(cards_layout, stretch=1)

            # Status footer
            self.lbl_status = QtWidgets.QLabel()
            self.lbl_status.setObjectName("statusLabel")
            body_layout.addWidget(self.lbl_status)

            main_layout.addLayout(body_layout, stretch=1)

        def _on_lang_changed(self) -> None:
            data = self.cb_lang.currentData()
            if data and data in TRANSLATIONS:
                self.current_locale = str(data)
                self._update_texts()

        def _update_texts(self) -> None:
            t = TRANSLATIONS.get(self.current_locale, TRANSLATIONS["en_US"])
            self.lbl_title.setText(t["title"])
            self.lbl_subtitle.setText(t["subtitle"])
            self.lbl_heading.setText(t["heading"])
            self.lbl_lang.setText(t["lang_label"])

            self.lbl_card_live_title.setText(t["card_live_title"])
            self.lbl_card_live_badge.setText(t["card_live_badge"])
            self.lbl_card_live_desc.setText(t["card_live_desc"])
            self.btn_live.setText(t["btn_live"])

            self.lbl_card_inst_title.setText(t["card_install_title"])
            self.lbl_card_inst_badge.setText(t["card_install_badge"])
            self.lbl_card_inst_desc.setText(t["card_install_desc"])
            self.btn_install.setText(t["btn_install"])

            self.lbl_status.setText(t["status_ready"])

        def handle_live_clicked(self) -> None:
            """Trata o clique em 'Experimentar ReimsOS'."""
            logger.info("Usuario selecionou: Experimentar ReimsOS (Live CD)")
            if self.on_live_action:
                self.on_live_action()
            else:
                self.close()
                sys.exit(0)

        def handle_install_clicked(self) -> None:
            """Trata o clique em 'Instalar o ReimsOS'."""
            logger.info("Usuario selecionou: Instalar o ReimsOS")
            t = TRANSLATIONS.get(self.current_locale, TRANSLATIONS["en_US"])
            self.lbl_status.setText(t["status_running"])
            self.btn_live.setEnabled(False)
            self.btn_install.setEnabled(False)

            if self.on_install_action:
                self.on_install_action()
                return

            if self.mock:
                logger.info("[MOCK] Simulando execucao do Calamares.")
                self.close()
                sys.exit(0)

            # Executa Calamares e aguarda termino
            try:
                cmd = (
                    ["sudo", "-E", "/usr/bin/calamares-launch-normal"]
                    if os.path.exists("/usr/bin/calamares-launch-normal")
                    else ["sudo", "-E", "calamares", "-d"]
                )
                subprocess.run(cmd, check=False)
            except Exception as e:
                logger.error("Falha ao executar calamares: %s", e)
            finally:
                self.close()
                sys.exit(0)


def main() -> int:
    parser = argparse.ArgumentParser(description="ReimsOS Live Welcome Prompt")
    parser.add_argument("--mock", action="store_true", help="Executa em modo simulacao")
    parser.add_argument("--test-init", action="store_true", help="Apenas inicializa UI e fecha com 0")
    args = parser.parse_args()

    if not QT_AVAILABLE:
        logger.warning("Nenhum backend Qt (PySide6/PyQt5/PyQt6) disponivel.")
        print("ReimsOS Live Welcome: Qt nao disponivel. Prosseguindo para Live Desktop...")
        return 0

    app = QtWidgets.QApplication(sys.argv)
    window = ReimsInstallerPromptWindow(mock=args.mock)

    if args.test_init:
        logger.info("Teste de inicializacao concluido com sucesso.")
        return 0

    window.show()
    return app.exec() if hasattr(app, "exec") else app.exec_()


if __name__ == "__main__":
    sys.exit(main())
