"""
Homebase Metrics History Service
Stores and retrieves historical server metrics for charting
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Database path
DB_PATH = Path.home() / "homebase" / "backend" / "homebase.db"


def init_metrics_tables():
    """Initialize metrics history tables"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Server metrics history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_name TEXT NOT NULL,
            server_ip TEXT NOT NULL,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            status TEXT DEFAULT 'online',
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_metrics_server_time 
        ON metrics_history(server_name, recorded_at)
    ''')
    
    conn.commit()
    conn.close()
    print("[MetricsHistory] Tables initialized")


def record_metrics(servers: List[Dict]):
    """Record current metrics for all servers"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    recorded = 0
    for server in servers:
        cpu = server.get("cpu_percent")
        
        # Calculate memory percent if we have used/total
        memory_percent = None
        if server.get("memory_used") and server.get("memory_total"):
            memory_percent = (server["memory_used"] / server["memory_total"]) * 100
        
        # Calculate disk percent if we have used/total
        disk_percent = None
        if server.get("disk_used") and server.get("disk_total"):
            disk_percent = (server["disk_used"] / server["disk_total"]) * 100
        
        cursor.execute('''
            INSERT INTO metrics_history 
            (server_name, server_ip, cpu_percent, memory_percent, disk_percent, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            server.get("name"),
            server.get("ip"),
            cpu,
            memory_percent,
            disk_percent,
            server.get("status", "unknown")
        ))
        recorded += 1
    
    conn.commit()
    conn.close()
    return recorded


def get_server_metrics(server_name: str, hours: int = 24, interval_minutes: int = 30) -> List[Dict]:
    """
    Get historical metrics for a specific server
    Returns data points at specified interval
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Calculate time window
    cutoff = datetime.now() - timedelta(hours=hours)
    
    # Get metrics with subsampling based on interval
    cursor.execute('''
        SELECT 
            server_name,
            cpu_percent,
            memory_percent,
            disk_percent,
            status,
            recorded_at
        FROM metrics_history
        WHERE server_name = ?
        AND recorded_at > ?
        ORDER BY recorded_at ASC
    ''', (server_name, cutoff.isoformat()))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert to list of dicts
    metrics = []
    last_time = None
    
    for row in rows:
        recorded = datetime.fromisoformat(row[5])
        
        # Apply interval sampling
        if last_time is None or (recorded - last_time).total_seconds() >= interval_minutes * 60:
            metrics.append({
                "server_name": row[0],
                "cpu_percent": row[1],
                "memory_percent": row[2],
                "disk_percent": row[3],
                "status": row[4],
                "timestamp": row[5],
                "time_label": recorded.strftime("%H:%M")
            })
            last_time = recorded
    
    return metrics


def get_all_servers_metrics(hours: int = 24, interval_minutes: int = 30) -> Dict[str, List[Dict]]:
    """Get historical metrics for all servers"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Get unique server names
    cursor.execute('SELECT DISTINCT server_name FROM metrics_history')
    servers = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    result = {}
    for server in servers:
        result[server] = get_server_metrics(server, hours, interval_minutes)
    
    return result


def get_metrics_summary(hours: int = 24) -> Dict:
    """Get summary stats for all servers"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cutoff = datetime.now() - timedelta(hours=hours)
    
    cursor.execute('''
        SELECT 
            server_name,
            AVG(cpu_percent) as avg_cpu,
            MAX(cpu_percent) as max_cpu,
            AVG(memory_percent) as avg_memory,
            MAX(memory_percent) as max_memory,
            AVG(disk_percent) as avg_disk,
            MAX(disk_percent) as max_disk,
            COUNT(*) as data_points
        FROM metrics_history
        WHERE recorded_at > ?
        GROUP BY server_name
    ''', (cutoff.isoformat(),))
    
    rows = cursor.fetchall()
    conn.close()
    
    summary = {}
    for row in rows:
        summary[row[0]] = {
            "avg_cpu": round(row[1], 1) if row[1] else None,
            "max_cpu": round(row[2], 1) if row[2] else None,
            "avg_memory": round(row[3], 1) if row[3] else None,
            "max_memory": round(row[4], 1) if row[4] else None,
            "avg_disk": round(row[5], 1) if row[5] else None,
            "max_disk": round(row[6], 1) if row[6] else None,
            "data_points": row[7]
        }
    
    return summary


def cleanup_old_metrics(days: int = 7):
    """Remove metrics older than specified days"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cutoff = datetime.now() - timedelta(days=days)
    cursor.execute('DELETE FROM metrics_history WHERE recorded_at < ?', (cutoff.isoformat(),))
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    return deleted


# Initialize tables when module is imported
init_metrics_tables()
