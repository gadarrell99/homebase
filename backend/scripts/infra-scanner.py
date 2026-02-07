#!/usr/bin/env python3
"""Scans active servers via SSH, updates live metrics in infrastructure.json."""
import json, subprocess, datetime

INFRA = "/home/rizeadmin/homebase/data/infrastructure.json"

def scan(ip, user):
    """SSH to remote server and collect metrics."""
    cmd = f'ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no {user}@{ip} "uptime -p; df -h / | tail -1; free -m | grep Mem; uname -r; cat /proc/loadavg"'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return {"status": "unreachable", "last_scan": datetime.datetime.now(datetime.UTC).isoformat()}
        
        lines = r.stdout.strip().split("\n")
        d = {"status": "ok", "last_scan": datetime.datetime.now(datetime.UTC).isoformat()}
        
        # Parse uptime
        if len(lines) > 0:
            d["uptime"] = lines[0].replace("up ", "")
        
        # Parse disk - format: /dev/sda1 100G 50G 50G 50% /
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 5:
                d["disk_pct"] = parts[4].replace("%", "")
        
        # Parse memory - format: Mem: total used free shared buff/cache available
        if len(lines) > 2:
            parts = lines[2].split()
            if len(parts) >= 3:
                d["mem_total"] = parts[1]
                d["mem_used"] = parts[2]
        
        # Parse kernel
        if len(lines) > 3:
            d["kernel"] = lines[3]
        
        # Parse load
        if len(lines) > 4:
            d["load"] = lines[4].split()[0]
        
        return d
    except Exception as e:
        return {"status": "error", "error": str(e), "last_scan": datetime.datetime.now(datetime.UTC).isoformat()}

def local_scan():
    """Collect metrics from localhost."""
    d = {"status": "ok", "last_scan": datetime.datetime.now(datetime.UTC).isoformat()}
    
    try:
        # Uptime
        r = subprocess.run("uptime -p", shell=True, capture_output=True, text=True)
        d["uptime"] = r.stdout.strip().replace("up ", "")
        
        # Disk
        r = subprocess.run("df -h / | tail -1", shell=True, capture_output=True, text=True)
        parts = r.stdout.split()
        if len(parts) >= 5:
            d["disk_pct"] = parts[4].replace("%", "")
        
        # Memory
        r = subprocess.run("free -m | grep Mem", shell=True, capture_output=True, text=True)
        parts = r.stdout.split()
        if len(parts) >= 3:
            d["mem_total"] = parts[1]
            d["mem_used"] = parts[2]
        
        # Kernel
        r = subprocess.run("uname -r", shell=True, capture_output=True, text=True)
        d["kernel"] = r.stdout.strip()
        
        # Load
        r = subprocess.run("cat /proc/loadavg", shell=True, capture_output=True, text=True)
        d["load"] = r.stdout.split()[0]
        
    except Exception as e:
        d["status"] = "error"
        d["error"] = str(e)
    
    return d

if __name__ == "__main__":
    with open(INFRA) as f:
        infra = json.load(f)
    
    for s in infra["servers"]:
        if s.get("status") != "online" or s["id"] == "hyperv":
            continue
        if s["ip"] == "192.168.65.245":
            s["live"] = local_scan()
        else:
            s["live"] = scan(s["ip"], s["ssh_user"])
    
    infra["meta"]["updated"] = datetime.datetime.now(datetime.UTC).isoformat()
    
    with open(INFRA, "w") as f:
        json.dump(infra, f, indent=4)
    
    ok = sum(1 for s in infra["servers"] if s.get("live", {}).get("status") == "ok")
    print(f"[{datetime.datetime.now(datetime.UTC).isoformat()}] Scanned {ok} servers OK")
