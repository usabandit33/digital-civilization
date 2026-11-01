#!/usr/bin/env python3
"""Read-only local CPU, memory, disk, and uptime snapshot for agent runtimes."""

from __future__ import annotations

import json
import os
import platform
import shutil
import time
from typing import Any

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None


def _linux_memory() -> dict[str, float] | None:
    """Read memory counters from /proc/meminfo without external dependencies."""
    try:
        values: dict[str, float] = {}
        with open("/proc/meminfo", encoding="ascii") as stream:
            for line in stream:
                key, raw = line.split(":", 1)
                parts = raw.split()
                if parts:
                    values[key] = float(parts[0])  # Linux reports kB.
        total = values["MemTotal"] / 1024
        available = values.get("MemAvailable", values.get("MemFree", 0)) / 1024
        if total <= 0:
            return None
        return {
            "total_mb": round(total, 2),
            "available_mb": round(available, 2),
            "percent_used": round(max(0.0, min(100.0, 100 * (total - available) / total)), 2),
        }
    except (OSError, KeyError, ValueError):
        return None


def _linux_uptime() -> float | None:
    try:
        with open("/proc/uptime", encoding="ascii") as stream:
            return round(float(stream.read().split()[0]), 2)
    except (OSError, ValueError, IndexError):
        return None


def _linux_cpu_percent(interval: float = 0.1) -> float | None:
    """Estimate CPU busy percentage from two /proc/stat samples."""
    def sample() -> tuple[int, int] | None:
        try:
            with open("/proc/stat", encoding="ascii") as stream:
                fields = stream.readline().split()[1:]
            numbers = [int(value) for value in fields]
            idle = numbers[3] + (numbers[4] if len(numbers) > 4 else 0)
            return sum(numbers), idle
        except (OSError, ValueError, IndexError):
            return None

    first = sample()
    if first is None:
        return None
    time.sleep(max(0.0, interval))
    second = sample()
    if second is None:
        return None
    total_delta = second[0] - first[0]
    idle_delta = second[1] - first[1]
    if total_delta <= 0:
        return None
    return round(100 * (1 - idle_delta / total_delta), 2)


def get_system_metrics() -> dict[str, Any]:
    """Return a JSON-serializable snapshot. This function never changes the host."""
    metrics: dict[str, Any] = {
        "timestamp": time.time(),
        "platform": platform.system().lower() or "unknown",
        "psutil_available": psutil is not None,
    }

    if psutil is not None:
        try:
            metrics["cpu_percent"] = round(float(psutil.cpu_percent(interval=0.1)), 2)
            mem = psutil.virtual_memory()
            metrics["memory"] = {
                "total_mb": round(mem.total / (1024 * 1024), 2),
                "available_mb": round(mem.available / (1024 * 1024), 2),
                "percent_used": round(float(mem.percent), 2),
            }
            metrics["uptime_seconds"] = round(max(0.0, time.time() - psutil.boot_time()), 2)
        except (OSError, RuntimeError, AttributeError):
            metrics["metrics_note"] = "Some psutil metrics were unavailable."
    else:
        metrics["note"] = "psutil is unavailable; using standard-library fallback metrics."
        if platform.system() == "Linux":
            metrics["cpu_percent"] = _linux_cpu_percent()
            memory = _linux_memory()
            if memory is not None:
                metrics["memory"] = memory
            uptime = _linux_uptime()
            if uptime is not None:
                metrics["uptime_seconds"] = uptime

    try:
        disk = shutil.disk_usage(os.path.abspath(os.sep))
        metrics["disk"] = {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "percent_used": round(100 * (disk.total - disk.free) / disk.total, 2)
            if disk.total else 0.0,
        }
    except OSError:
        metrics["disk"] = None

    memory = metrics.get("memory")
    disk_metrics = metrics.get("disk")
    pressures = []
    if isinstance(memory, dict) and memory.get("percent_used", 0) >= 90:
        pressures.append("memory")
    if isinstance(disk_metrics, dict) and disk_metrics.get("percent_used", 0) >= 90:
        pressures.append("disk")
    metrics["resource_pressure"] = {
        "level": "high" if pressures else "normal",
        "resources": pressures,
        "threshold_percent": 90,
    }
    return metrics


def main() -> None:
    print(json.dumps(get_system_metrics(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
