#!/bin/bash
# Generates a comprehensive, always-current cheat sheet
cd "$(dirname "$0")/../.."
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
OUTFILE="data/cheat-sheet-full.json"
SSH_OPTS="-o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no"

# Server definitions
declare -A SRV_IP SRV_USER SRV_PATH SRV_SSH
SRV_IP[helios]="192.168.65.240";       SRV_USER[helios]="heliosdev";       SRV_PATH[helios]="~/helios-ai";                SRV_SSH[helios]="https://helios-ssh.rize.bm"
SRV_IP[david]="192.168.65.241";        SRV_USER[david]="david";            SRV_PATH[david]="~/.openclaw";                 SRV_SSH[david]=""
SRV_IP[cobalt]="192.168.65.243";       SRV_USER[cobalt]="cobaltadmin";     SRV_PATH[cobalt]="~/homebase";                 SRV_SSH[cobalt]="https://cobalt-ssh.rize.bm"
SRV_IP[claude-dev]="192.168.65.245";   SRV_USER[claude-dev]="claudedevadmin"; SRV_PATH[claude-dev]="~";                   SRV_SSH[claude-dev]="https://claude-dev-ssh.rize.bm"
SRV_IP[demos]="192.168.65.246";       SRV_USER[demos]="demos";      SRV_PATH[demos]="~/demos";                  SRV_SSH[demos]="https://bpsai-ssh.rize.bm"
SRV_IP[nexus]="192.168.65.247";        SRV_USER[nexus]="nexusadmin";       SRV_PATH[nexus]="~/nexus";                     SRV_SSH[nexus]="https://nexus-ssh.rize.bm"
SRV_IP[relay]="192.168.65.248";        SRV_USER[relay]="relayadmin";       SRV_PATH[relay]="~/relay";                     SRV_SSH[relay]="https://relay-ssh.rize.bm"
SRV_IP[vector]="192.168.65.249";       SRV_USER[vector]="betadmin";        SRV_PATH[vector]="~/bet";                      SRV_SSH[vector]="https://vector-ssh.rize.bm"
SRV_IP[premier-emr]="192.168.65.239";  SRV_USER[premier-emr]="emradmin";   SRV_PATH[premier-emr]="~/premier-emr";         SRV_SSH[premier-emr]="https://emr-ssh.rize.bm"
SRV_IP[dockyard]="192.168.65.252";     SRV_USER[dockyard]="dockyardadmin"; SRV_PATH[dockyard]="~/dockyard-wifi-portal";    SRV_SSH[dockyard]="https://dockyard-ssh.rize.bm"
SRV_IP[hyper-v]="192.168.65.253";      SRV_USER[hyper-v]="Administrator";  SRV_PATH[hyper-v]="";                          SRV_SSH[hyper-v]=""

# Build servers array in Python directly to avoid JSON escaping issues
python3 << PYEOF
import subprocess, json, os

servers = []
srv_defs = [
    ("helios", "192.168.65.240", "heliosdev", "~/helios-ai", "https://helios-ssh.rize.bm"),
    ("david", "192.168.65.241", "david", "~/.openclaw", ""),
    ("cobalt", "192.168.65.243", "cobaltadmin", "~/homebase", "https://cobalt-ssh.rize.bm"),
    ("claude-dev", "192.168.65.245", "claudedevadmin", "~", "https://claude-dev-ssh.rize.bm"),
    ("demos", "192.168.65.246", "demos", "~/demos", "https://bpsai-ssh.rize.bm"),
    ("nexus", "192.168.65.247", "nexusadmin", "~/nexus", "https://nexus-ssh.rize.bm"),
    ("relay", "192.168.65.248", "relayadmin", "~/relay", "https://relay-ssh.rize.bm"),
    ("vector", "192.168.65.249", "betadmin", "~/bet", "https://vector-ssh.rize.bm"),
    ("premier-emr", "192.168.65.239", "emradmin", "~/premier-emr", "https://emr-ssh.rize.bm"),
    ("dockyard", "192.168.65.252", "dockyardadmin", "~/dockyard-wifi-portal", "https://dockyard-ssh.rize.bm"),
    ("hyper-v", "192.168.65.253", "Administrator", "", ""),
]

SSH_OPTS = "-o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no"

def ssh_cmd(host, cmd):
    try:
        r = subprocess.run(f"ssh {SSH_OPTS} {host} '{cmd}'", shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip().replace('\n', ' ').replace('"', "'")[:100]
    except:
        return ""

def ping(ip):
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", "2", ip], capture_output=True, timeout=5)
        return r.returncode == 0
    except:
        return False

for sid, ip, user, path, ssh_url in srv_defs:
    alive = ping(ip)
    version = uptime = disk = mem = services = ""
    if alive and sid != "hyper-v" and path:
        host = f"{user}@{ip}"
        version = ssh_cmd(host, f"cd {path} && git describe --tags --abbrev=0 2>/dev/null")
        uptime = ssh_cmd(host, "uptime -p 2>/dev/null")
        disk = ssh_cmd(host, "df / | awk 'NR==2{print $5}'")
        mem = ssh_cmd(host, "free -m | awk 'NR==2{printf \"%d/%dMB\",$3,$2}'")
        services = ssh_cmd(host, "pm2 list 2>/dev/null | grep -c online || echo 0")
    servers.append({
        "id": sid, "ip": ip, "user": user, "path": path, "ssh_url": ssh_url,
        "alive": alive, "version": version, "uptime": uptime, "disk": disk, "memory": mem, "services": services
    })

# Web apps
web_apps = []
apps = [
    ("homebase", "http://localhost:8000"),
    ("bpsai", "http://192.168.65.246:3000"),
    ("nexus", "http://192.168.65.247:3000"),
    ("relay", "http://192.168.65.248:8000"),
    ("vector", "http://192.168.65.249:3000"),
    ("dockyard", "http://192.168.65.252:3000"),
    ("david", "http://192.168.65.241:5000"),
    ("helios", "http://192.168.65.240:3800"),
    ("premier-emr", "http://192.168.65.239:3000"),
]
for name, url in apps:
    try:
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "5", url], capture_output=True, text=True, timeout=10)
        code = int(r.stdout.strip() or 0)
    except:
        code = 0
    status = "up" if 200 <= code < 500 else "down"
    web_apps.append({"name": name, "url": url, "http_code": code, "status": status})

# Cobalt crons
try:
    r = subprocess.run("crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$'", shell=True, capture_output=True, text=True)
    crons = [l.strip() for l in r.stdout.strip().split('\n') if l.strip()]
except:
    crons = []

# Status from local files
try:
    with open("data/alerts.json") as f:
        alerts = json.load(f)
    alert_count = sum(1 for a in alerts.get("alerts", []) if not a.get("acknowledged"))
except:
    alert_count = 0

try:
    with open("data/security-scans.json") as f:
        sec = json.load(f)
    sec_score = sec.get("overall_score", "?")
except:
    sec_score = "?"

try:
    with open("data/audit-fixes.json") as f:
        audit = json.load(f)
    audit_open = sum(1 for i in audit.get("items", []) if i.get("status") == "open")
except:
    audit_open = 0

sheet = {
    "generated": "$TIMESTAMP",
    "servers": servers,
    "web_apps": web_apps,
    "status": {
        "security_score": sec_score,
        "active_alerts": alert_count,
        "open_audit_items": audit_open
    },
    "deadlines": [
        {"item": "BPS Demo", "date": "Early February (OVERDUE)", "severity": "critical"},
        {"item": "Infrastructure Hardware RFP", "date": "February 20, 2026", "severity": "warning"},
        {"item": "Dockyard WiFi Launch", "date": "February 28, 2026", "severity": "warning"}
    ],
    "waiting_on": [
        "Martin — Authorize.net (Dockyard payments)",
        "Abraham — Ubiquiti (Dockyard network)",
        "Angel — Email templates (Dockyard)"
    ],
    "cobalt_crons": crons
}

with open("$OUTFILE", "w") as f:
    json.dump(sheet, f, indent=2)

alive_count = sum(1 for s in servers if s["alive"])
up_count = sum(1 for a in web_apps if a["status"] == "up")
print(f"  Cheat sheet generated: {alive_count}/{len(servers)} servers alive, {up_count}/{len(web_apps)} apps up")
PYEOF
