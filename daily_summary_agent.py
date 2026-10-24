import os
import re
import subprocess
import urllib.request
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

WORKSPACE_DIR = os.path.expanduser("~/dev")
NOTES_DIR = os.path.expanduser("~/Documents/DailyLogs")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

APP_BLACKLIST = {
    "Finder", "loginwindow", "Spotify", "1Password", 
    "System Settings", "Music", "Messages", "WhatsApp"
}

def scrub_secrets(text: str) -> str:
    """Mask common AWS keys, tokens, and credentials."""
    text = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]', text)
    text = re.sub(r'(bearer|token|password|secret)[\s:=]+["\']?([^"\']{8,})', r'\1: [REDACTED]', text, flags=re.I)
    return text

def collect_git_activity(base_path: str) -> str:
    """Scan repos for commits created in the last 24 hours."""
    # Rolling 24-hour timestamp
    since_time = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    repo_activities = []

    if not os.path.exists(base_path):
        return "Workspace directory not found."

    for root, dirs, _ in os.walk(base_path):
        if ".git" in dirs:
            log_cmd = [
                "git", "-C", root, "log",
                f"--since={since_time}",
                "--pretty=format:%h - %s (%an)",
                "--no-merges"
            ]
            res = subprocess.run(log_cmd, capture_output=True, text=True)
            commits = res.stdout.strip()

            branch_cmd = ["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"]
            branch = subprocess.run(branch_cmd, capture_output=True, text=True).stdout.strip()

            if commits:
                repo_name = os.path.basename(root)
                repo_activities.append(f"Repo: {repo_name} [Branch: {branch}]\nCommits:\n{commits}")

            dirs.remove(".git")

    return "\n\n".join(repo_activities) if repo_activities else "No git commits recorded in last 24h."

def collect_window_activity() -> str:
    """Fetch window activity from the last 24 hours."""
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        req = urllib.request.urlopen("http://localhost:5600/api/0/buckets", timeout=3)
        buckets = json.loads(req.read().decode())
        window_bucket = next((b for b in buckets if "aw-watcher-window" in b), None)

        if not window_bucket:
            return "ActivityWatch running, but window bucket not found."

        events_url = f"http://localhost:5600/api/0/buckets/{window_bucket}/events?start={start_time}&end={end_time}&limit=1500"
        req = urllib.request.urlopen(events_url, timeout=3)
        events = json.loads(req.read().decode())

        app_durations = defaultdict(int)
        app_titles = defaultdict(set)

        for event in events:
            app = event.get("data", {}).get("app", "")
            title = event.get("data", {}).get("title", "")
            duration = int(event.get("duration", 0))

            if not app or app in APP_BLACKLIST or duration < 45:
                continue

            app_durations[app] += duration
            if title and title != app:
                app_titles[app].add(title[:80])

        lines = []
        for app, sec in sorted(app_durations.items(), key=lambda x: x[1], reverse=True):
            mins = sec // 60
            if mins < 2:
                continue
            context_samples = "; ".join(list(app_titles[app])[:3])
            lines.append(f"- **{app}** ({mins} mins): {context_samples}")

        return "\n".join(lines) if lines else "No significant app activity recorded."

    except Exception as e:
        return f"ActivityWatch offline or unreachable: {str(e)}"

def run():
    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_git = scrub_secrets(collect_git_activity(WORKSPACE_DIR))
    raw_apps = scrub_secrets(collect_window_activity())

    prompt = f"""
You are an executive assistant to a Lead DevOps Engineer.
Using the engineering activity logs and app usage telemetry below, generate a clean, structured daily work note and standup summary.

### Git Commits Today:
{raw_git}

### Active Applications & Window Context Today:
{raw_apps}

Strictly output in this Markdown format:
# Daily DevOps Log - {today_str}

## 🚀 Key Accomplishments
- (Synthesize git commits and major terminal/IDE activities into clear achievements)

## 🔍 Investigations, Research & Troubleshooting
- (Identify what docs were read in browser, cluster debugging in terminal/k9s/ArgoCD UI, etc.)

## ⏱️ Focus Distribution
- (Highlight key tools and repositories that took the most active focus today)

## 📋 Standup Talking Points
- **Yesterday / Today:**
- **Next Up:**
- **Blockers:** None
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "keep_alive": 0
    }

    print("Generating summary with Ollama via native urllib...")
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

    print(f"Summary written to: {file_path}")

if __name__ == "__main__":
    run()