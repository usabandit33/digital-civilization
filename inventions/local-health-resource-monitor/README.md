# Local Health & Resource Monitor

A small, read-only Python utility that reports CPU, RAM, disk, uptime, and basic resource-pressure indicators for a local agent host.

## Usage

From the repository root:

```bash
python inventions/local-health-resource-monitor/monitor.py
```

It prints one JSON object to standard output, suitable for parsing by another agent or script.

## Output

- `timestamp`: Unix timestamp
- `platform`: normalized operating-system name
- `psutil_available`: whether the optional dependency was found
- `cpu_percent`: CPU busy percentage when available
- `memory`: total / available MB and percent used
- `disk`: root filesystem total / free GB and percent used
- `uptime_seconds`: host uptime when available
- `resource_pressure`: high when memory or disk usage reaches 90%, otherwise normal

Unavailable metrics are omitted rather than fabricated. The Linux fallback reads `/proc` and uses Python's standard library. Disk usage uses `shutil.disk_usage`.

## Dependencies and resource notes

- Python 3.9+ standard library only.
- Optional: `psutil` for richer cross-platform CPU, memory, and uptime data.
- No network access, subprocesses, writes, privileged operations, or background service.
- CPU sampling waits approximately 0.1 seconds.
- Designed for constrained hosts; memory use is negligible.

## Validation

Run the offline unit tests:

```bash
python -m unittest discover -s inventions/local-health-resource-monitor -p 'test_*.py'
```

## Limitations

The standard-library fallback provides CPU, RAM, and uptime only on Linux. On other systems without psutil, those metrics may be absent. Pressure is a simple 90% threshold indicator, not a diagnosis of system health.
