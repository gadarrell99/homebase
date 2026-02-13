"""
Homebase Requirements API v2 — Gitea-Powered
Reads issues from Gitea API instead of SSH-parsing REQUIREMENTS.md files.
Falls back to SSH parsing if Gitea is unavailable.

Replace requirements_api.py on .245 with this after Gitea is deployed.
"""

import json
import re
import subprocess
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# =====================================================
# CONFIGURATION
# =====================================================

GITEA_URL = os.environ.get("GITEA_URL", "http://localhost:3100")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")

# Try to load token from file
TOKEN_FILE = os.path.expanduser("~/gitea-api-token.txt")
if os.path.exists(TOKEN_FILE):
    GITEA_TOKEN = open(TOKEN_FILE).read().strip()

CACHE_FILE = os.path.expanduser("~/homebase/cache/requirements.json")

# Project registry
PROJECTS = [
    {
        "name": "Helios",
        "slug": "helios",
        "gitea_repo": "rize/helios",
        "ssh": "demos@192.168.65.246",
        "path": "~/helios",
        "requirements_file": "HELIOS-REQUIREMENTS.md",
        "deadline": "2026-02-17",
        "url": "https://helios.rize.bm",
        "port": 3005
    },
    {
        "name": "BPS AI",
        "slug": "bps-ai",
        "gitea_repo": "rize/bps-ai",
        "ssh": "demos@192.168.65.246",
        "path": "~/bps-ai",
        "requirements_file": "BPS-AI-REQUIREMENTS.md",
        "deadline": "2026-02-20",
        "url": "https://bpsai.rize.bm",
        "port": 3000
    },
    {
        "name": "Homebase",
        "slug": "homebase",
        "gitea_repo": "rize/homebase",
        "ssh": "rizeadmin@192.168.65.245",
        "path": "~/homebase",
        "requirements_file": "HOMEBASE-REQUIREMENTS.md",
        "deadline": None,
        "url": "https://homebase.rize.bm",
        "port": 8000
    },
    {
        "name": "BEST Shipping",
        "slug": "best-shipping",
        "gitea_repo": "rize/best-shipping",
        "ssh": "demos@192.168.65.246",
        "path": "~/best-shipping-dashboard",
        "requirements_file": "BEST-SHIPPING-REQUIREMENTS.md",
        "deadline": None,
        "url": "https://bestshipping.rize.bm",
        "port": 3001
    },
    {
        "name": "Premier EMR",
        "slug": "premier-emr",
        "gitea_repo": "rize/premier-emr",
        "ssh": "demos@192.168.65.246",
        "path": "~/premier-emr",
        "requirements_file": "PREMIER-EMR-REQUIREMENTS.md",
        "deadline": None,
        "url": "https://premieremr.rize.bm",
        "port": 3004
    }
]


# =====================================================
# GITEA API CLIENT
# =====================================================

def gitea_get(path, timeout=10):
    """GET request to Gitea API."""
    try:
        req = urllib.request.Request(
            f"{GITEA_URL}/api/v1{path}",
            headers={"Authorization": f"token {GITEA_TOKEN}"} if GITEA_TOKEN else {}
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except (urllib.error.URLError, Exception) as e:
        print(f"Gitea API error: {path} — {e}")
        return None


def gitea_available():
    """Check if Gitea is reachable."""
    result = gitea_get("/version")
    return result is not None


# =====================================================
# FETCH FROM GITEA
# =====================================================

def fetch_project_from_gitea(project):
    """Fetch project data from Gitea issues API."""
    repo = project["gitea_repo"]

    # Fetch all issues (open + closed) with pagination
    all_issues = []
    page = 1
    while True:
        issues = gitea_get(f"/repos/{repo}/issues?state=all&limit=50&page={page}&type=issues")
        if not issues:
            break
        all_issues.extend(issues)
        if len(issues) < 50:
            break
        page += 1

    # Parse into requirements format
    requirements = []
    for issue in all_issues:
        # Determine priority from labels
        priority = "P1"  # default
        labels = [l["name"] for l in issue.get("labels", [])]
        for p in ["P0", "P1", "P2"]:
            if p in labels:
                priority = p
                break

        # Map Gitea state to requirement status
        if issue["state"] == "closed":
            status = "DONE"
            # Check if it has "verified" label
            if "playwright-verified" in labels:
                status = "VERIFIED"
        elif "blocked" in [l["name"].lower() for l in issue.get("labels", [])]:
            status = "BLOCKED"
        else:
            status = "OPEN"

        # Extract REQ ID from title if present
        req_id_match = re.match(r'(REQ-\w+):', issue["title"])
        req_id = req_id_match.group(1) if req_id_match else f"GH-{issue['number']}"

        # Clean title (remove REQ-XXX: prefix)
        title = re.sub(r'^REQ-\w+:\s*', '', issue["title"])

        requirements.append({
            "id": req_id,
            "gitea_number": issue["number"],
            "status": status,
            "description": title,
            "priority": priority,
            "labels": labels,
            "created": issue.get("created_at"),
            "updated": issue.get("updated_at"),
            "gitea_url": issue.get("html_url", "")
        })

    # Compute totals
    totals = {
        "open": sum(1 for r in requirements if r["status"] == "OPEN"),
        "done": sum(1 for r in requirements if r["status"] == "DONE"),
        "verified": sum(1 for r in requirements if r["status"] == "VERIFIED"),
        "blocked": sum(1 for r in requirements if r["status"] == "BLOCKED"),
        "in_progress": sum(1 for r in requirements if r["status"] == "IN_PROGRESS"),
        "total": len(requirements)
    }

    completed = totals["done"] + totals["verified"]
    percent = round((completed / totals["total"]) * 100) if totals["total"] > 0 else 0

    p0_reqs = [r for r in requirements if r["priority"] == "P0"]
    p0_open = sum(1 for r in p0_reqs if r["status"] == "OPEN")

    # Deadline
    days_remaining = None
    if project.get("deadline"):
        deadline_date = datetime.strptime(project["deadline"], "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        days_remaining = (deadline_date - today).days

    # Milestones (from Gitea)
    milestones = gitea_get(f"/repos/{repo}/milestones?state=open") or []

    return {
        "name": project["name"],
        "slug": project["slug"],
        "server": project["ssh"].split("@")[1] if "@" in project["ssh"] else "",
        "deadline": project.get("deadline"),
        "days_remaining": days_remaining,
        "url": project.get("url", ""),
        "port": project.get("port"),
        "gitea_repo": repo,
        "gitea_url": f"{GITEA_URL}/{repo}",
        "totals": totals,
        "percent_complete": percent,
        "p0_status": {"open": p0_open, "total": len(p0_reqs)},
        "requirements": sorted(requirements, key=lambda r: (
            {"P0": 0, "P1": 1, "P2": 2}.get(r["priority"], 9),
            {"OPEN": 0, "IN_PROGRESS": 1, "BLOCKED": 2, "DONE": 3, "VERIFIED": 4}.get(r["status"], 9)
        )),
        "milestones": [{"title": m["title"], "due": m.get("due_on"), "open": m.get("open_issues", 0)} for m in milestones],
        "test_summary": None,  # TODO: read from CI results
        "last_test_run": None,
        "source": "gitea"
    }


# =====================================================
# FALLBACK: SSH PARSING (if Gitea is down)
# =====================================================

REQ_PATTERN = re.compile(
    r'^(REQ-\w+)\s*\|\s*(OPEN|DONE|VERIFIED|BLOCKED|IN_PROGRESS|REOPENED)\s*\|\s*(.+)$',
    re.MULTILINE
)
PRIORITY_PATTERN = re.compile(r'^##\s*(P\d+)', re.MULTILINE)


def ssh_read_file(ssh_target, remote_path, timeout=10):
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
             ssh_target, f"cat {remote_path}"],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout if result.returncode == 0 else None
    except:
        return None


def fetch_project_from_ssh(project):
    """Fallback: parse REQUIREMENTS.md via SSH."""
    content = ssh_read_file(project["ssh"], f"{project['path']}/{project['requirements_file']}")
    if not content:
        return None

    requirements = []
    current_priority = "P0"
    for line in content.split('\n'):
        pmatch = PRIORITY_PATTERN.match(line)
        if pmatch:
            current_priority = pmatch.group(1)
            continue
        rmatch = REQ_PATTERN.match(line.strip())
        if rmatch:
            requirements.append({
                "id": rmatch.group(1),
                "status": rmatch.group(2),
                "description": rmatch.group(3).strip(),
                "priority": current_priority
            })

    totals = {
        "open": sum(1 for r in requirements if r["status"] == "OPEN"),
        "done": sum(1 for r in requirements if r["status"] == "DONE"),
        "verified": sum(1 for r in requirements if r["status"] == "VERIFIED"),
        "blocked": sum(1 for r in requirements if r["status"] == "BLOCKED"),
        "in_progress": sum(1 for r in requirements if r["status"] == "IN_PROGRESS"),
        "total": len(requirements)
    }
    completed = totals["done"] + totals["verified"]
    percent = round((completed / totals["total"]) * 100) if totals["total"] > 0 else 0
    p0_reqs = [r for r in requirements if r["priority"] == "P0"]

    days_remaining = None
    if project.get("deadline"):
        deadline_date = datetime.strptime(project["deadline"], "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        days_remaining = (deadline_date - today).days

    return {
        "name": project["name"],
        "slug": project["slug"],
        "server": project["ssh"].split("@")[1] if "@" in project["ssh"] else "",
        "deadline": project.get("deadline"),
        "days_remaining": days_remaining,
        "url": project.get("url", ""),
        "totals": totals,
        "percent_complete": percent,
        "p0_status": {"open": sum(1 for r in p0_reqs if r["status"] == "OPEN"), "total": len(p0_reqs)},
        "requirements": requirements,
        "test_summary": None,
        "source": "ssh-fallback"
    }


# =====================================================
# MAIN REFRESH
# =====================================================

def refresh_all_projects():
    """Fetch data from all projects. Gitea-first, SSH fallback."""
    use_gitea = gitea_available()
    source = "gitea" if use_gitea else "ssh-fallback"
    print(f"Data source: {source}")

    projects_data = []
    for project in PROJECTS:
        try:
            if use_gitea:
                data = fetch_project_from_gitea(project)
            else:
                data = fetch_project_from_ssh(project)

            if data:
                projects_data.append(data)
            else:
                projects_data.append({
                    "name": project["name"],
                    "slug": project["slug"],
                    "error": "Could not fetch data",
                    "totals": {"total": 0, "open": 0, "done": 0, "verified": 0, "blocked": 0},
                    "percent_complete": 0,
                    "p0_status": {"open": 0, "total": 0},
                    "requirements": []
                })
        except Exception as e:
            print(f"Error: {project['name']} — {e}")

    result = {
        "projects": projects_data,
        "last_refresh": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "gitea_url": GITEA_URL if use_gitea else None,
        "project_count": len(projects_data),
        "total_requirements": sum(p.get("totals", {}).get("total", 0) for p in projects_data),
        "total_open": sum(p.get("totals", {}).get("open", 0) for p in projects_data)
    }

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(result, f, indent=2)

    return result


def get_cached_data():
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except:
        return refresh_all_projects()


if __name__ == "__main__":
    print("Refreshing all projects...")
    result = refresh_all_projects()
    print(f"\nSource: {result['source']}")
    print(f"Projects: {result['project_count']}")
    print(f"Total requirements: {result['total_requirements']}")
    print(f"Total open: {result['total_open']}")

    for p in result['projects']:
        t = p.get('totals', {})
        dl = f" ({p.get('days_remaining', '?')}d left)" if p.get('deadline') else ""
        print(f"\n  {p['name']}{dl} [{p.get('source', '?')}]")
        print(f"    {t.get('total', 0)} total | {t.get('open', 0)} open | {t.get('done', 0)} done | {p.get('percent_complete', 0)}%")
