import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'uptime.db')

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def get_server_uptime(server_id=None, hours=24):
    db = get_db()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    if server_id:
        rows = db.execute(
            "SELECT server_id, reachable, latency_ms FROM server_pings WHERE server_id=? AND timestamp>?",
            (server_id, cutoff)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT server_id, reachable, latency_ms FROM server_pings WHERE timestamp>?",
            (cutoff,)
        ).fetchall()
    db.close()

    servers = {}
    for r in rows:
        sid = r["server_id"]
        if sid not in servers:
            servers[sid] = {"total": 0, "up": 0, "latencies": []}
        servers[sid]["total"] += 1
        if r["reachable"]:
            servers[sid]["up"] += 1
            if r["latency_ms"] is not None:
                servers[sid]["latencies"].append(r["latency_ms"])

    result = {}
    for sid, data in servers.items():
        total = data["total"]
        up = data["up"]
        lats = data["latencies"]
        result[sid] = {
            "uptime_pct": round((up / total) * 100, 2) if total > 0 else None,
            "total_pings": total,
            "up_pings": up,
            "avg_latency_ms": round(sum(lats) / len(lats), 1) if lats else None
        }
    return result

def get_project_uptime(project_id=None, hours=24):
    db = get_db()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    if project_id:
        rows = db.execute(
            "SELECT project_id, http_code, response_ms, is_up FROM project_checks WHERE project_id=? AND timestamp>?",
            (project_id, cutoff)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT project_id, http_code, response_ms, is_up FROM project_checks WHERE timestamp>?",
            (cutoff,)
        ).fetchall()
    db.close()

    projects = {}
    for r in rows:
        pid = r["project_id"]
        if pid not in projects:
            projects[pid] = {"total": 0, "up": 0, "response_times": []}
        projects[pid]["total"] += 1
        if r["is_up"]:
            projects[pid]["up"] += 1
        if r["response_ms"] is not None:
            projects[pid]["response_times"].append(r["response_ms"])

    result = {}
    for pid, data in projects.items():
        total = data["total"]
        up = data["up"]
        rts = data["response_times"]
        result[pid] = {
            "uptime_pct": round((up / total) * 100, 2) if total > 0 else None,
            "total_checks": total,
            "up_checks": up,
            "avg_response_ms": round(sum(rts) / len(rts), 1) if rts else None
        }
    return result

def get_ping_history(server_id, hours=24):
    db = get_db()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    rows = db.execute(
        "SELECT timestamp, reachable, latency_ms FROM server_pings WHERE server_id=? AND timestamp>? ORDER BY timestamp",
        (server_id, cutoff)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

def get_check_history(project_id, hours=24):
    db = get_db()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    rows = db.execute(
        "SELECT timestamp, http_code, response_ms, is_up FROM project_checks WHERE project_id=? AND timestamp>? ORDER BY timestamp",
        (project_id, cutoff)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]
