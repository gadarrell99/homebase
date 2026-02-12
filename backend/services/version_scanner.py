#!/usr/bin/env python3
"""
Sentinel Version Scanner — Scans fleet for outdated packages
Stores results in version_status table
"""
import subprocess
import sqlite3
import json
from datetime import datetime
from pathlib import Path

FLEET = [
    ("talosadmin", "192.168.65.237", "Talos"),
    ("agents", "192.168.65.241", "Agents"),
    ("localhost", "192.168.65.245", "Rize-Apps"),
    ("demos", "192.168.65.246", "Demos"),
    ("betadmin", "192.168.65.249", "Vector"),
]

DB_PATH = Path.home() / "homebase" / "data" / "agents.db"

def run_ssh(user, host, cmd, timeout=60):
    """Run command via SSH or locally"""
    if host == "192.168.65.245":
        full_cmd = cmd
    else:
        full_cmd = f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {user}@{host} {repr(cmd)}"
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return ""

def get_apt_updates(user, host):
    """Get apt packages that need updates"""
    output = run_ssh(user, host, "apt list --upgradable 2>/dev/null | grep -v Listing")
    updates = []
    for line in output.split("\n"):
        if "/" in line and "[" in line:
            parts = line.split("/")
            pkg = parts[0]
            rest = "/".join(parts[1:])
            if "[upgradable from:" in rest:
                latest = rest.split()[0]
                current = rest.split("from: ")[-1].rstrip("]")
                updates.append({"package": pkg, "current": current, "latest": latest, "type": "apt"})
    return updates

def get_pip_updates(user, host):
    """Get pip packages that need updates"""
    output = run_ssh(user, host, "pip list --outdated --format=json 2>/dev/null")
    try:
        data = json.loads(output) if output else []
        return [{"package": p["name"], "current": p["version"], "latest": p["latest_version"], "type": "pip"} for p in data]
    except:
        return []

def get_npm_updates(user, host, path="~/.openclaw"):
    """Get npm packages that need updates (only on .241)"""
    if host != "192.168.65.241":
        return []
    output = run_ssh(user, host, f"cd {path} && npm outdated --json 2>/dev/null")
    try:
        data = json.loads(output) if output else {}
        return [{"package": k, "current": v.get("current", ""), "latest": v.get("latest", ""), "type": "npm"} for k, v in data.items()]
    except:
        return []

def scan_server(user, host, name):
    """Scan a single server for all package updates"""
    print(f"  Scanning {name} ({host})...")
    updates = []
    updates.extend(get_apt_updates(user, host))
    updates.extend(get_pip_updates(user, host))
    updates.extend(get_npm_updates(user, host))
    return updates

def save_to_db(target, updates):
    """Save updates to version_status table"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    # Mark all existing for this target as not needing update
    cur.execute("UPDATE version_status SET update_available=0 WHERE target=?", (target,))
    
    for u in updates:
        severity = "critical" if any(x in u["package"].lower() for x in ["openssl", "linux-image", "kernel", "ssh"]) else "normal"
        cur.execute("""
            INSERT INTO version_status (target, package, current_version, latest_version, update_available, severity, last_checked)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(target, package) DO UPDATE SET
                current_version=excluded.current_version,
                latest_version=excluded.latest_version,
                update_available=1,
                severity=excluded.severity,
                last_checked=excluded.last_checked
        """, (target, u["package"], u["current"], u["latest"], severity, now))
    
    conn.commit()
    conn.close()
    return len(updates)

def main():
    print("=" * 50)
    print(f"VERSION SCANNER — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    total = 0
    for user, host, name in FLEET:
        updates = scan_server(user, host, name)
        count = save_to_db(name, updates)
        total += count
        print(f"    Found {count} updates")
    
    print("-" * 50)
    print(f"Total updates found: {total}")
    
    # Show summary
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT target, COUNT(*) FROM version_status WHERE update_available=1 GROUP BY target")
    print("\nBy server:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} packages")
    cur.execute("SELECT COUNT(*) FROM version_status WHERE update_available=1 AND severity='critical'")
    critical = cur.fetchone()[0]
    if critical:
        print(f"\n⚠️  CRITICAL updates: {critical}")
    conn.close()

if __name__ == "__main__":
    main()
