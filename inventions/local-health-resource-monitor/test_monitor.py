"""Offline tests for the Local Health & Resource Monitor."""

import importlib.util
import json
import pathlib
import unittest
from unittest import mock

MODULE_PATH = pathlib.Path(__file__).with_name("monitor.py")
SPEC = importlib.util.spec_from_file_location("health_monitor", MODULE_PATH)
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def test_linux_memory_parser(self):
        sample = "MemTotal: 2048000 kB\nMemAvailable: 1024000 kB\n"
        with mock.patch("builtins.open", mock.mock_open(read_data=sample)):
            result = monitor._linux_memory()
        self.assertEqual(result["total_mb"], 2000.0)
        self.assertEqual(result["available_mb"], 1000.0)
        self.assertEqual(result["percent_used"], 50.0)

    def test_linux_uptime_parser(self):
        with mock.patch("builtins.open", mock.mock_open(read_data="1234.5 99.0\n")):
            self.assertEqual(monitor._linux_uptime(), 1234.5)

    def test_pressure_thresholds(self):
        fake_psutil = mock.Mock()
        fake_psutil.cpu_percent.return_value = 12.0
        fake_psutil.virtual_memory.return_value = mock.Mock(
            total=1000 * 1024 * 1024, available=50 * 1024 * 1024, percent=95.0
        )
        fake_psutil.boot_time.return_value = monitor.time.time() - 10
        with mock.patch.object(monitor, "psutil", fake_psutil), \
             mock.patch.object(monitor.shutil, "disk_usage",
                               return_value=mock.Mock(total=100, free=5)):
            result = monitor.get_system_metrics()
        self.assertEqual(result["resource_pressure"]["level"], "high")
        self.assertEqual(set(result["resource_pressure"]["resources"]), {"memory", "disk"})
        json.dumps(result)

    def test_fallback_metrics_are_json_serializable(self):
        with mock.patch.object(monitor, "psutil", None), \
             mock.patch.object(monitor.platform, "system", return_value="Linux"), \
             mock.patch.object(monitor, "_linux_cpu_percent", return_value=7.5), \
             mock.patch.object(monitor, "_linux_memory", return_value={
                 "total_mb": 100.0, "available_mb": 80.0, "percent_used": 20.0
             }), \
             mock.patch.object(monitor, "_linux_uptime", return_value=20.0), \
             mock.patch.object(monitor.shutil, "disk_usage",
                               return_value=mock.Mock(total=100, free=80)):
            result = monitor.get_system_metrics()
        self.assertFalse(result["psutil_available"])
        self.assertEqual(result["cpu_percent"], 7.5)
        self.assertEqual(result["resource_pressure"]["level"], "normal")
        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
