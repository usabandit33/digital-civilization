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

## 6. First run (manual)

```bash
source .venv/bin/activate
python -m core.main --once
```

This processes one task (or idles cleanly if the queue is empty) and writes a journal entry.

## 7. Run continuously (systemd)

Create a user service (example):

```bash
mkdir -p ~/.config/systemd/user
```

Then create `~/.config/systemd/user/digital-civilization.service` with content similar to the example in `system/systemd.example`.

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now digital-civilization.service
```

## 8. After setup

1. Update `system/hardware-notes.md` with real numbers from the machine.
2. Run the Bootstrap Agent (see `agents/bootstrap-agent.md`) or manually create a journal entry.
3. Begin Phase 1 work: first real tools and a small invention.

## Safety notes

- Do not run the service as root.
- Keep the working directory and database inside the repository or a clearly defined data path.
- Review any new tool before giving it network or shell access.
