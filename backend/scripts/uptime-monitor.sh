#!/bin/bash
cd "$(dirname "$0")/../.."

python3 << 'PYEOF'
import sqlite3
import subprocess
import re
from datetime import datetime, timedelta

DB = "data/uptime.db"
TIMESTAMP = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

db = sqlite3.connect(DB)

# ACTIVE SERVERS ONLY (as of 2026-02-06)
SERVERS = [
    ("237", "talos"),
    ("241", "agents"),
    ("245", "rize-apps"),
    ("246", "demos"),
    ("249", "vector"),
    ("253", "hyper-v")
]

for octet, sid in SERVERS:
    ip = f"192.168.65.{octet}"
    try:
        result = subprocess.run(["ping", "-c", "1", "-W", "2", ip], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            match = re.search(r'time=([0-9.]+)', result.stdout)
            latency = float(match.group(1)) if match else None
            db.execute("INSERT INTO server_pings(server_id,timestamp,reachable,latency_ms) VALUES(?,?,1,?)",
                       (sid, TIMESTAMP, latency))
        else:
            db.execute("INSERT INTO server_pings(server_id,timestamp,reachable,latency_ms) VALUES(?,?,0,NULL)",
                       (sid, TIMESTAMP))
    except:
        db.execute("INSERT INTO server_pings(server_id,timestamp,reachable,latency_ms) VALUES(?,?,0,NULL)",
                   (sid, TIMESTAMP))

# ACTIVE PROJECTS - HTTP checks
PROJECTS = [
    ("homebase", "http://localhost:8000"),
    ("property-rize", "http://localhost:8501"),
    ("nexus", "http://localhost:3002"),
    ("dockyard", "http://localhost:8080"),
    ("relay", "http://localhost:8888"),
    ("openhands", "http://localhost:3000"),
]

# Remote project checks (via curl from this server)
REMOTE_PROJECTS = [
    ("bps-ai", "http://192.168.65.246:3000"),
    ("bestshipping", "http://192.168.65.246:3001"),
    ("premier-emr", "http://192.168.65.246:3004"),
    ("helios", "http://192.168.65.246:3005"),
]

# SSH-based checks for internal-only projects
SSH_PROJECTS = [
    ("david", "agents@192.168.65.241", "http://localhost:7070"),
    ("vector", "betadmin@192.168.65.249", "http://localhost:8000")
]

for pid, url in PROJECTS + REMOTE_PROJECTS:
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}:%{time_total}", "--max-time", "5", url],
            capture_output=True, text=True, timeout=10
        )
        parts = result.stdout.strip().split(":")
        code = int(parts[0]) if parts[0].isdigit() else 0
        time_ms = float(parts[1]) * 1000 if len(parts) > 1 else None
        is_up = 1 if 200 <= code < 500 else 0
        db.execute("INSERT INTO project_checks(project_id,timestamp,http_code,response_ms,is_up) VALUES(?,?,?,?,?)",
                   (pid, TIMESTAMP, code, time_ms, is_up))
    except Exception as e:
        db.execute("INSERT INTO project_checks(project_id,timestamp,http_code,response_ms,is_up) VALUES(?,?,0,NULL,0)",
                   (pid, TIMESTAMP))

# SSH-based checks for internal-only projects
for pid, ssh_host, url in SSH_PROJECTS:
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no", ssh_host,
             f"curl -s -o /dev/null -w %{{http_code}}:%{{time_total}} --max-time 5 {url}"],
            capture_output=True, text=True, timeout=15
        )
        parts = result.stdout.strip().split(":")
        code = int(parts[0]) if parts[0].isdigit() else 0
        time_ms = float(parts[1]) * 1000 if len(parts) > 1 else None
        is_up = 1 if 200 <= code < 500 else 0
        db.execute("INSERT INTO project_checks(project_id,timestamp,http_code,response_ms,is_up) VALUES(?,?,?,?,?)",
                   (pid, TIMESTAMP, code, time_ms, is_up))
    except Exception as e:
        db.execute("INSERT INTO project_checks(project_id,timestamp,http_code,response_ms,is_up) VALUES(?,?,0,NULL,0)",
                   (pid, TIMESTAMP))

# Prune old data (keep 7 days)
cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
db.execute("DELETE FROM server_pings WHERE timestamp < ?", (cutoff,))
db.execute("DELETE FROM project_checks WHERE timestamp < ?", (cutoff,))

db.commit()
db.close()
print("Uptime check complete")
PYEOF
