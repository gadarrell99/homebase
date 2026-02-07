#!/usr/bin/env python3
"""
Project Status Scanner for Homebase.
SSHs to each server, collects project docs, git status, port health, file tree.
Runs via cron every 5 minutes. Writes to data/project-status.json.
"""
import json
import subprocess
import datetime
import os
import re

DATA_FILE = "/home/rizeadmin/homebase/data/project-status.json"
LOG_PREFIX = f"[{datetime.datetime.now(datetime.UTC).isoformat()}]"

# Project definitions with paths and expected docs
PROJECTS = [
    # Demos server (.246)
    {"name": "Best Shipping", "server": "demos", "ip": "192.168.65.246", "user": "demos",
     "path": "/home/demos/best-shipping-dashboard", "type": "demo",
     "ports": [3001, 8001], "domain": "bestshipping.rize.bm"},
    {"name": "BPS-AI", "server": "demos", "ip": "192.168.65.246", "user": "demos",
     "path": "/home/demos/bps-ai", "type": "demo",
     "ports": [3000], "domain": "bpsai.rize.bm"},
    {"name": "Premier EMR", "server": "demos", "ip": "192.168.65.246", "user": "demos",
     "path": "/home/demos/premier-emr", "type": "demo",
     "ports": [3004, 5004], "domain": "emr.rize.bm"},
    {"name": "Helios AI", "server": "demos", "ip": "192.168.65.246", "user": "demos",
     "path": "/home/demos/helios", "type": "demo",
     "ports": [3005], "domain": "helios.rize.bm"},

    # Rize-Apps server (.245 - localhost)
    {"name": "Homebase", "server": "rize-apps", "ip": "localhost", "user": None,
     "path": "/home/rizeadmin/homebase", "type": "infrastructure",
     "ports": [8000], "domain": "homebase.rize.bm"},
    {"name": "Nexus", "server": "rize-apps", "ip": "localhost", "user": None,
     "path": "/home/rizeadmin/nexus", "type": "infrastructure",
     "ports": [3002, 3003], "domain": "nexus.rize.bm"},
    {"name": "Dockyard WiFi", "server": "rize-apps", "ip": "localhost", "user": None,
     "path": "/home/rizeadmin/dockyard-wifi-portal", "type": "infrastructure",
     "ports": [8080, 8081], "domain": "dockyardwifi.rize.bm"},

    # Agents server (.241)
    {"name": "David Bishop", "server": "agents", "ip": "192.168.65.241", "user": "agents",
     "path": "/home/david", "type": "agent",
     "ports": [9001], "domain": "davidbot.rize.bm"},
    {"name": "Apex", "server": "agents", "ip": "192.168.65.241", "user": "agents",
     "path": "/home/agents/apex", "type": "agent",
     "ports": [9002], "domain": None},
    {"name": "Aegis", "server": "agents", "ip": "192.168.65.241", "user": "agents",
     "path": "/home/agents/aegis", "type": "agent",
     "ports": [9003], "domain": None},

    # Vector server (.249)
    {"name": "BET Air Ambulance", "server": "vector", "ip": "192.168.65.249", "user": "betadmin",
     "path": "/home/betadmin/bet", "type": "infrastructure",
     "ports": [3000], "domain": "vector.rize.bm"},
]

# Documentation requirements by project type
DOC_REQUIREMENTS = {
    "demo": [
        ("README.md", True),
        ("TODO.md", True),
        ("CHANGELOG.md", True),
        ("ARCHITECTURE.md", True),
        ("DEMO-SCRIPT.md", True),
        ("API.md", True),
        ("DEPLOYMENT.md", True),
        (".env.example", True),
        ("ROADMAP.md", True),
    ],
    "agent": [
        ("README.md", True),
        ("TODO.md", True),
        ("CHANGELOG.md", True),
        ("SPEC.md", True),
        ("SECURITY.md", True),
        ("INTEGRATIONS.md", True),
        ("RUNBOOK.md", True),
        ("ESCALATION.md", True),
        ("AUDIT-LOG.md", True),
    ],
    "infrastructure": [
        ("README.md", True),
        ("TODO.md", True),
        ("CHANGELOG.md", True),
        ("DEPLOYMENT.md", True),
    ],
}


def run_cmd(cmd, timeout=30):
    """Run a shell command and return output."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode == 0
    except subprocess.TimeoutExpired:
        return "", False
    except Exception as e:
        return str(e), False


def ssh_cmd(ip, user, cmd, timeout=15):
    """Run command via SSH."""
    if ip == "localhost":
        return run_cmd(cmd, timeout)
    ssh = f'ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes {user}@{ip} "{cmd}"'
    return run_cmd(ssh, timeout)


def read_file_content(ip, user, filepath, max_lines=500):
    """Read file content via SSH (or locally). Returns tuple: (content, exists)."""
    cmd = f"head -n {max_lines} '{filepath}' 2>/dev/null"
    content, ok = ssh_cmd(ip, user, cmd)
    if ok and content:
        return content, True
    return "", False


def get_git_status(ip, user, path):
    """Get git status for project."""
    cmd = f"cd '{path}' && git status --porcelain 2>/dev/null | head -20"
    output, ok = ssh_cmd(ip, user, cmd)

    if not ok:
        return {"status": "not_git", "changes": []}

    changes = []
    for line in output.split("\n"):
        if line.strip():
            status = line[:2].strip()
            file = line[3:].strip()
            changes.append({"status": status, "file": file})

    # Get branch info
    cmd = f"cd '{path}' && git rev-parse --abbrev-ref HEAD 2>/dev/null"
    branch, _ = ssh_cmd(ip, user, cmd)

    # Get last commit
    cmd = f"cd '{path}' && git log -1 --format='%h %s (%ar)' 2>/dev/null"
    last_commit, _ = ssh_cmd(ip, user, cmd)

    return {
        "status": "clean" if not changes else "dirty",
        "branch": branch or "unknown",
        "last_commit": last_commit or "unknown",
        "changes": changes[:10],  # Limit to 10
        "uncommitted_count": len(changes),
    }


def check_port(ip, port, timeout=3):
    """Check if port is open."""
    if ip == "localhost":
        cmd = f"nc -z localhost {port}"
    else:
        cmd = f"nc -z -w {timeout} {ip} {port}"
    _, ok = run_cmd(cmd, timeout=timeout+2)
    return ok


def check_http(ip, port, timeout=5):
    """Check HTTP health on port."""
    if ip == "localhost":
        url = f"http://localhost:{port}"
    else:
        url = f"http://{ip}:{port}"
    cmd = f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout {timeout} '{url}'"
    output, ok = run_cmd(cmd, timeout=timeout+2)
    try:
        code = int(output)
        return {"code": code, "healthy": 200 <= code < 500}
    except:
        return {"code": 0, "healthy": False}


def get_file_tree(ip, user, path, max_depth=2):
    """Get project file tree."""
    cmd = f"find '{path}' -maxdepth {max_depth} -type f -name '*.md' -o -type f -name '*.json' -o -type f -name '*.py' -o -type f -name '*.js' -o -type f -name '*.ts' 2>/dev/null | head -50"
    output, ok = ssh_cmd(ip, user, cmd)
    if not ok:
        return []

    files = []
    for line in output.split("\n"):
        if line.strip():
            # Get relative path
            rel = line.replace(path, "").lstrip("/")
            files.append(rel)
    return sorted(files)


def check_docs(ip, user, path, project_type):
    """Check for required documentation files."""
    requirements = DOC_REQUIREMENTS.get(project_type, [])
    results = []

    for doc, required in requirements:
        filepath = f"{path}/{doc}"
        cmd = f"test -f '{filepath}' && echo 'EXISTS'"
        output, _ = ssh_cmd(ip, user, cmd)
        exists = "EXISTS" in output

        results.append({
            "file": doc,
            "required": required,
            "exists": exists,
            "status": "ok" if exists else ("warning" if required else "info"),
        })

    return results


def extract_todos(content):
    """Extract TODO items from TODO.md content."""
    todos = []
    in_list = False

    for line in content.split("\n"):
        line = line.strip()
        # Match checkbox items
        if line.startswith("- [ ]") or line.startswith("- [x]"):
            completed = line.startswith("- [x]")
            text = line[5:].strip()
            todos.append({"text": text, "done": completed})
        # Match priority items like ## High Priority
        elif line.startswith("## "):
            in_list = line

    return todos[:20]  # Limit to 20


def extract_changelog_version(content):
    """Extract latest version from CHANGELOG.md."""
    # Look for patterns like ## [1.0.0] or ## v1.0.0 or ## 1.0.0
    match = re.search(r'^##\s*\[?v?(\d+\.\d+\.\d+)', content, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def scan_project(project):
    """Scan a single project."""
    ip = project["ip"]
    user = project["user"]
    path = project["path"]

    result = {
        "name": project["name"],
        "server": project["server"],
        "type": project["type"],
        "path": path,
        "domain": project.get("domain"),
        "ports": project["ports"],
        "scanned_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    # Check if path exists
    cmd = f"test -d '{path}' && echo 'EXISTS'"
    output, _ = ssh_cmd(ip, user, cmd)
    if "EXISTS" not in output:
        result["status"] = "not_found"
        result["issues"] = [{"severity": "critical", "message": f"Project path not found: {path}"}]
        return result

    result["status"] = "ok"
    result["issues"] = []

    # Get documentation status
    result["docs"] = check_docs(ip, user, path, project["type"])
    missing_docs = [d["file"] for d in result["docs"] if d["required"] and not d["exists"]]
    if missing_docs:
        result["issues"].append({
            "severity": "warning",
            "message": f"Missing required docs: {', '.join(missing_docs)}",
        })

    # Read key files
    readme, readme_exists = read_file_content(ip, user, f"{path}/README.md")
    todo, todo_exists = read_file_content(ip, user, f"{path}/TODO.md")
    changelog, changelog_exists = read_file_content(ip, user, f"{path}/CHANGELOG.md")

    result["readme"] = readme if readme_exists else None
    result["todo"] = todo if todo_exists else None
    result["changelog"] = changelog if changelog_exists else None

    # Extract todos
    if todo_exists:
        todos = extract_todos(todo)
        result["todos_parsed"] = todos
        open_todos = [t for t in todos if not t["done"]]
        result["todos_open"] = len(open_todos)
        result["todos_done"] = len([t for t in todos if t["done"]])
    else:
        result["todos_parsed"] = []
        result["todos_open"] = 0
        result["todos_done"] = 0

    # Extract version
    if changelog_exists:
        result["version"] = extract_changelog_version(changelog)
    else:
        result["version"] = None

    # Git status
    result["git"] = get_git_status(ip, user, path)
    if result["git"]["status"] == "dirty":
        result["issues"].append({
            "severity": "info",
            "message": f"{result['git']['uncommitted_count']} uncommitted changes",
        })

    # Port health
    port_results = []
    for port in project["ports"]:
        port_open = check_port(ip, port)
        http = check_http(ip, port) if port_open else {"code": 0, "healthy": False}
        port_results.append({
            "port": port,
            "open": port_open,
            "http_code": http["code"],
            "healthy": http["healthy"],
        })
        if not port_open:
            result["issues"].append({
                "severity": "critical",
                "message": f"Port {port} not responding",
            })
        elif not http["healthy"]:
            result["issues"].append({
                "severity": "warning",
                "message": f"Port {port} HTTP {http['code']}",
            })
    result["ports_status"] = port_results

    # File tree
    result["files"] = get_file_tree(ip, user, path)

    # Calculate health score
    score = 100
    for issue in result["issues"]:
        if issue["severity"] == "critical":
            score -= 25
        elif issue["severity"] == "warning":
            score -= 10
        elif issue["severity"] == "info":
            score -= 2
    result["health_score"] = max(0, score)

    return result


def main():
    print(f"{LOG_PREFIX} Starting project status scan...")

    results = {
        "meta": {
            "scanned_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "project_count": len(PROJECTS),
            "scanner_version": "1.0.0",
        },
        "projects": [],
        "issues": [],  # Global issues list
        "summary": {
            "total": len(PROJECTS),
            "healthy": 0,
            "warning": 0,
            "critical": 0,
        },
    }

    for project in PROJECTS:
        print(f"{LOG_PREFIX} Scanning {project['name']}...")
        try:
            result = scan_project(project)
            results["projects"].append(result)

            # Aggregate issues with project context
            for issue in result.get("issues", []):
                results["issues"].append({
                    "project": project["name"],
                    "server": project["server"],
                    **issue
                })

            # Update summary
            if result.get("health_score", 0) >= 90:
                results["summary"]["healthy"] += 1
            elif result.get("health_score", 0) >= 60:
                results["summary"]["warning"] += 1
            else:
                results["summary"]["critical"] += 1

        except Exception as e:
            print(f"{LOG_PREFIX} ERROR scanning {project['name']}: {e}")
            results["projects"].append({
                "name": project["name"],
                "server": project["server"],
                "status": "error",
                "error": str(e),
                "health_score": 0,
            })
            results["summary"]["critical"] += 1

    # Sort issues by severity
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    results["issues"].sort(key=lambda x: severity_order.get(x.get("severity"), 99))

    # Write results
    with open(DATA_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"{LOG_PREFIX} Scan complete. {results['summary']['healthy']} healthy, "
          f"{results['summary']['warning']} warning, {results['summary']['critical']} critical")


if __name__ == "__main__":
    main()
