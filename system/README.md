# System

Deployment, operations, and constraints for the Digital Civilization.

## Current contents

| File | Purpose |
|------|---------|
| `hardware-notes.md` | Authoritative resource budget and machine constraints |
| `setup.md` | Step-by-step setup instructions |
| `systemd.example` | Example user systemd unit for continuous operation |

## Design goals

- Stay runnable on ~8 GB RAM
- Survive reboots via systemd (user service preferred)
- Keep the core loop simple and observable
- Make it easy for a new agent to understand the runtime state
