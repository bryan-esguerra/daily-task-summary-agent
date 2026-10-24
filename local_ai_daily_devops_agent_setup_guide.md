# Local AI Daily DevOps Agent Setup Guide

This guide details how to set up a 100% offline, privacy-preserving AI agent on macOS. The agent monitors your daily Git commits across your workspaces and active applications via ActivityWatch, then automatically generates a structured Markdown daily standup report every day at 8:00 PM.

## Prerequisites
- macOS (Apple Silicon recommended for local LLM inference)
- Python 3
- [Homebrew](https://brew.sh/) installed

---

## Step 1: Install Ollama and Download the Model

Ollama runs the AI model entirely locally. We use `qwen2.5:7b` because it is highly optimized for coding context and fits well within a 16GB memory footprint.

1. Open your terminal and install Ollama:
   ```bash
   brew install ollama
   ```
2. Start the Ollama background service:
   ```bash
   brew services start ollama
   ```
3. Pull the local model:
   ```bash
   ollama pull qwen2.5:7b
   ```

---

## Step 2: Install and Configure ActivityWatch

ActivityWatch is a lightweight, open-source privacy tracker that logs your active window titles locally.

1. Install ActivityWatch via Homebrew:
   ```bash
   brew install --cask activitywatch
   ```
2. Open **ActivityWatch.app** from your `/Applications` folder.
3. Grant macOS Accessibility permissions:
   * Go to **System Settings > Privacy & Security > Accessibility**.
   * Toggle **ON** permissions for `ActivityWatch`.
4. Ensure it starts on boot:
   * Go to **System Settings > General > Login Items & Extensions**.
   * Add **ActivityWatch** to **Open at Login**.

---

## Step 3: Prepare Your Directories

Create the directory for your daily logs:

```bash
mkdir -p ~/Documents/DailyLogs
```

---

## Step 4: Configure the Python Agent Script

This project includes [`daily_summary_agent.py`](./daily_summary_agent.py). It uses only native Python libraries to avoid virtual environment dependency issues. It collects your git activity, fetches window telemetry from ActivityWatch, and passes it to Ollama.

Before automating, check or customize the settings at the top of [`daily_summary_agent.py`](./daily_summary_agent.py):

```python
WORKSPACE_DIR = os.path.expanduser("~/dev")           # Path to your git repos directory
NOTES_DIR = os.path.expanduser("~/Documents/DailyLogs") # Path to output folder for daily markdown notes
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"
```

---

## Step 5: Automate at 8:00 PM Daily (macOS Launchd)

We use macOS's native `launchd` to schedule the script to run automatically at 20:00 (8 PM) every day.

1. Check your current macOS username:
   ```bash
   whoami
   ```
2. Create your `launchd` plist configuration file:
   ```bash
   nano ~/Library/LaunchAgents/com.devops.dailylogs.plist
   ```
3. Paste the following configuration (replace `<YOUR_USERNAME>` with the output from `whoami`, or use the absolute path to your cloned repository):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.devops.dailylogs</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/<YOUR_USERNAME>/Documents/Projects/daily-task-summary-agent/daily_summary_agent.py</string>
    </array>
    
    <!-- Trigger every day at 8:00 PM (20:00) -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>20</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/tmp/daily_logs.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/daily_logs.err</string>
</dict>
</plist>
```
4. Load the schedule into macOS:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.devops.dailylogs.plist
   ```

---

## Troubleshooting & Manual Testing

To run the generator manually at any time to verify it works:
```bash
python3 /path/to/daily-task-summary-agent/daily_summary_agent.py
# Or directly from the project directory:
python3 daily_summary_agent.py
```

To view your logs:
```bash
open ~/Documents/DailyLogs
```

To check for any scheduled execution errors, check the temp logs:
```bash
cat /tmp/daily_logs.err
```