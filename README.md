# Daily Task Summary Agent

A 100% offline, privacy-preserving AI assistant that monitors your daily git commits and active window telemetry (via ActivityWatch), synthesizing them into structured Markdown daily standup reports using a local Ollama LLM.

## Features
- **100% Local & Private**: No data leaves your machine; runs on Ollama with local models (`qwen2.5:7b`).
- **Zero Python Dependencies**: Written entirely with Python standard libraries (`urllib`, `subprocess`, `json`, etc.) — no virtual environments or `pip` errors.
- **TCC & Permission-Safe**: Stores logs in `~/DailyLogs` instead of macOS protected directories (`~/Documents`) to avoid system authorization dialog prompts.
- **Secret Scrubbing**: Automatically redacts sensitive patterns such as AWS access keys, bearer tokens, passwords, and secrets before prompting the model.
- **Activity Telemetry**: Captures repo commit history and active work apps from ActivityWatch.
- **Convenient CLI Shortcut**: Adds a `logday` terminal command to generate your summary and open your notes folder anytime with a single command.
- **Automated Scheduling**: Native macOS `launchd` automation running daily at 8:00 PM.

---

## Repository Structure

```plaintext
daily-task-summary-agent/
├── daily_summary_agent.py   # Agent script with dynamic paths & env var overrides
├── install.sh               # Automated one-click setup script
├── uninstall.sh             # Clean teardown script
└── README.md
```

---

## Quickstart (Under 60 Seconds)

### 1. Prerequisites
- macOS (Apple Silicon recommended for local LLM inference)
- [Homebrew](https://brew.sh/)
- Python 3

### 2. Install & Configure ActivityWatch (Optional but Recommended)
ActivityWatch is a lightweight, open-source privacy tracker that logs active window titles locally.

```bash
brew install --cask activitywatch
```
1. Open **ActivityWatch.app** from `/Applications`.
2. Grant macOS Accessibility permissions (**System Settings > Privacy & Security > Accessibility > ActivityWatch [ON]**).
3. Set ActivityWatch to open at login (**System Settings > General > Login Items & Extensions**).

> **Note**: If ActivityWatch is not installed or running, the agent will gracefully continue and generate summaries using git commits alone.

### 3. One-Click Automated Setup
Clone the repository and run `install.sh`:

```bash
git clone https://github.com/<your-username>/daily-task-summary-agent.git
cd daily-task-summary-agent
chmod +x install.sh uninstall.sh
./install.sh
```

What `install.sh` does automatically:
1. Detects your Python 3 environment.
2. Checks for and installs **Ollama** (via Homebrew if missing) and pulls `qwen2.5:7b`.
3. Creates safe user directories: `~/.local/share/daily-task-summary-agent` and `~/DailyLogs`.
4. Copies the agent script into your user binary directory and generates your personalized `launchd` plist without manual path editing.
5. Loads the `launchd` agent to trigger daily at 8:00 PM.
6. Configures the `logday` shell alias in `~/.zshrc` (or `~/.bashrc`).
7. Executes a test run immediately.

---

## Usage

### Run Manually (`logday`)
Generate your report on demand and immediately open your logs folder:

```bash
logday
```

*(Note: If you just ran `install.sh`, restart your terminal or run `source ~/.zshrc` to activate the alias.)*

You can also run the agent directly with Python:
```bash
python3 daily_summary_agent.py
```

### View Daily Logs
Your markdown logs are saved to `~/DailyLogs/YYYY-MM-DD.md`.
```bash
open ~/DailyLogs
```

---

## Configuration & Environment Variables

`daily_summary_agent.py` works out of the box with sensible defaults, but can be customized with environment variables:

| Variable | Default | Description |
|---|---|---|
| `DAILY_AGENT_WORKSPACE` | `~/dev` | Root directory containing your git repositories |
| `DAILY_AGENT_NOTES` | `~/DailyLogs` | Directory where daily markdown notes are stored |
| `DAILY_AGENT_OLLAMA_URL` | `http://127.0.0.1:11434/api/generate` | Local Ollama API endpoint |
| `DAILY_AGENT_MODEL` | `qwen2.5:7b` | Ollama model name to use for synthesis |

Example override in `~/.zshrc`:
```bash
export DAILY_AGENT_WORKSPACE="$HOME/Documents/Projects"
export DAILY_AGENT_MODEL="qwen2.5:7b"
```

---

## Uninstall

To cleanly remove the automated background service and installed binary files:

```bash
./uninstall.sh
```

Your generated daily logs in `~/DailyLogs/` remain preserved.