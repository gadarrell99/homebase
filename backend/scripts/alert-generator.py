#!/usr/bin/env python3
"""
Alert Generator for Sentinel
Runs every 5 minutes via cron to generate alerts for:
- Agent heartbeat issues
- Server disk/memory warnings
- Project downtime
"""

import sqlite3
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("/home/rizeadmin/homebase/data/agents.db")
ALERT_FILE = Path("/home/rizeadmin/homebase/data/alerts.json")
INFRA_FILE = Path("/home/rizeadmin/homebase/data/infrastructure.json")

# Alert thresholds
HEARTBEAT_WARN_MIN = 10
HEARTBEAT_CRIT_MIN = 30
DISK_WARN_PCT = 80
DISK_CRIT_PCT = 90
MEM_WARN_PCT = 85
MEM_CRIT_PCT = 95

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db

def load_infra():
    """Load infrastructure.json for server list."""
    try:
        with open(INFRA_FILE) as f:
            return json.load(f)
    except:
        return {"servers": []}

def load_existing_alerts():
    """Load existing alerts to avoid duplicates."""
    try:
        with open(ALERT_FILE) as f:
            return json.load(f)
    except:
        return {"alerts": [], "last_generated": None}

def save_alerts(data):
    """Save alerts to file."""
    with open(ALERT_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def alert_key(alert):
    """Generate unique key for deduplication."""
    return f"{alert['source']}-{alert['target']}-{alert['message'][:50]}"

def check_agent_heartbeats():
    """Check for stale agent heartbeats."""
    alerts = []
    db = get_db()
    
    # Get latest heartbeat per agent
    cur = db.execute("""
        SELECT agent_id, MAX(timestamp) as last_hb
        FROM heartbeats
        GROUP BY agent_id
    """)
    
    now = datetime.utcnow()
    for row in cur.fetchall():
        agent_id = row['agent_id']
        last_hb = datetime.fromisoformat(row['last_hb'].replace('Z', '+00:00').replace('+00:00', ''))
        
        # Calculate minutes since last heartbeat
        delta = now - last_hb
        minutes = delta.total_seconds() / 60
        
        if minutes > HEARTBEAT_CRIT_MIN:
            alerts.append({
                "severity": "critical",
                "source": "agent",
                "target": agent_id,
                "message": f"Agent {agent_id} no heartbeat for {int(minutes)} min"
            })
        elif minutes > HEARTBEAT_WARN_MIN:
            alerts.append({
                "severity": "warning",
                "source": "agent", 
                "target": agent_id,
                "message": f"Agent {agent_id} heartbeat stale ({int(minutes)} min ago)"
            })
    
    db.close()
    return alerts

def check_server_resources():
    """Check server disk and memory usage."""
    alerts = []
    infra = load_infra()
    
    # Get active servers
    servers = [s for s in infra.get('servers', []) if s.get('status') != 'decommissioned']
    
    for server in servers:
        if not server.get('ssh_user') or not server.get('ip'):
            continue
            
        if server.get('ip') == '192.168.65.253':  # Skip Hyper-V
            continue
            
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", f"{server['ssh_user']}@{server['ip']}",
                 "echo DISK:$(df -h / | awk 'NR==2{print $5}'); echo MEM:$(free -m | awk '/Mem/{printf \"%.0f\", $3/$2*100}')"],
                capture_output=True, text=True, timeout=10
            )
            
            for line in result.stdout.strip().split('\n'):
                if line.startswith('DISK:'):
                    disk_pct = int(line.replace('DISK:', '').replace('%', ''))
                    if disk_pct >= DISK_CRIT_PCT:
                        alerts.append({
                            "severity": "critical",
                            "source": "server",
                            "target": server['hostname'],
                            "message": f"{server['hostname']} disk critically full: {disk_pct}%"
                        })
                    elif disk_pct >= DISK_WARN_PCT:
                        alerts.append({
                            "severity": "warning",
                            "source": "server",
                            "target": server['hostname'],
                            "message": f"{server['hostname']} disk usage high: {disk_pct}%"
                        })
                        
                elif line.startswith('MEM:'):
                    mem_pct = int(line.replace('MEM:', ''))
                    if mem_pct >= MEM_CRIT_PCT:
                        alerts.append({
                            "severity": "critical",
                            "source": "server",
                            "target": server['hostname'],
                            "message": f"{server['hostname']} memory critically high: {mem_pct}%"
                        })
                    elif mem_pct >= MEM_WARN_PCT:
                        alerts.append({
                            "severity": "warning",
                            "source": "server",
                            "target": server['hostname'],
                            "message": f"{server['hostname']} memory usage high: {mem_pct}%"
                        })
                        
        except Exception as e:
            alerts.append({
                "severity": "critical",
                "source": "server",
                "target": server['hostname'],
                "message": f"{server['hostname']} unreachable: {str(e)[:50]}"
            })
    
    return alerts

def send_email_alert(alert):
    """Send email for critical alerts."""
    try:
        subprocess.run([
            "ssh", "agents@192.168.65.241",
            f"python3 ~/scripts/send-email.py dbishop@rize.bm artiedarrell@gmail.com "
            f"'SENTINEL ALERT: {alert['target']}' '{alert['message']}'"
        ], capture_output=True, timeout=30)
    except:
        pass  # Don't fail alert generation if email fails

def main():
    print(f"[{datetime.utcnow().isoformat()}] Alert generator starting...")
    
    # Load existing alerts
    existing = load_existing_alerts()
    existing_keys = {alert_key(a) for a in existing.get('alerts', []) 
                     if a.get('timestamp', '') > (datetime.utcnow() - timedelta(hours=1)).isoformat()}
    
    # Collect new alerts
    new_alerts = []
    new_alerts.extend(check_agent_heartbeats())
    new_alerts.extend(check_server_resources())
    
    # Add timestamp and deduplicate
    timestamp = datetime.utcnow().isoformat() + 'Z'
    alerts_to_add = []
    
    for alert in new_alerts:
        key = alert_key(alert)
        if key not in existing_keys:
            alert['id'] = f"ALT-{datetime.utcnow().strftime('%Y-%m%d%H%M%S')}"
            alert['timestamp'] = timestamp
            alert['acknowledged'] = False
            alerts_to_add.append(alert)
            existing_keys.add(key)
            
            # Send email for critical alerts
            if alert['severity'] == 'critical':
                send_email_alert(alert)
    
    # Merge with existing, keep last 100
    all_alerts = alerts_to_add + existing.get('alerts', [])
    all_alerts = sorted(all_alerts, key=lambda x: x.get('timestamp', ''), reverse=True)[:100]
    
    # Save
    save_alerts({
        "alerts": all_alerts,
        "last_generated": timestamp
    })
    
    print(f"[{timestamp}] Generated {len(alerts_to_add)} new alerts, {len(all_alerts)} total")

if __name__ == '__main__':
    main()
