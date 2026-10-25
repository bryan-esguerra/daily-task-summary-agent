import os
import re
import subprocess
import urllib.request
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
# Set this to where your actual Git repositories live:
WORKSPACE_DIR = os.path.expanduser("~/Documents/Projects")
NOTES_DIR = os.path.expanduser("~/DailyLogs")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "gemma2:9b"  # Upgraded model with strict adherence

APP_BLACKLIST = {
    "Finder", "loginwindow", "Spotify", "1Password", 
    "System Settings", "Music", "Messages", "WhatsApp"
}

def scrub_secrets(text: str) -> str:
    text = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]', text)
    text = re.sub(r'(bearer|token|password|secret)[\s:=]+["\']?([^"\']{8,})', r'\1: [REDACTED]', text, flags=re.I)
    return text

def collect_git_activity(base_path: str) -> str:
    now = datetime.now()
    since_time = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    repo_activities = []

    if not os.path.exists(base_path):
        return "None: Workspace directory does not exist or has no git repos."

    for root, dirs, _ in os.walk(base_path):
        if ".git" in dirs:
            log_cmd = [
                "git", "-C", root, "log",
                f"--since={since_time}",
                "--pretty=format:%h - %s",
                "--no-merges"
            ]
            res = subprocess.run(log_cmd, capture_output=True, text=True)
            commits = res.stdout.strip()

            if commits:
                repo_name = os.path.basename(root)
                repo_activities.append(f"Repo [{repo_name}]:\n{commits}")

            dirs.remove(".git")

    return "\n\n".join(repo_activities) if repo_activities else "No git commits made in the last 24 hours."

def collect_window_activity() -> str:
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        req = urllib.request.urlopen("http://localhost:5600/api/0/buckets", timeout=2)
        buckets = json.loads(req.read().decode())
        window_bucket = next((b for b in buckets if "aw-watcher-window" in b), None)

        if not window_bucket:
            return "No application telemetry available."

        events_url = f"http://localhost:5600/api/0/buckets/{window_bucket}/events?start={start_time}&end={end_time}&limit=1500"
        req = urllib.request.urlopen(events_url, timeout=2)
        events = json.loads(req.read().decode())

        app_durations = defaultdict(int)
        app_titles = defaultdict(set)

        for event in events:
            app = event.get("data", {}).get("app", "")
            title = event.get("data", {}).get("title", "")
            duration = int(event.get("duration", 0))

            if not app or app in APP_BLACKLIST or duration < 60:
                continue

            app_durations[app] += duration
            if title and title != app:
                app_titles[app].add(title[:80])

        lines = []
        for app, sec in sorted(app_durations.items(), key=lambda x: x[1], reverse=True):
            mins = sec // 60
            if mins < 3:
                continue
            context_samples = "; ".join(list(app_titles[app])[:3])
            lines.append(f"- {app} ({mins} mins): {context_samples}")

        return "\n".join(lines) if lines else "No significant application activity recorded."

    except Exception:
        return "No application telemetry recorded."

def run():
    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_git = scrub_secrets(collect_git_activity(WORKSPACE_DIR))
    raw_apps = scrub_secrets(collect_window_activity())

    prompt = f"""
You are an objective auditor generating a daily technical work log.
Your output must be 100% FACTUAL and directly grounded in the provided logs.

RULES TO PREVENT HALLUCINATION:
1. ONLY include facts, repos, tools, or topics explicitly named in the RAW LOGS below.
2. NEVER assume, extrapolate, or embellish. (For example: if Google Chrome shows a documentation title, state that they read documentation on that topic. Do NOT state they "optimized application telemetry").
3. If Git logs show "No git commits", explicitly state "No code commits recorded today".
4. Do NOT mention internal directory paths or configuration errors as accomplishments.
5. If a section has no evidence in the logs, write "None recorded".

=== RAW LOGS START ===
[GIT COMMITS - LAST 24H]:
{raw_git}

[APPLICATION AND WINDOW ACTIVITY - LAST 24H]:
{raw_apps}
=== RAW LOGS END ===

Respond strictly using this Markdown template:
# Daily Work Log - {today_str}

## 🚀 Code Deliverables
(List commits made and repos touched. If none, write "No commits made today.")

## 🔍 Topics Researched & Systems Accessed
(Factual bullet points of tools opened, documentation viewed, or tasks evidenced in window titles. Do not extrapolate.)

## ⏱️ Active Applications
(Bulleted list of applications and durations directly from the telemetry.)

## 📋 Standup Talking Points
- **Yesterday / Today:** (1-2 sentences strictly summarizing the actual logs)
- **Blockers:** None recorded
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "keep_alive": 0
    }

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            output = data.get("response", "Error: No response generated.")
    except Exception as e:
        output = f"Failed to generate summary: {str(e)}"

    os.makedirs(NOTES_DIR, exist_ok=True)
    file_path = os.path.join(NOTES_DIR, f"{today_str}.md")
    with open(file_path, "w") as f:
        f.write(output)

    print(f"Report written to: {file_path}")

if __name__ == "__main__":
    run()