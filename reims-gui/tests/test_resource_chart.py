"""Unit tests for the CPU/RAM usage chart widgets (resource_chart)."""
from __future__ import annotations

import unittest

from reims_gui.core.system_stats import SystemSample
from reims_gui.qt_compat import QT_BACKEND
from reims_gui.ui.widgets.resource_chart import (
    HISTORY_SIZE,
    ResourceMonitorBar,
    UsageChart,
)


def _ensure_app():
    if QT_BACKEND != "MockQt":
        from reims_gui.qt_compat import QtWidgets
        app = QtWidgets.QApplication.instance()
        if not app:
            app = QtWidgets.QApplication([])
        return app
    return None


class TestUsageChart(unittest.TestCase):

    def setUp(self):
        self.app = _ensure_app()
        self.chart = UsageChart("#3B82F6", "CPU")

    def test_initial_state(self):
        self.assertEqual(self.chart.point_count, 0)
        self.assertEqual(self.chart.last_value, 0.0)

    def test_set_value_pushes_history_and_clamps(self):
        self.chart.set_value(42.0)
        self.chart.set_value(150.0)
        self.chart.set_value(-10.0)
        self.assertEqual(self.chart.point_count, 3)
        self.assertEqual(self.chart.last_value, 0.0)

    def test_history_respects_maxlen(self):
        for i in range(HISTORY_SIZE + 20):
            self.chart.set_value(float(i % 100))
        self.assertEqual(self.chart.point_count, HISTORY_SIZE)

    def test_clear(self):
        self.chart.set_value(50.0)
        self.chart.clear()
        self.assertEqual(self.chart.point_count, 0)


class TestResourceMonitorBar(unittest.TestCase):

    def setUp(self):
        self.app = _ensure_app()
        self.bar = ResourceMonitorBar()

    def test_widgets_exist(self):
        self.assertIsNotNone(self.bar.chart_cpu)
        self.assertIsNotNone(self.bar.chart_ram)
        self.assertIsNotNone(self.bar.sampler)

    def test_update_sample_populates_charts_and_detail(self):
        sample = SystemSample(
            cpu_percent=37.0,
            ram_percent=64.0,
            ram_used_gb=10.2,
            ram_total_gb=16.0,
        )
        self.bar.update_sample(sample)
        self.assertAlmostEqual(self.bar.chart_cpu.last_value, 37.0, places=1)
        self.assertAlmostEqual(self.bar.chart_ram.last_value, 64.0, places=1)
        self.assertIn("10.2", self.bar.lbl_ram_detail.text())
        self.assertIn("16.0", self.bar.lbl_ram_detail.text())

    def test_update_sample_none_is_noop(self):
        self.bar.update_sample(None)
        self.assertEqual(self.bar.chart_cpu.point_count, 0)

    def test_refresh_samples_host(self):
        # Best-effort: em qualquer ambiente deve completar sem erro.
        self.bar.refresh()
        self.assertIsNotNone(self.bar.chart_cpu)

    def test_retranslate_updates_title(self):
        from reims_gui.i18n.translator import Translator
        tr = Translator.get_instance()
        original_lang = tr.current_language
        self.addCleanup(tr.set_language, original_lang)
        tr.set_language("pt_BR")
        self.bar.retranslate()
        self.assertIn("Uso do Host", self.bar.lbl_title.text())
        tr.set_language("en_US")
        self.bar.retranslate()
        self.assertIn("Host Usage", self.bar.lbl_title.text())


if __name__ == "__main__":
    unittest.main()
