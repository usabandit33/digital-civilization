# Hardware & Resource Notes

**Last updated:** 2026-10-31

This file is the authoritative resource budget for the Digital Civilization. Every agent and process must respect these limits.

## Current Observed Environment (2026-10-31)

Diagnostics were run from **Git Bash on Windows** (UCRT64), not a native Linux laptop.

| Item | Value | Notes |
|------|-------|-------|
| Host OS | Windows | Git Bash / MSYS2 UCRT64 environment |
| Shell | Git Bash | Many Linux utilities (`free`, `lscpu`, `hostnamectl`, `lsblk`, `swapon`) are unavailable |
| Python | 3.14.6 | |
| Ollama | 0.40.13 | Installed and working |
| Disk (Git view) | ~476 GB total, ~250 GB free | Root shown as `C:/Program Files/Git` |

### Available Ollama models (at time of measurement)

| Model | Size | Notes |
|-------|------|-------|
| qwen3.5:4b | 3.3 GB | Good candidate for constrained / local work |
| hermes3:latest | 4.7 GB | |
| humanity:latest | 4.9 GB | |
| mattmurdock32/llama-humanity:latest | 4.9 GB | |
| mattmurdock32/humanity:latest | 4.9 GB | |
| gemma4:e4b-it-qat | 6.1 GB | Heavier |
| minimax-m3.1-flash:cloud | — | Cloud |

## Original Target (still relevant)

The project was originally designed for an older Linux laptop (~8 GB RAM, dual-core era CPU). Designs should remain viable under those constraints even when developed on a stronger Windows machine.

| Item | Target value | Notes |
|------|--------------|-------|
| Machine | Older laptop (Lenovo G500s class) | Dual-core era CPU |
| RAM | ~7.6–8 GB | Critical constraint on the intended runtime host |
| CPU | i5-3230M or similar | Low single-thread performance |
| GPU | None / very weak | CPU-only inference expected |

## Runtime Rules

- Prefer **one model loaded at a time**.
- On the Windows development machine, `qwen3.5:4b` is a reasonable default; heavier models are available but should not be assumed on the eventual Linux host.
- Keep context modest.
- Prefer SQLite + files over large in-memory stores.
- Queue work instead of running many heavy tasks concurrently.
- When moving to the real Linux laptop, re-run diagnostics and replace the numbers in this file.

## How to update this file

On a real Linux host, run:

```bash
free -h
lscpu | grep -E 'Model name|CPU\(s\)|Thread|Core'
df -h /
swapon --show
ollama list
```

Then update the tables above and commit.
