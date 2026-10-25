#!/usr/bin/env bash
set -e

PLIST_PATH="$HOME/Library/LaunchAgents/com.devops.dailylogs.plist"
APP_DIR="$HOME/.local/share/daily-task-summary-agent"
MODEL_NAME="${DAILY_MODEL:-gemma2:9b}"

echo "=== Uninstalling Daily Task Summary Agent ==="

# 1. Unload and remove launchd background task
if [ -f "$PLIST_PATH" ]; then
    echo "Stopping and removing background daemon..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
fi

# 2. Remove script directory
if [ -d "$APP_DIR" ]; then
    echo "Removing script installation at $APP_DIR..."
    rm -rf "$APP_DIR"
fi

# 3. Clean up shell alias
SHELL_RC="$HOME/.zshrc"
if [ -f "$HOME/.bashrc" ] && [ "$SHELL" = "/bin/bash" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -f "$SHELL_RC" ]; then
    # Remove the alias line and comment
    sed -i '' '/# Daily Task Summary Agent/d' "$SHELL_RC" 2>/dev/null || true
    sed -i '' '/alias logday=/d' "$SHELL_RC" 2>/dev/null || true
    echo "Removed 'logday' alias from $SHELL_RC."
fi

# 4. Optional model cleanup
echo ""
read -p "Do you want to delete the local Ollama model '$MODEL_NAME' to free up disk space? (y/N): " -r CONFIRM
if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    if command -v ollama &> /dev/null; then
        echo "Deleting model $MODEL_NAME from Ollama..."
        ollama rm "$MODEL_NAME" 2>/dev/null || true
    fi
fi

echo ""
echo "=== Uninstall Complete ==="
echo "Note: Your generated daily logs in ~/DailyLogs have been preserved."