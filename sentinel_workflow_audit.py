"""
Sentinel Workflow Audit
Checks compliance with WORKFLOW-SPEC.md rules.
Run via crontab every 30 minutes.
"""
import subprocess
import json
import os
from datetime import datetime, timezone, timedelta

GITEA_URL = "http://localhost:3100"
TOKEN = open(os.path.expanduser("~/gitea-api-token.txt")).read().strip()
AUDIT_LOG = os.path.expanduser("~/homebase/logs/workflow-audit.log")

os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    with open(AUDIT_LOG, 'a') as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")

def gitea_get(path):
    import urllib.request
    try:
        req = urllib.request.Request(
            f"{GITEA_URL}/api/v1{path}",
            headers={"Authorization": f"token {TOKEN}"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except:
        return None

def check_stale_p0():
    """Flag P0 issues open > 48 hours."""
    repos = ["helios", "bps-ai", "homebase", "best-shipping", "premier-emr"]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    stale = []

    for repo in repos:
        issues = gitea_get(f"/repos/rize/{repo}/issues?state=open&labels=P0&limit=50") or []
        for issue in issues:
            created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            if created < cutoff:
                stale.append(f"rize/{repo} #{issue['number']}: {issue['title']} (open {(datetime.now(timezone.utc) - created).days}d)")

    if stale:
        log(f"STALE P0 WARNING: {len(stale)} issues open > 48h")
        for s in stale:
            log(f"  → {s}")
    else:
        log("STALE P0 CHECK: OK — no stale P0 issues")

    return stale

def check_issues_without_tests():
    """Flag closed issues that don't have test evidence in comments."""
    repos = ["helios", "bps-ai", "homebase"]
    flagged = []

    for repo in repos:
        issues = gitea_get(f"/repos/rize/{repo}/issues?state=closed&limit=20") or []
        for issue in issues:
            comments = gitea_get(f"/repos/rize/{repo}/issues/{issue['number']}/comments") or []
            has_test_evidence = any(
                "playwright" in (c.get("body", "").lower()) or
                "passed" in (c.get("body", "").lower()) or
                "test" in (c.get("body", "").lower())
                for c in comments
            )
            if not has_test_evidence:
                flagged.append(f"rize/{repo} #{issue['number']}: {issue['title']}")

    if flagged:
        log(f"AUDIT WARNING: {len(flagged)} issues closed without test evidence")
        for f_item in flagged:
            log(f"  → {f_item}")
    else:
        log("AUDIT CHECK: OK — all closed issues have test evidence")

    return flagged

def check_service_health():
    """Verify all project URLs respond."""
    services = {
        "Homebase": "http://localhost:8000",
        "Gitea": "http://localhost:3100",
    }
    down = []

    for name, url in services.items():
        try:
            import urllib.request
            resp = urllib.request.urlopen(url, timeout=5)
            if resp.status != 200:
                down.append(f"{name} ({url}): HTTP {resp.status}")
        except Exception as e:
            down.append(f"{name} ({url}): {e}")

    if down:
        log(f"SERVICE HEALTH WARNING: {len(down)} services down")
        for d in down:
            log(f"  → {d}")
    else:
        log("SERVICE HEALTH: OK — all local services responding")

    return down

if __name__ == "__main__":
    log("=== WORKFLOW AUDIT START ===")
    check_stale_p0()
    check_issues_without_tests()
    check_service_health()
    log("=== WORKFLOW AUDIT COMPLETE ===")
