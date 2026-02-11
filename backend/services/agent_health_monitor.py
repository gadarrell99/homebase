#!/usr/bin/env python3
"""
Sentinel Agent Health Monitor
Pings all 5 OpenClaw agents + legacy FastAPI services, logs health to DB, alerts on failures.
Runs every 5 minutes via cron.
Updated: 2026-02-11 — All 5 agents now on OpenClaw gateways (localhost-bound).
"""
import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime

DB_PATH = os.path.expanduser("~/homebase/data/homebase.db")

AGENTS = [
    # OpenClaw Gateways (all bind to localhost on .241, need SSH check)
    {"name": "David",    "host": "192.168.65.241", "port": 18789, "check": "ssh",  "path": "/", "ssh_user": "agents"},
    {"name": "Cortex",   "host": "192.168.65.241", "port": 9101,  "check": "ssh",  "path": "/", "ssh_user": "agents"},
    {"name": "Apex",     "host": "192.168.65.241", "port": 9004,  "check": "ssh",  "path": "/", "ssh_user": "agents"},
    {"name": "Aegis",    "host": "192.168.65.241", "port": 9005,  "check": "ssh",  "path": "/", "ssh_user": "agents"},
    {"name": "Sentinel", "host": "192.168.65.241", "port": 9006,  "check": "ssh",  "path": "/", "ssh_user": "agents"},
    # Legacy FastAPI services (still running, externally accessible)
    {"name": "Apex-API",    "host": "192.168.65.241", "port": 9002, "check": "http", "path": "/health"},
    {"name": "Aegis-API",   "host": "192.168.65.241", "port": 9003, "check": "http", "path": "/health"},
    # Sentinel API on Homebase
    {"name": "Sentinel-API", "host": "127.0.0.1",     "port": 8000, "check": "http", "path": "/api/sentinel/overview"},
]

ALERT_THRESHOLD = 3  # consecutive failures before alerting


def check_agent(agent):
    """Check a single agent's health. Returns (status, response_time_ms)."""
    if agent.get("expected_offline"):
        return "offline(expected)", 0

    start = time.time()

    if agent.get("check") == "ssh":
        ssh_user = agent.get("ssh_user", "agents")
        url = f"http://127.0.0.1:{agent['port']}{agent['path']}"
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", f"{ssh_user}@{agent['host']}",
                 f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout 5 --max-time 8 {url}"],
                capture_output=True, text=True, timeout=20
            )
            elapsed_ms = int((time.time() - start) * 1000)
            http_code = result.stdout.strip().replace("'", "")
            if http_code.startswith("2"):
                return "healthy", elapsed_ms
            else:
                return f"error:{http_code}", elapsed_ms
        except subprocess.TimeoutExpired:
            return "timeout", int((time.time() - start) * 1000)
        except Exception as e:
            return f"error:{str(e)[:50]}", int((time.time() - start) * 1000)
    else:
        url = f"http://{agent['host']}:{agent['port']}{agent['path']}"
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--connect-timeout", "5", "--max-time", "30", url],
                capture_output=True, text=True, timeout=15
            )
            elapsed_ms = int((time.time() - start) * 1000)
            http_code = result.stdout.strip()
            if http_code.startswith("2"):
                return "healthy", elapsed_ms
            else:
                return f"error:{http_code}", elapsed_ms
        except subprocess.TimeoutExpired:
            return "timeout", int((time.time() - start) * 1000)
        except Exception as e:
            return f"error:{str(e)[:50]}", int((time.time() - start) * 1000)


def get_consecutive_failures(db, agent_name):
    """Get the current consecutive failure count for an agent."""
    row = db.execute(
        "SELECT consecutive_failures FROM agent_health WHERE agent_name=? ORDER BY checked_at DESC LIMIT 1",
        (agent_name,)
    ).fetchone()
    return row[0] if row else 0


def send_alert(agent_name, status, failures):
    """Send email alert for agent failure."""
    subject = f"SENTINEL ALERT: {agent_name} DOWN ({failures} consecutive failures)"
    body = f"Agent {agent_name} has failed {failures} consecutive health checks. Last status: {status}. Time: {datetime.now().isoformat()}"
    try:
        subprocess.run(
            ["ssh", "agents@192.168.65.241",
             f"python3 ~/scripts/send-email.py sentinel@rize.bm artiedarrell@gmail.com '{subject}' '{body}'"],
            timeout=30, capture_output=True
        )
        print(f"  Alert sent for {agent_name}")
    except Exception as e:
        print(f"  Alert send failed: {e}")


def main():
    db = sqlite3.connect(DB_PATH)
    results = []

    for agent in AGENTS:
        status, ms = check_agent(agent)
        prev_failures = get_consecutive_failures(db, agent["name"])

        if status == "healthy":
            failures = 0
        else:
            failures = prev_failures + 1

        db.execute(
            "INSERT INTO agent_health (agent_name, endpoint, status, response_time_ms, consecutive_failures) VALUES (?,?,?,?,?)",
            (agent["name"], f"{agent['host']}:{agent['port']}", status, ms, failures)
        )

        if failures >= ALERT_THRESHOLD and prev_failures < ALERT_THRESHOLD:
            send_alert(agent["name"], status, failures)

        results.append(f"  {agent['name']:15s} {status:15s} {ms:5d}ms  failures={failures}")

    db.commit()

    # Cleanup: keep only 7 days of data
    db.execute("DELETE FROM agent_health WHERE checked_at < datetime('now', '-7 days')")
    db.commit()
    db.close()

    print(f"Agent Health Check — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
