#!/usr/bin/env bash
set -e

PLIST_PATH="$HOME/Library/LaunchAgents/com.devops.dailylogs.plist"
APP_DIR="$HOME/.local/share/daily-task-summary-agent"

echo "Uninstalling Daily Task Summary Agent..."

launchctl unload "$PLIST_PATH" 2>/dev/null || true
rm -f "$PLIST_PATH"
rm -rf "$APP_DIR"

echo "Unloaded daemon and removed agent files."
echo "Your generated logs in ~/DailyLogs were preserved."