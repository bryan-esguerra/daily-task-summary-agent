#!/usr/bin/env bash
set -e

# Configurable defaults (can be overridden: e.g., DAILY_MODEL="qwen2.5:14b" ./install.sh)
MODEL_NAME="${DAILY_MODEL:-gemma2:9b}"
WORKSPACE_PATH="${DAILY_WORKSPACE:-$HOME/Documents/Projects}"

echo "=== Setting up Daily Task Summary Agent ==="
echo "Target Model: $MODEL_NAME"
echo "Workspace Path: $WORKSPACE_PATH"

# 1. Detect Python path
PYTHON_BIN=$(which python3)
if [ -z "$PYTHON_BIN" ]; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# 2. Check and start Ollama
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama via Homebrew..."
    brew install ollama
    brew services start ollama
else
    # Ensure Ollama service is active
    brew services start ollama 2>/dev/null || true
fi

# 3. Pull the upgraded model
echo "Pulling $MODEL_NAME (this may take a few minutes)..."
ollama pull "$MODEL_NAME"

# Optional cleanup: remove older qwen2.5:7b to reclaim ~4.7 GB of disk space
if ollama list | grep -q "qwen2.5:7b"; then
    echo "Found older qwen2.5:7b model. Removing to reclaim disk space..."
    ollama rm qwen2.5:7b || true
fi

# 4. Create unconstrained directories (avoids macOS TCC permission blocks)
APP_DIR="$HOME/.local/share/daily-task-summary-agent"
LOGS_DIR="$HOME/DailyLogs"
PLIST_PATH="$HOME/Library/LaunchAgents/com.devops.dailylogs.plist"

mkdir -p "$APP_DIR"
mkdir -p "$LOGS_DIR"
mkdir -p "$HOME/Library/LaunchAgents"

# 5. Copy agent script to local share
cp "$(dirname "$0")/daily_summary_agent.py" "$APP_DIR/daily_summary_agent.py"
chmod +x "$APP_DIR/daily_summary_agent.py"

# 6. Generate LaunchAgent Plist with environment variables
echo "Generating launchd configuration..."
cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.devops.dailylogs</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$APP_DIR/daily_summary_agent.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>DAILY_AGENT_MODEL</key>
        <string>$MODEL_NAME</string>
        <key>DAILY_AGENT_WORKSPACE</key>
        <string>$WORKSPACE_PATH</string>
        <key>DAILY_AGENT_NOTES</key>
        <string>$LOGS_DIR</string>
    </dict>
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
EOF

# 7. Register and start background service
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

# 8. Add terminal alias
SHELL_RC="$HOME/.zshrc"
if [ -f "$HOME/.bashrc" ] && [ "$SHELL" = "/bin/bash" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

ALIAS_LINE="alias logday=\"$PYTHON_BIN $APP_DIR/daily_summary_agent.py && open $LOGS_DIR\""
if ! grep -q "alias logday" "$SHELL_RC"; then
    echo "" >> "$SHELL_RC"
    echo "# Daily Task Summary Agent" >> "$SHELL_RC"
    echo "$ALIAS_LINE" >> "$SHELL_RC"
fi

echo ""
echo "=== Installation Complete! ==="
echo "- Logs directory: $LOGS_DIR"
echo "- Scheduled time: 8:00 PM daily"
echo "- Active LLM:     $MODEL_NAME"
echo ""
echo "Testing immediate run with $MODEL_NAME..."
$PYTHON_BIN "$APP_DIR/daily_summary_agent.py"