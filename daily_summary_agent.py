#!/usr/bin/env python3
import os
import re
import subprocess
import urllib.request
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION (Overrides via Environment Variables) ---
HOME = os.path.expanduser("~")
WORKSPACE_DIR = os.getenv("DAILY_AGENT_WORKSPACE", os.path.join(HOME, "Documents/Projects"))
NOTES_DIR = os.getenv("DAILY_AGENT_NOTES", os.path.join(HOME, "DailyLogs"))
OLLAMA_URL = os.getenv("DAILY_AGENT_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL_NAME = os.getenv("DAILY_AGENT_MODEL", "gemma2:9b")

APP_BLACKLIST = {
    "Finder", "loginwindow", "Spotify", "1Password", 
    "System Settings", "Music", "Messages", "WhatsApp"
}

def scrub_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and AWS access keys from raw text."""
    text = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]', text)
    text = re.sub(r'(bearer|token|password|secret)[\s:=]+["\']?([^"\']{8,})', r'\1: [REDACTED]', text, flags=re.I)
    return text

def get_time_boundaries():
    """Calculate exact yesterday 8:00 PM to today 8:00 PM timestamps."""
    now = datetime.now().astimezone()
    today_8pm = now.replace(hour=20, minute=0, second=0, microsecond=0)
    yesterday_8pm = today_8pm - timedelta(days=1)
    return yesterday_8pm, today_8pm

def collect_git_activity(base_path: str, start_dt: datetime) -> str:
    """Scan repos for commits created strictly within the 24-hour window."""
    since_time = start_dt.strftime("%Y-%m-%d %H:%M:%S")
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

    return "\n\n".join(repo_activities) if repo_activities else "No git commits made in this period."

def fetch_aw_events(start_dt: datetime, end_dt: datetime) -> list:
    """Fetch raw ActivityWatch window telemetry for the specified window."""
    start_iso = start_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        req = urllib.request.urlopen("http://localhost:5600/api/0/buckets", timeout=2)
        buckets = json.loads(req.read().decode())
        window_bucket = next((b for b in buckets if "aw-watcher-window" in b), None)
        if not window_bucket:
            return []

        events_url = f"http://localhost:5600/api/0/buckets/{window_bucket}/events?start={start_iso}&end={end_iso}&limit=2500"
        req = urllib.request.urlopen(events_url, timeout=3)
        return json.loads(req.read().decode())
    except Exception:
        return []

def collect_calendar_events(aw_events: list, start_dt: datetime, end_dt: datetime) -> str:
    """
    Combines scheduled calendar events (via icalBuddy) with active Google Meet 
    window telemetry (via ActivityWatch) into a single consolidated record.
    """
    sections = []

    # --- 1. Scheduled Events via icalBuddy ---
    ical_path = "/opt/homebrew/bin/icalBuddy" if os.path.exists("/opt/homebrew/bin/icalBuddy") else "icalBuddy"
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S %z")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S %z")

    try:
        cmd = [
            ical_path,
            "-ea",  # Exclude all-day tasks/timesheets
            "-nc",  # No calendar names
            "-b", "- ",
            "-iep", "title,datetime",
            f"eventsFrom:{start_str}",
            f"to:{end_str}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        calendar_output = res.stdout.strip()
        sections.append("### Scheduled Calendar Events (Apple Calendar / Google Sync):\n" + 
                        (calendar_output if calendar_output else "None recorded on calendar."))
    except Exception as e:
        sections.append(f"### Scheduled Calendar Events:\nSkipped (icalBuddy error: {str(e)})")

    # --- 2. Detected Google Meet Telemetry via ActivityWatch ---
    meet_sessions = defaultdict(list)
    max_gap_seconds = 45 * 60  # Allows up to 45 mins of multitasking while on call

    for event in aw_events:
        title = event.get("data", {}).get("title", "")
        if ("Meet -" in title or "Meet –" in title or "Google Meet" in title) and ("left the meeting" not in title.lower()):
            clean_title = re.sub(r' - (Google Chrome|Brave|Arc|Edge|Firefox).*$', '', title).strip()
            clean_title = clean_title.replace("–", "-")

            ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).timestamp()
            duration = event.get("duration", 0)
            end_ts = ts + duration

            matched = False
            for session in meet_sessions[clean_title]:
                if ts - session["last_seen"] <= max_gap_seconds:
                    session["last_seen"] = max(session["last_seen"], end_ts)
                    session["screen_time"] += duration
                    matched = True
                    break

            if not matched:
                meet_sessions[clean_title].append({
                    "start": ts,
                    "last_seen": end_ts,
                    "screen_time": duration
                })

    formatted_calls = []
    for title, sessions in meet_sessions.items():
        for s in sessions:
            span_mins = int((s["last_seen"] - s["start"]) // 60)
            screen_mins = int(s["screen_time"] // 60)
            est_mins = max(span_mins, screen_mins)
            if est_mins < 2:
                continue
            start_hour = datetime.fromtimestamp(s["start"]).strftime("%I:%M %p")
            formatted_calls.append(f"- {title} (~{est_mins} mins active, started ~{start_hour})")

    meet_output = "\n".join(formatted_calls) if formatted_calls else "No active Google Meet calls detected."
    sections.append("### Detected Google Meet Calls (Window Telemetry):\n" + meet_output)

    return "\n\n".join(sections)

def collect_window_activity(events: list) -> str:
    """Aggregate general application usage outside of meetings."""
    app_durations = defaultdict(int)
    app_titles = defaultdict(set)

    for event in events:
        app = event.get("data", {}).get("app", "")
        title = event.get("data", {}).get("title", "")
        duration = int(event.get("duration", 0))

        if not app or app in APP_BLACKLIST or duration < 60:
            continue
        # Skip Google Meet titles (already processed in collect_calendar_events)
        if "Meet -" in title or "Meet –" in title or "Google Meet" in title:
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

def run():
    start_dt, end_dt = get_time_boundaries()
    today_str = end_dt.strftime("%Y-%m-%d")

    # Collect telemetry
    raw_git = scrub_secrets(collect_git_activity(WORKSPACE_DIR, start_dt))
    aw_events = fetch_aw_events(start_dt, end_dt)
    raw_meetings_and_calendar = scrub_secrets(collect_calendar_events(aw_events, start_dt, end_dt))
    raw_apps = scrub_secrets(collect_window_activity(aw_events))

    prompt = f"""
You are an objective auditor generating a daily technical work log.
Your output must be 100% FACTUAL and directly grounded in the provided logs.

RULES TO PREVENT HALLUCINATION:
1. ONLY include facts, meetings, repos, or tools explicitly named in the RAW LOGS below.
2. Cross-reference scheduled calendar meetings and detected Google Meet calls into a single cohesive list under 'Meetings & Syncs'.
3. If Git logs show "No git commits made", explicitly state "No code commits recorded today".
4. If a section has no evidence in the logs, write "None recorded".
5. Do NOT interpret internal script directory warnings as engineering tasks.

=== RAW LOGS START ===
[GIT COMMITS (YESTERDAY 8 PM - TODAY 8 PM)]:
{raw_git}

[CALENDAR & MEETINGS (YESTERDAY 8 PM - TODAY 8 PM)]:
{raw_meetings_and_calendar}

[OTHER APPLICATIONS & TOOLS USED]:
{raw_apps}
=== RAW LOGS END ===

Respond strictly using this Markdown template:
# Daily Work Log - {today_str}

## 🚀 Code Deliverables
(List commits made and repos touched. If none, write "No code commits recorded today.")

## 📞 Meetings & Syncs
(Consolidate scheduled calendar meetings and Google Meet calls attended within the 8 PM to 8 PM window.)

## 🔍 Topics Researched & Systems Accessed
(Factual bullet points of tools opened, documentation viewed, or tasks evidenced in window titles. Do not extrapolate.)

## ⏱️ Active Applications
(Bulleted list of applications and durations directly from the telemetry.)

## 📋 Standup Talking Points
- **Yesterday / Today:** (1-2 sentences strictly summarizing commits and major meetings attended)
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

    print(f"Report successfully generated at: {file_path}")

if __name__ == "__main__":
    run()