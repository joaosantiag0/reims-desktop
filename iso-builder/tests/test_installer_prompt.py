"""Testes unitários para o Reims Desktop Live Installer Prompt."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch, MagicMock

# Define platform offscreen antes de qualquer import Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import sys
from pathlib import Path

# Adiciona o diretorio de customizacao ao path
CUSTOM_DIR = Path(__file__).resolve().parent.parent / "customization"
sys.path.insert(0, str(CUSTOM_DIR))

import importlib
prompt_module = importlib.import_module("reims-installer-prompt")


class TestReimsInstallerPrompt(unittest.TestCase):
    """Bateria de testes para o prompt de boas-vindas do Reims Desktop."""

    def test_translations_completeness(self) -> None:
        """Verifica se todas as chaves essenciais estao presentes em todos os idiomas."""
        required_keys = [
            "title",
            "subtitle",
            "heading",
            "lang_label",
            "card_live_title",
            "card_live_badge",
            "card_live_desc",
            "btn_live",
            "card_install_title",
            "card_install_badge",
            "card_install_desc",
            "btn_install",
            "status_ready",
            "status_running",
        ]
        for lang in ["pt_BR", "en_US", "es_ES"]:
            self.assertIn(lang, prompt_module.TRANSLATIONS)
            t = prompt_module.TRANSLATIONS[lang]
            for key in required_keys:
                self.assertIn(key, t, f"Chave {key} ausente em {lang}")
                self.assertTrue(len(t[key]) > 0, f"Chave {key} vazia em {lang}")

    def test_detect_locale(self) -> None:
        """Testa deteccao automatica do idioma com base em variaveis de ambiente."""
        with patch.dict(os.environ, {"LANG": "pt_BR.UTF-8"}):
            self.assertEqual(prompt_module.detect_locale(), "pt_BR")

        with patch.dict(os.environ, {"LANG": "es_ES.UTF-8"}):
            self.assertEqual(prompt_module.detect_locale(), "es_ES")

        with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}):
            self.assertEqual(prompt_module.detect_locale(), "en_US")

        with patch.dict(os.environ, {"LANG": "C"}):
            self.assertEqual(prompt_module.detect_locale(), "en_US")

    def test_window_ui_and_actions(self) -> None:
        """Testa ciclo de vida da janela do prompt Qt se disponivel."""
        if not prompt_module.QT_AVAILABLE:
            self.skipTest("Qt nao instalado no ambiente de teste")

        app = prompt_module.QtWidgets.QApplication.instance()
        if not app:
            app = prompt_module.QtWidgets.QApplication([])

        live_called = False
        install_called = False

        def on_live() -> None:
            nonlocal live_called
            live_called = True

        def on_install() -> None:
            nonlocal install_called
            install_called = True

        window = prompt_module.ReimsInstallerPromptWindow(
            mock=True,
            on_live_action=on_live,
            on_install_action=on_install,
        )

        # Verifica textos iniciais
        self.assertEqual(window.lbl_title.text(), "Reims Desktop 24.04 LTS")
        self.assertIn("Reims Desktop", window.btn_live.text())
        self.assertIn("Reims Desktop", window.btn_install.text())

        # Testa troca de idioma para en_US
        idx = window.cb_lang.findData("en_US")
        window.cb_lang.setCurrentIndex(idx)
        self.assertEqual(window.current_locale, "en_US")
        self.assertEqual(window.btn_live.text(), "Try Reims Desktop (Live CD)")

        # Testa troca de idioma para pt_BR
        idx_pt = window.cb_lang.findData("pt_BR")
        window.cb_lang.setCurrentIndex(idx_pt)
        self.assertEqual(window.current_locale, "pt_BR")
        self.assertEqual(window.btn_live.text(), "Experimentar Reims Desktop (Live CD)")

        # Testa acao do botao Live CD
        window.handle_live_clicked()
        self.assertTrue(live_called)

        # Testa acao do botao Instalar
        window.handle_install_clicked()
        self.assertTrue(install_called)

        window.close()


if __name__ == "__main__":
    unittest.main()
