import json
from services import sentinel
import os
import sqlite3
from datetime import datetime, timedelta

BASE = os.path.join(os.path.dirname(__file__), '..', '..')
ALERTS_FILE = os.path.join(BASE, 'data', 'alerts.json')
UPTIME_DB = os.path.join(BASE, 'data', 'uptime.db')
AGENTS_DB = os.path.join(BASE, 'data', 'agents.db')
SECURITY_FILE = os.path.join(BASE, 'data', 'security-scans.json')

def load_alerts():
    try:
        with open(ALERTS_FILE) as f:
            return json.load(f)
    except:
        return {"alerts": [], "settings": {"cooldown_minutes": 30, "thresholds": {}}, "cooldowns": {}}

def save_alerts(data):
    with open(ALERTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def sanitize_msg(msg):
    """Ensure alert messages are never None/undefined"""
    if not msg or not isinstance(msg, str):
        return "Unknown alert condition"
    return msg.replace('"', "'")

def gen_alert_id():
    now = datetime.utcnow()
    return f"ALT-{now.strftime('%Y')}-{now.strftime('%m%d%H%M%S')}"

def is_cooled_down(data, source, target):
    key = f"{source}:{target}"
    cooldowns = data.get("cooldowns", {})
    if key in cooldowns:
        last = datetime.fromisoformat(cooldowns[key])
        minutes = data["settings"].get("cooldown_minutes", 30)
        if datetime.utcnow() - last < timedelta(minutes=minutes):
            return True
    return False

def set_cooldown(data, source, target):
    key = f"{source}:{target}"
    if "cooldowns" not in data:
        data["cooldowns"] = {}
    data["cooldowns"][key] = datetime.utcnow().isoformat()

def add_alert(data, severity, source, target, message):
    if is_cooled_down(data, source, target):
        return False
    alert = {
        "id": gen_alert_id(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "severity": severity,
        "source": source,
        "target": target,
        "message": message,
        "acknowledged": False,
        "notified": False
    }
    data["alerts"].insert(0, alert)
    data["alerts"] = data["alerts"][:500]
    set_cooldown(data, source, target)
    return True

def check_server_uptime(data):
    thresh = data["settings"].get("thresholds", {}).get("server_down_pings", 3)
    if not os.path.exists(UPTIME_DB):
        return
    db = sqlite3.connect(UPTIME_DB)
    servers = [r[0] for r in db.execute("SELECT DISTINCT server_id FROM server_pings").fetchall()]
    for sid in servers:
        recent = db.execute(
            "SELECT reachable FROM server_pings WHERE server_id=? ORDER BY timestamp DESC LIMIT ?",
            (sid, thresh)
        ).fetchall()
        if len(recent) >= thresh and all(not r[0] for r in recent):
            add_alert(data, "critical", "server", sid, sanitize_msg(f"Server {sid} unreachable for {thresh} consecutive pings"))
    db.close()

def check_project_uptime(data):
    thresh_ms = data["settings"].get("thresholds", {}).get("response_warn_ms", 5000)
    if not os.path.exists(UPTIME_DB):
        return
    db = sqlite3.connect(UPTIME_DB)
    projects = [r[0] for r in db.execute("SELECT DISTINCT project_id FROM project_checks").fetchall()]
    for pid in projects:
        recent = db.execute(
            "SELECT is_up, response_ms FROM project_checks WHERE project_id=? ORDER BY timestamp DESC LIMIT 3",
            (pid,)
        ).fetchall()
        if len(recent) >= 3 and all(not r[0] for r in recent):
            add_alert(data, "critical", "project", pid, sanitize_msg(f"Project {pid} down for 3 consecutive checks"))
        elif recent and recent[0][1] and recent[0][1] > thresh_ms:
            add_alert(data, "warning", "project", pid, sanitize_msg(f"Project {pid} response time {int(recent[0][1])}ms (>{thresh_ms}ms)"))
    db.close()

def check_agent_heartbeats(data):
    warn_min = data["settings"].get("thresholds", {}).get("heartbeat_warn_min", 10)
    crit_min = data["settings"].get("thresholds", {}).get("heartbeat_crit_min", 30)
    if not os.path.exists(AGENTS_DB):
        return
    db = sqlite3.connect(AGENTS_DB)
    db.row_factory = sqlite3.Row
    agents = db.execute("SELECT agent_id, display_name, updated_at, agent_type FROM agents").fetchall()
    now = datetime.utcnow()
    for a in agents:
        # Skip oversight agents (they do not send heartbeats)
        if a["agent_type"] == "oversight":
            continue
        if not a["updated_at"]:
            continue
        try:
            last = datetime.fromisoformat(a["updated_at"].replace("Z", ""))
            mins = (now - last).total_seconds() / 60
            if mins > crit_min:
                add_alert(data, "critical", "agent", a["agent_id"],
                         f"Agent {a['display_name']} no heartbeat for {int(mins)} min")
            elif mins > warn_min:
                add_alert(data, "warning", "agent", a["agent_id"],
                         f"Agent {a['display_name']} heartbeat stale ({int(mins)} min)")
        except:
            pass
    db.close()

def check_security_scores(data):
    if not os.path.exists(SECURITY_FILE):
        return
    try:
        with open(SECURITY_FILE) as f:
            scans = json.load(f)
        for sid, sdata in scans.get("servers", {}).items():
            score = sdata.get("score", 100)
            if score < 50:
                add_alert(data, "critical", "security", sid, sanitize_msg(f"Server {sid} security score critically low: {score}"))
            elif score < 70:
                add_alert(data, "warning", "security", sid, sanitize_msg(f"Server {sid} security score below threshold: {score}"))
    except:
        pass

def check_all():
    # Skip alerting during maintenance window
    if sentinel.is_maintenance_active():
        return {"checked": False, "skipped": "maintenance_window"}
    data = load_alerts()
    check_server_uptime(data)
    check_project_uptime(data)
    check_agent_heartbeats(data)
    check_security_scores(data)
    save_alerts(data)

    new_alerts = [a for a in data["alerts"] if not a.get("notified")]
    if new_alerts:
        critical = [a for a in new_alerts if a["severity"] == "critical"]
        if critical and data["settings"].get("email_enabled"):
            try:
                send_alert_email(critical, data["settings"].get("email_to", ""))
            except Exception as e:
                print(f"Email send failed: {e}")
        for a in new_alerts:
            a["notified"] = True
        save_alerts(data)

    return {"checked": True, "new_alerts": len(new_alerts)}

def send_alert_email(alerts, to_email):
    if not to_email: return
    try:
        from services.email_alerts import send_email
        subject = f"[HOMEBASE] 🔴 {len(alerts)} Critical Alert(s)"
        body = "Homebase Alert Summary\n\n" + "".join(f"• [{a['severity'].upper()}] {a['message']}\n" for a in alerts)
        send_email(to_email, subject, body + "\nhttps://homebase.rize.bm/security")
    except: pass

def get_alerts(severity=None, acknowledged=None, limit=100):
    alerts = load_alerts()["alerts"]
    if severity: alerts = [a for a in alerts if a["severity"] == severity]
    if acknowledged is not None: alerts = [a for a in alerts if a["acknowledged"] == acknowledged]
    return alerts[:limit]

def acknowledge_alert(alert_id):
    data = load_alerts()
    for a in data["alerts"]:
        if a["id"] == alert_id:
            a["acknowledged"] = True; save_alerts(data); return True
    return False

def get_alert_settings(): return load_alerts()["settings"]

def update_alert_settings(new_settings):
    data = load_alerts(); data["settings"].update(new_settings); save_alerts(data); return data["settings"]
