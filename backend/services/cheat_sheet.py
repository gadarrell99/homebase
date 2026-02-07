import json, sqlite3, subprocess, os
from datetime import datetime

BASE = os.path.join(os.path.dirname(__file__), '..', '..')

def load_json(path, default=None):
    try:
        with open(os.path.join(BASE, path)) as f: return json.load(f)
    except: return default or {}

def generate_cheat_sheet():
    now = datetime.utcnow().isoformat() + "Z"
    sdata = load_json("data/servers.json", {"servers": []})
    servers = sdata.get("servers", sdata if isinstance(sdata, list) else [])
    pdata = load_json("data/projects.json", {"projects": []})
    projects = pdata.get("projects", pdata if isinstance(pdata, list) else [])
    scans = load_json("data/security-scans.json")
    alerts_data = load_json("data/alerts.json", {"alerts": []})
    active_alerts = [a for a in alerts_data.get("alerts", []) if not a.get("acknowledged")]
    audit = load_json("data/audit-fixes.json", {"items": []})
    open_items = [i for i in audit.get("items", []) if i.get("status") == "open"]
    agents = []
    db_path = os.path.join(BASE, "data", "agents.db")
    if os.path.exists(db_path):
        try:
            db = sqlite3.connect(db_path); db.row_factory = sqlite3.Row
            agents = [dict(r) for r in db.execute("SELECT * FROM agents")]
            db.close()
        except: pass
    try: crons = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5).stdout.strip()
    except: crons = "unavailable"
    return {
        "generated": now,
        "sections": {
            "servers": [{"id":s.get("id"),"name":s.get("name"),"ip":s.get("ip"),"user":s.get("user"),"ssh_url":s.get("ssh_url"),"projects":[p.get("name") for p in s.get("projects",[])]} for s in servers],
            "projects": [{"id":p.get("id"),"name":p.get("name"),"version":p.get("version"),"status":p.get("status"),"server_id":p.get("server_id"),"last_git":(p.get("backup") or {}).get("last_git_commit")} for p in projects],
            "agents": agents,
            "security_score": scans.get("overall_score"),
            "active_alerts": len(active_alerts),
            "open_audit_items": len(open_items),
            "crons": crons,
            "deadlines": [
                {"what":"BPS Demo","when":"Early February (OVERDUE)","severity":"critical"},
                {"what":"Hardware RFP","when":"February 20","severity":"warning"},
                {"what":"Dockyard WiFi Launch","when":"February 28","severity":"warning"},
            ],
            "waiting_on": ["Martin — Authorize.net","Abraham — Ubiquiti","Angel — Email templates"],
        }
    }
