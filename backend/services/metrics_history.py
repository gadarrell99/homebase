"""Metrics History - Stores and retrieves server metrics over time."""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
import random

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agents.db"

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db

def init_metrics_table():
    """Create metrics table if it doesn't exist."""
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS server_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_ip TEXT NOT NULL,
            server_name TEXT,
            cpu REAL,
            mem_used INTEGER,
            mem_total INTEGER,
            disk_pct INTEGER,
            load_avg REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_metrics_server ON server_metrics(server_ip)')
    db.execute('CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON server_metrics(timestamp)')
    db.commit()
    db.close()

# Initialize table on import
init_metrics_table()

def record_metrics(results):
    """Record metrics from server scan results."""
    if not results:
        return 0
    
    db = get_db()
    count = 0
    for server in results:
        if not server or not isinstance(server, dict):
            continue
        
        ip = server.get("ip", "")
        name = server.get("name", server.get("hostname", ""))
        live = server.get("live", {})
        
        cpu = 0
        if "load" in live:
            try:
                cpu = float(live["load"]) * 10  # Approximate CPU from load
            except:
                pass
        
        mem_used = int(live.get("mem_used", 0) or 0)
        mem_total = int(live.get("mem_total", 0) or 0)
        
        disk_pct = 0
        if "disk_pct" in live:
            try:
                disk_pct = int(str(live["disk_pct"]).replace("%", ""))
            except:
                pass
        
        load_avg = 0
        if "load" in live:
            try:
                load_avg = float(live["load"])
            except:
                pass
        
        try:
            db.execute('''
                INSERT INTO server_metrics (server_ip, server_name, cpu, mem_used, mem_total, disk_pct, load_avg)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ip, name, cpu, mem_used, mem_total, disk_pct, load_avg))
            count += 1
        except Exception as e:
            print(f"Error recording metrics for {ip}: {e}")
    
    db.commit()
    db.close()
    return count

def get_server_metrics(server_name, hours=24, interval=30):
    """Get historical metrics for a specific server."""
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    cur = db.execute('''
        SELECT server_ip, cpu, mem_used, mem_total, disk_pct, load_avg, timestamp
        FROM server_metrics
        WHERE (server_name LIKE ? OR server_ip LIKE ?)
        AND timestamp > ?
        ORDER BY timestamp ASC
    ''', (f"%{server_name}%", f"%{server_name}%", cutoff.isoformat()))
    
    rows = cur.fetchall()
    db.close()
    
    # Sample at interval to avoid too many points
    result = []
    last_ts = None
    for row in rows:
        ts = row["timestamp"]
        if last_ts:
            try:
                t1 = datetime.fromisoformat(last_ts.replace("Z", ""))
                t2 = datetime.fromisoformat(ts.replace("Z", ""))
                if (t2 - t1).seconds < interval * 60:
                    continue
            except:
                pass
        
        result.append({
            "server_ip": row["server_ip"],
            "cpu": row["cpu"],
            "mem_used": row["mem_used"],
            "mem_total": row["mem_total"],
            "disk_pct": row["disk_pct"],
            "load_avg": row["load_avg"],
            "timestamp": ts
        })
        last_ts = ts
    
    return result

def get_all_servers_metrics(hours=24, interval=30):
    """Get historical metrics for all servers."""
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    # Get distinct servers
    cur = db.execute('SELECT DISTINCT server_ip FROM server_metrics WHERE timestamp > ?', (cutoff.isoformat(),))
    servers = [row["server_ip"] for row in cur.fetchall()]
    db.close()
    
    result = {}
    for server in servers:
        result[server] = get_server_metrics(server, hours, interval)
    
    return result

def get_metrics_summary(hours=24):
    """Get summary statistics for all servers."""
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    cur = db.execute('''
        SELECT 
            server_ip,
            server_name,
            AVG(cpu) as avg_cpu,
            MAX(cpu) as max_cpu,
            AVG(mem_used) as avg_mem,
            MAX(mem_used) as max_mem,
            AVG(disk_pct) as avg_disk,
            MAX(disk_pct) as max_disk,
            COUNT(*) as sample_count
        FROM server_metrics
        WHERE timestamp > ?
        GROUP BY server_ip
    ''', (cutoff.isoformat(),))
    
    result = {}
    for row in cur.fetchall():
        result[row["server_ip"]] = {
            "name": row["server_name"],
            "avg_cpu": round(row["avg_cpu"] or 0, 1),
            "max_cpu": round(row["max_cpu"] or 0, 1),
            "avg_mem": int(row["avg_mem"] or 0),
            "max_mem": int(row["max_mem"] or 0),
            "avg_disk": int(row["avg_disk"] or 0),
            "max_disk": int(row["max_disk"] or 0),
            "samples": row["sample_count"]
        }
    
    db.close()
    return result

def cleanup_old_metrics(days=30):
    """Remove metrics older than specified days."""
    db = get_db()
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    cur = db.execute('DELETE FROM server_metrics WHERE timestamp < ?', (cutoff.isoformat(),))
    deleted = cur.rowcount
    
    db.commit()
    db.close()
    return deleted


# Legacy compatibility: keep the old history_service for any code that uses it
class MetricsHistory:
    def __init__(self, max_len=20):
        self.history = deque(maxlen=max_len)
        self._populate_initial_data()

    def _populate_initial_data(self):
        current_time = datetime.now().timestamp()
        for i in range(20):
            t = current_time - (20 - i)
            self.history.append({
                "timestamp": datetime.fromtimestamp(t).isoformat(),
                "cpu": round(random.uniform(20, 60), 1),
                "memory": round(random.uniform(40, 80), 1)
            })

    def add_mock_point(self):
        point = {
            "timestamp": datetime.now().isoformat(),
            "cpu": round(random.uniform(20, 80), 1),
            "memory": round(random.uniform(40, 90), 1)
        }
        self.history.append(point)
        return point

    def get_data(self):
        return list(self.history)

history_service = MetricsHistory()
