#!/usr/bin/env bash
set -e

echo "=== Setting up Daily DevOps Task Summary Agent ==="

# 1. Detect Python path
PYTHON_BIN=$(which python3)
if [ -z "$PYTHON_BIN" ]; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# 2. Check Prerequisites
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama via Homebrew..."
    brew install ollama
    brew services start ollama
fi

echo "Ensuring Qwen2.5:7b model is available in Ollama..."
ollama pull qwen2.5:7b

# 3. Create unconstrained, TCC-safe directories
APP_DIR="$HOME/.local/share/daily-task-summary-agent"
LOGS_DIR="$HOME/DailyLogs"
PLIST_PATH="$HOME/Library/LaunchAgents/com.devops.dailylogs.plist"

mkdir -p "$APP_DIR"
mkdir -p "$LOGS_DIR"
mkdir -p "$HOME/Library/LaunchAgents"

# 4. Copy agent script to standard user-level binary location
cp "$(dirname "$0")/daily_summary_agent.py" "$APP_DIR/daily_summary_agent.py"
chmod +x "$APP_DIR/daily_summary_agent.py"

# 5. Generate LaunchAgent Plist with current user's paths
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

# 6. Load the agent
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

# 7. Add a convenience alias to shell rc if not already present
SHELL_RC="$HOME/.zshrc"
if [ -f "$HOME/.bashrc" ] && [ "$SHELL" = "/bin/bash" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

ALIAS_LINE="alias logday=\"$PYTHON_BIN $APP_DIR/daily_summary_agent.py && open $LOGS_DIR\""
if ! grep -q "alias logday" "$SHELL_RC"; then
    echo "" >> "$SHELL_RC"
    echo "# Daily Task Summary Agent" >> "$SHELL_RC"
    echo "$ALIAS_LINE" >> "$SHELL_RC"
    echo "Added 'logday' alias to $SHELL_RC"
fi

echo ""
echo "=== Installation Complete! ==="
echo "1. Output directory: $LOGS_DIR"
echo "2. Scheduled to run: Every day at 8:00 PM"
echo "3. Run manually anytime: Type 'logday' (restart terminal or run 'source $SHELL_RC')"
echo "Testing execution now..."
$PYTHON_BIN "$APP_DIR/daily_summary_agent.py"