"""
Cortex P0 Monitor
Checks for stale P0 issues and approaching deadlines.
Sends Teams alerts via webhook.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

GITEA_URL = "http://localhost:3100"
TOKEN = open(os.path.expanduser("~/gitea-api-token.txt")).read().strip()

# Teams webhook URL (update with actual webhook)
TEAMS_WEBHOOK = os.environ.get("TEAMS_WEBHOOK", "")

DEADLINES = {
    "helios": "2026-02-17",
    "bps-ai": "2026-02-20",
}

def gitea_get(path):
    try:
        req = urllib.request.Request(
            f"{GITEA_URL}/api/v1{path}",
            headers={"Authorization": f"token {TOKEN}"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except:
        return None

def check_deadlines():
    alerts = []
    today = datetime.now(timezone.utc).date()

    for repo, deadline_str in DEADLINES.items():
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        days_left = (deadline - today).days

        if days_left <= 3:
            issues = gitea_get(f"/repos/rize/{repo}/issues?state=open&labels=P0&limit=50") or []
            if issues:
                alerts.append(f"⚠️ {repo}: {len(issues)} open P0 issues, deadline in {days_left} days!")

    return alerts

def send_teams_alert(message):
    if not TEAMS_WEBHOOK:
        print(f"[NO WEBHOOK] {message}")
        return
    payload = json.dumps({"text": message}).encode()
    req = urllib.request.Request(TEAMS_WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)

if __name__ == "__main__":
    alerts = check_deadlines()
    for alert in alerts:
        send_teams_alert(alert)
        print(alert)

    if not alerts:
        print("No deadline alerts.")
