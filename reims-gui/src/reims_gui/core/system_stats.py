"""Portable host CPU/RAM usage sampler for the Reims Control Center.

Lê o uso de CPU e RAM do host de forma portátil e sem dependências novas:
- Linux (alvo do ReimsOS): /proc/stat e /proc/meminfo (stdlib puro);
- macOS (ambiente de desenvolvimento): vm_stat/sysctl/top como melhor esforço;
- psutil é usado automaticamente quando instalado.

Todas as leituras são best-effort: em caso de falha `sample()` retorna None e a
GUI simplesmente mantém o último gráfico válido.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SystemSample:
    """One CPU/RAM reading of the host, percentages in the 0-100 range."""

    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def parse_proc_stat(text: str) -> Tuple[int, int]:
    """Parse /proc/stat aggregate "cpu" line -> (total_delta_units, idle_units).

    Returns cumulative counters (not a delta); the sampler subtracts the
    previous reading to compute the busy fraction between two samples.
    """
    for line in text.splitlines():
        if line.startswith("cpu "):
            fields = [int(f) for f in line.split()[1:] if f.isdigit()]
            if not fields:
                break
            # user nice system idle iowait irq softirq steal ...
            idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
            total = sum(fields)
            return total, idle
    raise ValueError("no aggregate 'cpu' line in /proc/stat")


def parse_proc_meminfo(text: str) -> Tuple[int, int]:
    """Parse /proc/meminfo -> (total_kib, available_kib)."""
    total_kib = available_kib = None
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            total_kib = int(line.split()[1])
        elif line.startswith("MemAvailable:"):
            available_kib = int(line.split()[1])
    if total_kib is None or available_kib is None:
        raise ValueError("MemTotal/MemAvailable missing in /proc/meminfo")
    return total_kib, available_kib


def parse_vm_stat(text: str) -> Tuple[float, float]:
    """Parse macOS `vm_stat` output -> (used_gb, total_gb), best-effort."""
    page_size = 4096.0
    m = re.search(r"page size of (\d+) bytes", text)
    if m:
        page_size = float(m.group(1))

    def pages(key: str) -> float:
        m = re.search(rf"^{re.escape(key)}:\s+(\d+)", text, re.MULTILINE)
        return float(m.group(1)) if m else 0.0

    total_b = 0.0
    try:
        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        total_b = float(out.stdout.strip())
    except Exception as e:
        logger.debug(f"sysctl hw.memsize failed: {e}")

    if total_b <= 0:
        # Sem sysctl (ex.: CI Linux, mocks): estima o total somando as classes
        # principais de páginas do próprio vm_stat — suficiente para testes e
        # ambientes onde o sysctl BSD não existe.
        total_b = (
            pages("Pages free")
            + pages("Pages active")
            + pages("Pages inactive")
            + pages("Pages speculative")
            + pages("Pages wired down")
            + pages("Pages compressed")
            + pages("Pages purgeable")
            + pages("Pages occupied by compressor")
        ) * page_size

    if total_b <= 0:
        raise ValueError("could not determine total RAM via sysctl")

    # Available ~= free + inactive + speculative (what macOS can hand out fast).
    available_b = (pages("Pages free") + pages("Pages inactive") + pages("Pages speculative")) * page_size
    used_b = max(0.0, total_b - available_b)
    return used_b / (1024 ** 3), total_b / (1024 ** 3)


def parse_top_cpu(text: str) -> float:
    """Parse macOS `top -l 1 -n 0` "CPU usage" line -> busy percent."""
    m = re.search(r"CPU usage:\s*([\d.]+)%\s*user,\s*([\d.]+)%\s*sys,\s*([\d.]+)%\s*idle", text)
    if not m:
        raise ValueError("no 'CPU usage' line in top output")
    user, sys_, idle = (float(m.group(i)) for i in (1, 2, 3))
    return _clamp(user + sys_)


class SystemStatsSampler:
    """Reads host CPU/RAM usage. Call `sample()` periodically (e.g. every 4 s)."""

    def __init__(self) -> None:
        self._prev_cpu: Optional[Tuple[int, int]] = None
        self._sample_psutil: Optional[SystemSample] = None

    def sample(self) -> Optional[SystemSample]:
        try:
            if self._try_psutil():
                return self._sample_psutil
            if os.path.exists("/proc/stat") and os.path.exists("/proc/meminfo"):
                return self._sample_proc()
            if os.uname().sysname == "Darwin":
                return self._sample_macos()
        except Exception as e:
            logger.debug(f"system stats sample failed: {e}")
        return None

    # --- psutil (opcional) -------------------------------------------------
    def _try_psutil(self) -> bool:
        try:
            import psutil  # type: ignore
        except ImportError:
            return False
        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        if cpu <= 0 and self._prev_cpu is None:
            # Primeira chamada do psutil sempre devolve 0.0; use 1 s bloqueante
            # apenas uma vez para sembrar a medição.
            cpu = psutil.cpu_percent(interval=0.5)
        self._sample_psutil = SystemSample(
            cpu_percent=_clamp(float(cpu)),
            ram_percent=_clamp(float(vm.percent)),
            ram_used_gb=float(vm.used) / (1024 ** 3),
            ram_total_gb=float(vm.total) / (1024 ** 3),
        )
        return True

    # --- Linux /proc --------------------------------------------------------
    def _sample_proc(self) -> SystemSample:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            total, idle = parse_proc_stat(f.read())
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            total_kib, available_kib = parse_proc_meminfo(f.read())

        cpu_percent = 0.0
        if self._prev_cpu is not None:
            d_total = total - self._prev_cpu[0]
            d_idle = idle - self._prev_cpu[1]
            if d_total > 0:
                cpu_percent = _clamp(100.0 * (1.0 - d_idle / d_total))
        self._prev_cpu = (total, idle)

        total_gb = total_kib / (1024 ** 2)
        used_gb = (total_kib - available_kib) / (1024 ** 2)
        return SystemSample(
            cpu_percent=cpu_percent,
            ram_percent=_clamp(100.0 * used_gb / total_gb) if total_gb > 0 else 0.0,
            ram_used_gb=used_gb,
            ram_total_gb=total_gb,
        )

    # --- macOS (ambiente de dev) --------------------------------------------
    def _sample_macos(self) -> SystemSample:
        used_gb, total_gb = parse_vm_stat(
            subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5, check=True
            ).stdout
        )
        cpu_percent = 0.0
        try:
            top_out = subprocess.run(
                ["top", "-l", "1", "-n", "0"],
                capture_output=True,
                text=True,
                timeout=8,
                check=True,
            ).stdout
            cpu_percent = parse_top_cpu(top_out)
        except Exception as e:
            logger.debug(f"macOS top CPU read failed: {e}")
        if total_gb <= 0:
            raise ValueError("macOS RAM total unavailable")
        return SystemSample(
            cpu_percent=cpu_percent,
            ram_percent=_clamp(100.0 * used_gb / total_gb),
            ram_used_gb=used_gb,
            ram_total_gb=total_gb,
        )
