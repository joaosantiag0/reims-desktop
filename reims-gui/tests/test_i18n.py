"""Unit tests for the Translator and localization dictionaries."""

import unittest
from reims_gui.i18n.translator import Translator, t


class TestTranslator(unittest.TestCase):

    def test_translator_locales_load(self):
        tr = Translator.get_instance()
        self.assertIn("pt_BR", tr._translations)
        self.assertIn("en_US", tr._translations)
        self.assertIn("es_ES", tr._translations)

    def test_translations_keys_consistency(self):
        tr = Translator.get_instance()
        pt = tr._translations["pt_BR"]
        en = tr._translations["en_US"]
        es = tr._translations["es_ES"]

        for key in pt.keys():
            self.assertIn(key, en, f"Missing key in en_US: {key}")
            self.assertIn(key, es, f"Missing key in es_ES: {key}")

    def test_translate_function_and_switch(self):
        tr = Translator.get_instance()

        tr.set_language("pt_BR")
        self.assertEqual(t("vm.status.running"), "Executando")

        tr.set_language("en_US")
        self.assertEqual(t("vm.status.running"), "Running")

        tr.set_language("es_ES")
        self.assertEqual(t("vm.status.running"), "En ejecución")

    def test_translation_formatting(self):
        tr = Translator.get_instance()
        tr.set_language("pt_BR")
        res = t("dialog.confirm_delete", name="MinhaVM")
        self.assertIn("MinhaVM", res)


if __name__ == "__main__":
    unittest.main()
