"""
Unified Rize Monitor — Runs every 5 minutes
Handles: requirements refresh, service health, test results, issue tracking
Replaces multiple separate crontabs with one comprehensive check.
"""

import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# =====================================================
# CONFIG
# =====================================================

GITEA_URL = "http://localhost:3100"
GITEA_TOKEN = ""
TOKEN_FILE = os.path.expanduser("~/gitea-api-token.txt")
if os.path.exists(TOKEN_FILE):
    GITEA_TOKEN = open(TOKEN_FILE).read().strip()

CACHE_DIR = os.path.expanduser("~/homebase/cache")
LOG_DIR = os.path.expanduser("~/homebase/logs")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

TEAMS_WEBHOOK = os.environ.get("TEAMS_WEBHOOK", "")

PROJECTS = [
    {"name": "Helios", "slug": "helios", "repo": "rize/helios", "ssh": "demos@192.168.65.246", "path": "~/helios", "url": "https://helios.rize.bm", "port": 3005, "deadline": "2026-02-17"},
    {"name": "BPS AI", "slug": "bps-ai", "repo": "rize/bps-ai", "ssh": "demos@192.168.65.246", "path": "~/bps-ai", "url": "https://bpsai.rize.bm", "port": 3000, "deadline": "2026-02-20"},
    {"name": "Homebase", "slug": "homebase", "repo": "rize/homebase", "ssh": "rizeadmin@192.168.65.245", "path": "~/homebase", "url": "http://localhost:8000", "port": 8000, "deadline": None},
    {"name": "BEST Shipping", "slug": "best-shipping", "repo": "rize/best-shipping", "ssh": "demos@192.168.65.246", "path": "~/best-shipping-dashboard", "url": "https://bestshipping.rize.bm", "port": None, "deadline": None},
    {"name": "Premier EMR", "slug": "premier-emr", "repo": "rize/premier-emr", "ssh": "demos@192.168.65.246", "path": "~/premier-emr", "url": "https://premieremr.rize.bm", "port": None, "deadline": None},
    {"name": "Cortex", "slug": "cortex", "repo": "rize/cortex", "ssh": "agents@192.168.65.241", "path": "~/cortex", "url": "", "port": 9101, "deadline": None, "category": "agent"},
    {"name": "David Bishop", "slug": "david-bishop", "repo": "rize/david-bishop", "ssh": "agents@192.168.65.241", "path": "~/david-bishop", "url": "", "port": 18789, "deadline": None, "category": "agent"},
    {"name": "Apex", "slug": "apex", "repo": "rize/apex", "ssh": "agents@192.168.65.241", "path": "~/apex", "url": "", "port": 9004, "deadline": None, "category": "agent"},
    {"name": "Aegis", "slug": "aegis", "repo": "rize/aegis", "ssh": "agents@192.168.65.241", "path": "~/aegis", "url": "", "port": 9005, "deadline": None, "category": "agent"},
    {"name": "Talos", "slug": "talos", "repo": "rize/talos", "ssh": "talosadmin@192.168.65.237", "path": "~/talos-repo", "url": "https://talos.rize.bm", "port": None, "deadline": None, "category": "infrastructure"},
    {"name": "Vector", "slug": "vector", "repo": "rize/vector", "ssh": "betadmin@192.168.65.249", "path": "~/bet", "url": "", "port": None, "deadline": None, "category": "infrastructure"},
    {"name": "Sentinel", "slug": "sentinel", "repo": "rize/sentinel", "ssh": "agents@192.168.65.241", "path": "~/sentinel", "url": "", "port": 9006, "deadline": None, "category": "agent"},
]

SERVICES = {
    "Homebase": "http://localhost:8000",
    "Gitea": "http://localhost:3100",
}

# =====================================================
# HELPERS
# =====================================================

def log(msg, level="INFO"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    log_file = os.path.join(LOG_DIR, f"monitor-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log")
    with open(log_file, 'a') as f:
        f.write(line + "\n")

def gitea_get(path):
    try:
        req = urllib.request.Request(
            f"{GITEA_URL}/api/v1{path}",
            headers={"Authorization": f"token {GITEA_TOKEN}"} if GITEA_TOKEN else {}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        log(f"Gitea API error: {path} — {e}", "ERROR")
        return None

def ssh_cmd(target, cmd, timeout=10):
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no", target, cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

def send_alert(message, level="warning"):
    """Send alert to Teams webhook and/or log."""
    log(f"ALERT [{level}]: {message}", "ALERT")
    if TEAMS_WEBHOOK:
        try:
            icon = "⚠️" if level == "warning" else "🔴" if level == "critical" else "ℹ️"
            payload = json.dumps({"text": f"{icon} **Rize Monitor**: {message}"}).encode()
            req = urllib.request.Request(TEAMS_WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except:
            pass

# =====================================================
# CHECK 1: REQUIREMENTS REFRESH (every run = every 5 min)
# =====================================================

def refresh_requirements():
    """Fetch all project requirements from Gitea and cache."""
    log("Refreshing requirements from Gitea...")

    gitea_ok = gitea_get("/version") is not None
    projects_data = []

    for project in PROJECTS:
        try:
            if gitea_ok:
                # Fetch from Gitea API
                repo = project["repo"]
                all_issues = []
                page = 1
                while page <= 5:  # Max 5 pages
                    issues = gitea_get(f"/repos/{repo}/issues?state=all&limit=50&page={page}&type=issues")
                    if not issues:
                        break
                    all_issues.extend(issues)
                    if len(issues) < 50:
                        break
                    page += 1

                requirements = []
                for issue in all_issues:
                    labels = [l["name"] for l in issue.get("labels", [])]
                    priority = "P1"
                    for p in ["P0", "P1", "P2"]:
                        if p in labels:
                            priority = p
                            break

                    if issue["state"] == "closed":
                        status = "VERIFIED" if "playwright-verified" in labels else "DONE"
                    else:
                        status = "OPEN"

                    req_match = re.match(r'(REQ-\w+):', issue["title"])
                    req_id = req_match.group(1) if req_match else f"GH-{issue['number']}"
                    title = re.sub(r'^REQ-\w+:\s*', '', issue["title"])

                    requirements.append({
                        "id": req_id,
                        "gitea_number": issue["number"],
                        "status": status,
                        "description": title,
                        "priority": priority,
                        "labels": labels,
                        "gitea_url": issue.get("html_url", "")
                    })

                totals = {
                    "open": sum(1 for r in requirements if r["status"] == "OPEN"),
                    "done": sum(1 for r in requirements if r["status"] == "DONE"),
                    "verified": sum(1 for r in requirements if r["status"] == "VERIFIED"),
                    "blocked": sum(1 for r in requirements if r["status"] == "BLOCKED"),
                    "total": len(requirements)
                }
                completed = totals["done"] + totals["verified"]
                pct = round((completed / totals["total"]) * 100) if totals["total"] > 0 else 0

                p0 = [r for r in requirements if r["priority"] == "P0"]
                p0_open = sum(1 for r in p0 if r["status"] == "OPEN")

                days_left = None
                if project.get("deadline"):
                    dl = datetime.strptime(project["deadline"], "%Y-%m-%d").date()
                    days_left = (dl - datetime.now(timezone.utc).date()).days

                projects_data.append({
                    "name": project["name"],
                    "slug": project["slug"],
                    "url": project.get("url", ""),
                    "deadline": project.get("deadline"),
                    "days_remaining": days_left,
                    "totals": totals,
                    "percent_complete": pct,
                    "p0_status": {"open": p0_open, "total": len(p0)},
                    "requirements": sorted(requirements, key=lambda r: (
                        {"P0": 0, "P1": 1, "P2": 2}.get(r["priority"], 9),
                        {"OPEN": 0, "DONE": 3, "VERIFIED": 4}.get(r["status"], 9)
                    )),
                    "source": "gitea"
                })
            else:
                # Fallback: SSH parse REQUIREMENTS.md
                content = ssh_cmd(project["ssh"], f"cat {project['path']}/{project['slug'].upper().replace('-','_')}-REQUIREMENTS.md 2>/dev/null || cat {project['path']}/REQUIREMENTS.md 2>/dev/null")
                # Basic parse — count OPEN/DONE lines
                if content:
                    open_count = len(re.findall(r'\|\s*OPEN\s*\|', content))
                    done_count = len(re.findall(r'\|\s*DONE\s*\|', content))
                    total = open_count + done_count
                    pct = round((done_count / total) * 100) if total > 0 else 0
                    projects_data.append({
                        "name": project["name"], "slug": project["slug"],
                        "totals": {"open": open_count, "done": done_count, "total": total},
                        "percent_complete": pct,
                        "p0_status": {"open": open_count, "total": total},
                        "requirements": [],
                        "source": "ssh-fallback"
                    })

        except Exception as e:
            log(f"Error refreshing {project['name']}: {e}", "ERROR")

    result = {
        "projects": projects_data,
        "last_refresh": datetime.now(timezone.utc).isoformat(),
        "source": "gitea" if gitea_ok else "ssh-fallback",
        "project_count": len(projects_data),
        "total_requirements": sum(p.get("totals", {}).get("total", 0) for p in projects_data),
        "total_open": sum(p.get("totals", {}).get("open", 0) for p in projects_data)
    }

    with open(os.path.join(CACHE_DIR, "requirements.json"), 'w') as f:
        json.dump(result, f, indent=2)

    log(f"Requirements refreshed: {result['total_requirements']} total, {result['total_open']} open ({result['source']})")
    return result

# =====================================================
# CHECK 2: SERVICE HEALTH (every run = every 5 min)
# =====================================================

def check_services():
    """Check all service URLs respond."""
    log("Checking service health...")
    down = []

    for name, url in SERVICES.items():
        try:
            resp = urllib.request.urlopen(url, timeout=5)
            if resp.status >= 400:
                down.append(f"{name}: HTTP {resp.status}")
        except Exception as e:
            down.append(f"{name}: {e}")

    # Check project servers via SSH
    for server in [("Demos .246", "demos@192.168.65.246"), ("Talos .237", "talosadmin@192.168.65.237")]:
        result = ssh_cmd(server[1], "echo ok")
        if result != "ok":
            down.append(f"{server[0]}: SSH unreachable")

    if down:
        for d in down:
            send_alert(f"Service down: {d}", "critical")
    else:
        log("All services healthy")

    # Cache health status
    health = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "all_healthy": len(down) == 0,
        "down": down,
        "checked": list(SERVICES.keys()) + ["Demos .246", "Talos .237"]
    }
    with open(os.path.join(CACHE_DIR, "health.json"), 'w') as f:
        json.dump(health, f, indent=2)

    return down

# =====================================================
# CHECK 3: STALE P0 ISSUES (every run, alert threshold)
# =====================================================

def check_stale_p0():
    """Flag P0 issues open > 48 hours."""
    log("Checking for stale P0 issues...")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    stale = []

    for project in PROJECTS:
        issues = gitea_get(f"/repos/{project['repo']}/issues?state=open&labels=P0&limit=50") or []
        for issue in issues:
            try:
                created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
                if created < cutoff:
                    age_days = (datetime.now(timezone.utc) - created).days
                    stale.append({
                        "project": project["name"],
                        "issue": f"#{issue['number']}",
                        "title": issue["title"],
                        "age_days": age_days
                    })
            except:
                pass

    if stale:
        # Only alert once per 6 hours (check last alert time)
        alert_file = os.path.join(CACHE_DIR, "last_stale_alert.txt")
        should_alert = True
        if os.path.exists(alert_file):
            last = datetime.fromisoformat(open(alert_file).read().strip())
            if datetime.now(timezone.utc) - last < timedelta(hours=6):
                should_alert = False

        if should_alert:
            msg = f"{len(stale)} stale P0 issues (>48h): " + ", ".join(f"{s['project']} {s['issue']} ({s['age_days']}d)" for s in stale)
            send_alert(msg, "warning")
            with open(alert_file, 'w') as f:
                f.write(datetime.now(timezone.utc).isoformat())

    # Cache stale status
    with open(os.path.join(CACHE_DIR, "stale_p0.json"), 'w') as f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "stale": stale}, f, indent=2)

    log(f"Stale P0 check: {len(stale)} stale issues")
    return stale

# =====================================================
# CHECK 4: DEADLINE WARNINGS (every run, alert daily)
# =====================================================

def check_deadlines():
    """Warn about approaching deadlines with open P0s."""
    log("Checking deadlines...")
    today = datetime.now(timezone.utc).date()
    warnings = []

    for project in PROJECTS:
        if not project.get("deadline"):
            continue
        deadline = datetime.strptime(project["deadline"], "%Y-%m-%d").date()
        days_left = (deadline - today).days

        if days_left <= 7:
            issues = gitea_get(f"/repos/{project['repo']}/issues?state=open&labels=P0&limit=50") or []
            if issues:
                warnings.append({
                    "project": project["name"],
                    "deadline": project["deadline"],
                    "days_left": days_left,
                    "open_p0": len(issues)
                })

    if warnings:
        # Alert once daily
        alert_file = os.path.join(CACHE_DIR, "last_deadline_alert.txt")
        should_alert = True
        if os.path.exists(alert_file):
            last_date = open(alert_file).read().strip()
            if last_date == str(today):
                should_alert = False

        if should_alert:
            for w in warnings:
                urgency = "critical" if w["days_left"] <= 3 else "warning"
                send_alert(f"{w['project']}: {w['open_p0']} P0 open, deadline in {w['days_left']} days ({w['deadline']})", urgency)
            with open(alert_file, 'w') as f:
                f.write(str(today))

    with open(os.path.join(CACHE_DIR, "deadlines.json"), 'w') as f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "warnings": warnings}, f, indent=2)

    log(f"Deadline check: {len(warnings)} warnings")
    return warnings

# =====================================================
# CHECK 5: TEST RESULTS (every run)
# =====================================================

def refresh_test_results():
    """Read TEST-RESULTS.txt from each project."""
    log("Refreshing test results...")
    results = {}

    for project in PROJECTS:
        content = ssh_cmd(project["ssh"], f"cat {project['path']}/TEST-RESULTS.txt 2>/dev/null")
        if content:
            pass_match = re.search(r'(\d+)\s+passed', content)
            fail_match = re.search(r'(\d+)\s+failed', content)
            passed = int(pass_match.group(1)) if pass_match else 0
            failed = int(fail_match.group(1)) if fail_match else 0

            # Check for regression vs last cached result
            prev_file = os.path.join(CACHE_DIR, f"tests_{project['slug']}.json")
            prev_passed = 0
            if os.path.exists(prev_file):
                try:
                    prev = json.load(open(prev_file))
                    prev_passed = prev.get("passed", 0)
                except:
                    pass

            if prev_passed > 0 and passed < prev_passed:
                send_alert(f"REGRESSION: {project['name']} tests dropped from {prev_passed} to {passed} passed", "critical")

            results[project["slug"]] = {"passed": passed, "failed": failed, "total": passed + failed}

            with open(prev_file, 'w') as f:
                json.dump(results[project["slug"]], f)

    with open(os.path.join(CACHE_DIR, "test_results.json"), 'w') as f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)

    log(f"Test results refreshed for {len(results)} projects")
    return results

# =====================================================
# MAIN — RUN ALL CHECKS
# =====================================================



# =====================================================



# =====================================================
# CHECK 6: SENTINEL DATA CACHE
# =====================================================

def refresh_sentinel_cache():
    """Pre-cache sentinel data so the page loads instantly."""
    log("Refreshing Sentinel cache...")
    
    sentinel_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": [],
        "audit_log": [],
        "oversight_mode": "active",
        "guardrails": {"status": "enabled", "violations_24h": 0}
    }
    
    # Agent heartbeat status  
    agent_configs = [
        {"name": "David Bishop", "server": "agents@192.168.65.241", "port": 18789},
        {"name": "Cortex", "server": "agents@192.168.65.241", "port": 9101},
        {"name": "Apex", "server": "agents@192.168.65.241", "port": 9004},
        {"name": "Aegis", "server": "agents@192.168.65.241", "port": 9005},
        {"name": "Sentinel", "server": "agents@192.168.65.241", "port": 9006},
        {"name": "Homebase", "server": "rizeadmin@192.168.65.245", "port": 8000},
    ]
    
    for agent in agent_configs:
        check_cmd = f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{agent['port']}/ 2>/dev/null || echo 000"
        result = ssh_cmd(agent["server"], check_cmd)
        status = "active" if result and result.strip() in ["200", "302", "401"] else "unknown"
        sentinel_data["agents"].append({
            "name": agent["name"],
            "server": agent["server"].split("@")[1] if "@" in agent["server"] else agent["server"],
            "port": agent["port"],
            "status": status,
            "last_check": datetime.now(timezone.utc).isoformat()
        })
    
    # Recent audit entries from log
    log_today = os.path.join(LOG_DIR, f"monitor-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log")
    if os.path.exists(log_today):
        with open(log_today) as f:
            lines = f.readlines()[-50:]
            sentinel_data["audit_log"] = [l.strip() for l in lines if l.strip()]
    
    with open(os.path.join(CACHE_DIR, "sentinel.json"), 'w') as f:
        json.dump(sentinel_data, f, indent=2)
    
    log(f"Sentinel cache refreshed: {len(sentinel_data['agents'])} agents tracked")
    return sentinel_data


if __name__ == "__main__":
    log("========== MONITOR RUN START ==========")

    refresh_requirements()
    check_services()
    check_stale_p0()
    check_deadlines()
    refresh_test_results()
    refresh_sentinel_cache()

    log("========== MONITOR RUN COMPLETE ==========")
