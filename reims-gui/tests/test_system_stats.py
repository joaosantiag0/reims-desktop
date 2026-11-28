"""Unit tests for the host CPU/RAM stats sampler (system_stats)."""
from __future__ import annotations

import unittest
from unittest import mock

from reims_gui.core.system_stats import (
    SystemStatsSampler,
    parse_proc_meminfo,
    parse_proc_stat,
    parse_top_cpu,
    parse_vm_stat,
)

PROC_STAT_SAMPLE = """\
cpu  12345 0 6789 90000 1000 0 100 0 0 0
cpu0 6000 0 3000 45000 500 0 50 0 0 0
intr 123456
"""

PROC_MEMINFO_SAMPLE = """\
MemTotal:       16384000 kB
MemFree:         2000000 kB
MemAvailable:    8192000 kB
Buffers:          300000 kB
Cached:          4000000 kB
"""

VM_STAT_SAMPLE = """\
Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                              12345.
Pages active:                            98765.
Pages inactive:                           4321.
Pages speculative:                         111.
Pages wired down:                        22222.
"""

TOP_SAMPLE = "CPU usage: 12.34% user, 8.76% sys, 78.90% idle\n"


class TestProcParsers(unittest.TestCase):

    def test_parse_proc_stat_counters(self):
        total, idle = parse_proc_stat(PROC_STAT_SAMPLE)
        # user+nice+sys+idle+iowait+irq+softirq+steal
        self.assertEqual(total, 12345 + 0 + 6789 + 90000 + 1000 + 0 + 100 + 0)
        # idle + iowait
        self.assertEqual(idle, 90000 + 1000)

    def test_parse_proc_stat_missing_line_raises(self):
        with self.assertRaises(ValueError):
            parse_proc_stat("intr 1\n")

    def test_parse_proc_meminfo(self):
        total, available = parse_proc_meminfo(PROC_MEMINFO_SAMPLE)
        self.assertEqual(total, 16384000)
        self.assertEqual(available, 8192000)

    def test_parse_proc_meminfo_missing_raises(self):
        with self.assertRaises(ValueError):
            parse_proc_meminfo("MemFree: 1 kB\n")


class TestMacosParsers(unittest.TestCase):

    def test_parse_vm_stat(self):
        used, total = parse_vm_stat(VM_STAT_SAMPLE)
        self.assertGreater(total, 0.0)
        self.assertGreaterEqual(used, 0.0)
        self.assertLess(used, total)

    def test_parse_vm_stat_falls_back_to_page_sum_without_sysctl(self):
        """Sem sysctl (CI Linux/mock), o total vem da soma das páginas do sample."""
        with mock.patch(
            "reims_gui.core.system_stats.subprocess.run",
            side_effect=FileNotFoundError("no sysctl here"),
        ):
            used, total = parse_vm_stat(VM_STAT_SAMPLE)
        # Soma das classes: (12345+98765+4321+111+22222) * 16384 bytes
        expected_total_gb = (12345 + 98765 + 4321 + 111 + 22222) * 16384 / (1024 ** 3)
        self.assertAlmostEqual(total, expected_total_gb, places=6)
        self.assertGreater(total, 0.0)
        self.assertGreaterEqual(used, 0.0)
        self.assertLess(used, total)

    def test_parse_top_cpu(self):
        self.assertAlmostEqual(parse_top_cpu(TOP_SAMPLE), 12.34 + 8.76, places=2)

    def test_parse_top_cpu_out_of_range_clamped(self):
        self.assertEqual(parse_top_cpu("CPU usage: 80.0% user, 30.0% sys, 78.9% idle"), 100.0)
        self.assertEqual(parse_top_cpu("CPU usage: 0.0% user, 0.0% sys, 100.0% idle"), 0.0)


class TestSampler(unittest.TestCase):

    def test_sample_proc_two_points_yields_cpu_delta(self):
        sampler = SystemStatsSampler()
        with mock.patch.object(SystemStatsSampler, "_try_psutil", return_value=False), \
             mock.patch("os.path.exists", return_value=True), \
             mock.patch.object(
                SystemStatsSampler, "_sample_proc",
                side_effect=[
                    _fake_proc(0.0),
                    _fake_proc(75.0),
                ],
            ):
            first = sampler.sample()
            self.assertIsNotNone(first)
            self.assertGreaterEqual(first.ram_percent, 0.0)
            self.assertLessEqual(first.ram_percent, 100.0)
            second = sampler.sample()
            self.assertAlmostEqual(second.cpu_percent, 75.0, places=1)

    def test_sample_proc_real_delta_logic(self):
        """Duas leituras /proc com contadores avançando -> CPU% = 1 - idle/total."""
        sampler = SystemStatsSampler()
        # 2ª leitura: system +3500 ticks, idle +4500 => d_total=8000, d_idle=4500
        stat_data = [PROC_STAT_SAMPLE, PROC_STAT_SAMPLE.replace("6789", "10289").replace("90000", "94500")]
        meminfo_data = [PROC_MEMINFO_SAMPLE, PROC_MEMINFO_SAMPLE.replace("8192000", "4000000")]
        calls = {"n": 0}

        def fake_open(path, *args, **kwargs):
            name = str(path)
            if "stat" in name:
                data = stat_data[min(calls["n"], len(stat_data) - 1)]
            else:
                data = meminfo_data[min(calls["n"], len(meminfo_data) - 1)]
            calls["n"] += 1
            return mock.mock_open(read_data=data)()

        with mock.patch.object(SystemStatsSampler, "_try_psutil", return_value=False), \
             mock.patch("os.path.exists", return_value=True), \
             mock.patch("builtins.open", side_effect=fake_open):
            first = sampler.sample()
            second = sampler.sample()

        self.assertAlmostEqual(first.cpu_percent, 0.0, places=1)  # primeira amostra semeia
        self.assertAlmostEqual(second.cpu_percent, 100.0 * (1 - 4500 / 8000), places=1)
        self.assertAlmostEqual(second.ram_percent, 100.0 * (16384 - 4000) / 16384, places=1)

    def test_sample_returns_none_when_all_sources_fail(self):
        sampler = SystemStatsSampler()
        with mock.patch.object(SystemStatsSampler, "_try_psutil", return_value=False), \
             mock.patch("os.path.exists", return_value=False), \
             mock.patch("os.uname") as mock_uname:
            mock_uname.return_value.sysname = "UnknownOS"
            self.assertIsNone(sampler.sample())


def _fake_proc(cpu_percent: float):
    from reims_gui.core.system_stats import SystemSample
    return SystemSample(
        cpu_percent=cpu_percent,
        ram_percent=50.0,
        ram_used_gb=8.0,
        ram_total_gb=16.0,
    )


if __name__ == "__main__":
    unittest.main()
