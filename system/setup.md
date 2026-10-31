# Setup Guide — Digital Civilization

This guide gets a Linux machine ready to run the civilization.

## 1. System packages

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv sqlite3 curl build-essential
```

Optional but recommended:

```bash
sudo apt install -y htop tmux
```

## 2. Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve   # or enable as a service
```

Pull the preferred models:

```bash
ollama pull openbmb/minicpm5-2b
ollama pull qwen3.5:4b
```

## 3. Clone the civilization

```bash
cd ~
git clone https://github.com/usabandit33/digital-civilization.git
cd digital-civilization
```

## 4. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r core/requirements.txt
```

## 5. Initialize the task database

```bash
python -m core.init_db
```

## 6. Run the system

You need two processes (use tmux or two terminals):

**Worker** (processes tasks):
```bash
source .venv/bin/activate
python -m core.main
```

**API** (lets other agents submit work):
```bash
source .venv/bin/activate
python -m core.serve
```

The API defaults to `http://127.0.0.1:8741`.

### One-shot test

```bash
python -m core.add_task "Summarize the current Phase 1 objectives in three bullet points"
python -m core.main --once
```

## 7. Continuous operation (systemd)

Example user services are in `system/`. You will typically want two units:

- one for the worker (`core.main`)
- one for the API (`core.serve`)

See `system/systemd.example` and create a second unit for the API if desired.

## 8. After setup

1. Update `system/hardware-notes.md` with real numbers from the machine.
2. Confirm both worker and API are running.
3. Submit a test task via curl or another agent.
4. Begin adding the first real tools.

## Safety notes

- Do not run the services as root.
- API is bound to localhost by default. Only expose it (via Tailscale, reverse proxy, etc.) after you understand the risk.
- Review any new tool before giving it network or shell access.
