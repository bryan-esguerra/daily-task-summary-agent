# Daily Task Summary Agent

A 100% offline, privacy-preserving AI assistant that monitors your daily Git commits across a rolling 24-hour window (8:00 PM yesterday to 8:00 PM today), scheduled calendar meetings (via `icalBuddy`), Google Meet calls, and active window telemetry (via ActivityWatch), synthesizing them into an objective, factual Markdown daily work log using a local Ollama LLM.

## Features
- **100% Local & Private**: No data leaves your machine; runs locally with Ollama (default: `gemma2:9b`).
- **Calendar & Meeting Sync**: Consolidates scheduled calendar events from Apple Calendar / synced Google Calendar via `icalBuddy` and detected Google Meet screen sessions into a cohesive "Meetings & Syncs" section.
- **Zero Hallucination Guardrails**: Prompt engineered with strict grounding rules to ensure only explicitly recorded commits, meetings, tools, and docs appear in your reports.
- **Strict 24-Hour Boundary**: Tracks activity strictly from yesterday 8:00 PM to today 8:00 PM to match your daily standup cycle.
- **Zero Python Dependencies**: Written entirely with Python standard libraries (`urllib`, `subprocess`, `json`, `datetime`) — no virtual environments or `pip` errors.
- **TCC & Permission-Safe**: Stores logs in `~/DailyLogs` instead of macOS protected directories (`~/Documents`) to prevent repetitive system authorization prompts.
- **Secret Scrubbing**: Automatically masks sensitive patterns such as AWS access keys, bearer tokens, passwords, and secrets prior to model inference.
- **Convenient CLI Shortcut**: Adds a `logday` terminal command to generate your summary and open your notes folder on demand.
- **Automated Scheduling**: Native macOS `launchd` automation running daily at 8:00 PM.

---

## Repository Structure

```plaintext
daily-task-summary-agent/
├── daily_summary_agent.py   # Agent script with strict grounding & configurable paths
├── install.sh               # Automated one-click setup script (Ollama, models, launchd, alias)
├── uninstall.sh             # Clean teardown script (unloads launchd, cleans alias & model)
└── README.md
```

---

## Quickstart (Under 60 Seconds)

### 1. Prerequisites
- macOS (Apple Silicon M-series recommended for local LLM inference)
- [Homebrew](https://brew.sh/)
- Python 3

### 2. Optional Telemetry & Calendar Integrations

#### A. Install `icalBuddy` for Scheduled Calendar Meetings (Recommended)
`icalBuddy` reads local events from macOS Apple Calendar (including synced Google, Outlook, or iCloud calendars).

```bash
brew install ical-buddy
```

> **IMPORTANT: Grant Calendar Permissions to your Terminal**  
> macOS requires explicit permission for terminal applications to access Calendar data:  
> 1. Go to **System Settings > Privacy & Security > Calendars**.  
> 2. Ensure your terminal emulator (e.g., **Terminal**, **iTerm2**, **Ghostty**, or **Alacritty**) is toggled **ON**.  
> 
> *If `icalBuddy` is not installed or permission is withheld, the agent will skip calendar events gracefully and continue compiling git and telemetry logs.*

#### B. Install ActivityWatch for Window & Google Meet Telemetry
ActivityWatch is a lightweight, open-source privacy tracker that logs active window titles locally. It is also used to detect active Google Meet call durations.

```bash
brew install --cask activitywatch
```
1. Open **ActivityWatch.app** from `/Applications`.
2. Grant macOS Accessibility permissions (**System Settings > Privacy & Security > Accessibility > ActivityWatch [ON]**).
3. Set ActivityWatch to open at login (**System Settings > General > Login Items & Extensions**).

> **Note**: If ActivityWatch is not running, the agent will skip window and Google Meet telemetry, compiling logs from git and calendar events alone.

### 3. One-Click Automated Setup
Clone the repository and run `install.sh`:

```bash
git clone https://github.com/bryan-esguerra/daily-task-summary-agent.git
cd daily-task-summary-agent
chmod +x install.sh uninstall.sh
./install.sh
```

#### What `install.sh` does automatically:
1. Detects your Python 3 binary.
2. Checks for and starts **Ollama** (installs via Homebrew if not found).
3. Pulls the target local model (`gemma2:9b` by default) and cleans up older model artifacts (e.g. `qwen2.5:7b`) to reclaim disk space.
4. Creates non-restricted user directories: `~/.local/share/daily-task-summary-agent` and `~/DailyLogs`.
5. Copies the agent script into the local share directory and generates a personalized `launchd` plist injected with your workspace configuration.
6. Loads the `launchd` service to run automatically every day at 8:00 PM.
7. Adds a `logday` convenience alias to your shell configuration (`~/.zshrc` or `~/.bashrc`).
8. Runs an immediate test execution.

---

## Customizing Installation

You can pass environment variables directly to `./install.sh` to customize your setup during installation:

```bash
# Example: Use a custom repository path and custom model
DAILY_WORKSPACE="$HOME/dev" DAILY_MODEL="gemma2:9b" ./install.sh
```

| Variable | Default | Description |
|---|---|---|
| `DAILY_MODEL` | `gemma2:9b` | Local Ollama model to pull and configure |
| `DAILY_WORKSPACE` | `~/Documents/Projects` | Root directory to scan for Git repositories |

---

## Usage

### Run Manually (`logday`)
Generate your report on demand and immediately open the daily notes folder:

```bash
logday
```

*(Note: If you just ran `install.sh`, restart your terminal or run `source ~/.zshrc` to activate the alias.)*

You can also run the script directly:
```bash
python3 daily_summary_agent.py
```

### View Daily Logs
Your markdown logs are saved to `~/DailyLogs/YYYY-MM-DD.md`.
```bash
open ~/DailyLogs
```

---

## Script Configuration

Inside [daily_summary_agent.py](./daily_summary_agent.py), you can adjust configuration settings at the top of the file or via environment variables:

```python
WORKSPACE_DIR = os.getenv("DAILY_AGENT_WORKSPACE", os.path.expanduser("~/Documents/Projects"))
NOTES_DIR = os.getenv("DAILY_AGENT_NOTES", os.path.expanduser("~/DailyLogs"))
OLLAMA_URL = os.getenv("DAILY_AGENT_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL_NAME = os.getenv("DAILY_AGENT_MODEL", "gemma2:9b")
```

---

## Uninstall

To cleanly remove the background service and installed files:

```bash
./uninstall.sh
```

The uninstaller will:
1. Stop and remove the `launchd` scheduled agent.
2. Delete the installed script directory from `~/.local/share/daily-task-summary-agent`.
3. Clean up the `logday` alias from your `~/.zshrc` / `~/.bashrc`.
4. Prompt whether you want to delete the local Ollama model to free up disk space (~5.5 GB).
5. **Preserve** your generated logs in `~/DailyLogs/`.