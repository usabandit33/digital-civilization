# Hardware & Resource Notes

**Last updated:** 2026-10-30 (initial template)

This file is the authoritative resource budget for the Digital Civilization. Every agent and process must respect these limits.

## Target Machine (initial)

| Item | Value | Notes |
|------|-------|-------|
| Machine | Older laptop (Lenovo G500s class) | Dual-core era CPU |
| RAM | ~7.6–8 GB | Critical constraint |
| CPU | i5-3230M or similar | Low single-thread performance |
| Storage | Check with `df -h` | Prefer SSD if available |
| OS | Linux (Mint / Ubuntu recommended) | |
| GPU | None / very weak | CPU-only inference |

## Model Constraints

- Prefer **one model loaded at a time**.
- Recommended starting models:
  - `openbmb/minicpm5-2b` (~1.6 GB)
  - `qwen3.5:4b` (heavier, use only when needed)
- Avoid 7B+ models on this hardware unless heavily quantized and tested.
- Keep context modest (16k–32k) rather than forcing large windows.

## Runtime Rules

- Never run multiple heavy processes (browser automation + large model + multiple Python services) simultaneously without checking free memory.
- Prefer SQLite + files over in-memory stores.
- Queue work instead of concurrent heavy tasks.
- Monitor with `free -h` and `htop` (or equivalent).
- Swap should exist and be used as a safety net, not as primary memory.

## How to update this file

After running diagnostics on the real machine, replace the placeholder values above with actual output from:

```bash
free -h
lscpu | grep -E 'Model name|CPU\(s\)|Thread|Core'
df -h /
swapon --show
ollama list
```

Commit the updated numbers so future agents have accurate limits.
