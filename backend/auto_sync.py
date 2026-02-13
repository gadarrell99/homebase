#!/usr/bin/env python3
"""
Homebase Auto-Sync
Refreshes cached data from all sources:
- Fleet server status (SSH ping)
- Agent status (process checks)
- Gitea issues/repos
Runs every 15 minutes via cron
"""
import json
import subprocess
import os
from datetime import datetime

DATA_DIR = os.path.expanduser("~/homebase/data")
os.makedirs(DATA_DIR, exist_ok=True)

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

def sync_fleet():
    fleet = {
        "237": {"name": "Talos", "ip": "192.168.65.237", "ports": [22, 7681, 7682, 8080]},
        "241": {"name": "Agents", "ip": "192.168.65.241", "ports": [22, 9010, 18789]},
        "245": {"name": "Rize-Apps", "ip": "192.168.65.245", "ports": [22, 3100, 3002, 3003, 9020]},
        "246": {"name": "Demos", "ip": "192.168.65.246", "ports": [22]},
        "249": {"name": "Vector", "ip": "192.168.65.249", "ports": [22, 8000, 5173]},
    }
    results = {}
    for sid, info in fleet.items():
        ping = run_cmd(f"ping -c1 -W2 {info['ip']} 2>/dev/null | grep -c '1 received'")
        online = ping.strip() == "1"
        port_status = {}
        if online:
            for port in info["ports"]:
                code = run_cmd(f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout 3 http://{info['ip']}:{port} 2>/dev/null")
                port_status[str(port)] = code if code else "timeout"
        results[sid] = {
            "name": info["name"], "ip": info["ip"], "online": online,
            "ports": port_status, "checked": datetime.now().isoformat()
        }
    with open(os.path.join(DATA_DIR, "fleet_status.json"), "w") as f:
        json.dump(results, f, indent=2)
    return results

def sync_gitea():
    try:
        result = run_cmd("curl -s 'http://localhost:3100/api/v1/repos/search?limit=50' 2>/dev/null")
        if result:
            repos = json.loads(result).get("data", [])
            summary = []
            for repo in repos:
                summary.append({
                    "name": repo.get("name"),
                    "open_issues": repo.get("open_issues_count", 0),
                    "updated": repo.get("updated_at", ""),
                    "stars": repo.get("stars_count", 0),
                })
            summary.sort(key=lambda x: x["open_issues"], reverse=True)
            with open(os.path.join(DATA_DIR, "gitea_repos.json"), "w") as f:
                json.dump({"repos": summary, "synced": datetime.now().isoformat()}, f, indent=2)
            return summary
    except:
        pass
    return []

def sync_agents():
    agents = {}
    checks = {
        "apex": "systemctl --user is-active apex-time-dashboard 2>/dev/null",
        "david": "systemctl --user is-active openclaw-gateway 2>/dev/null",
        "aegis": "pgrep -f aegis 2>/dev/null && echo active || echo inactive",
        "cortex": "pgrep -f cortex 2>/dev/null && echo active || echo inactive",
        "sentinel": "pgrep -f sentinel 2>/dev/null && echo active || echo inactive",
    }
    for agent, cmd in checks.items():
        status = run_cmd(f"ssh -o ConnectTimeout=5 agents@192.168.65.241 '{cmd}' 2>/dev/null")
        agents[agent] = {
            "status": status.strip() if status else "unknown",
            "checked": datetime.now().isoformat()
        }
    with open(os.path.join(DATA_DIR, "agent_status.json"), "w") as f:
        json.dump(agents, f, indent=2)
    return agents

def main():
    print(f"=== Homebase Auto-Sync — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print("Syncing fleet...")
    fleet = sync_fleet()
    online = sum(1 for v in fleet.values() if v["online"])
    print(f"  Fleet: {online}/{len(fleet)} online")

    print("Syncing Gitea...")
    repos = sync_gitea()
    total_issues = sum(r["open_issues"] for r in repos)
    print(f"  Gitea: {len(repos)} repos, {total_issues} open issues")

    print("Syncing agents...")
    agents = sync_agents()
    active = sum(1 for v in agents.values() if "active" in v.get("status", ""))
    print(f"  Agents: {active}/{len(agents)} active")

    sync_status = {
        "last_sync": datetime.now().isoformat(),
        "fleet_online": online, "fleet_total": len(fleet),
        "gitea_repos": len(repos), "gitea_issues": total_issues,
        "agents_active": active, "agents_total": len(agents),
    }
    with open(os.path.join(DATA_DIR, "sync_status.json"), "w") as f:
        json.dump(sync_status, f, indent=2)
    print(f"\nSync complete. Data saved to {DATA_DIR}/")

if __name__ == "__main__":
    main()
