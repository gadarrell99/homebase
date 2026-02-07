"""
Agent Monitor Service - Tracks AI agents across Rize infrastructure
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agents.db"

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db

def list_agents():
    """Get all registered agents with their latest status"""
    db = get_db()
    agents = db.execute('''
        SELECT a.*, 
            (SELECT status FROM heartbeats WHERE agent_id = a.agent_id ORDER BY timestamp DESC LIMIT 1) as last_status,
            (SELECT timestamp FROM heartbeats WHERE agent_id = a.agent_id ORDER BY timestamp DESC LIMIT 1) as last_heartbeat
        FROM agents a
        ORDER BY a.display_name
    ''').fetchall()
    db.close()
    return [dict(a) for a in agents]

def get_overview():
    """Get dashboard overview stats"""
    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM agents').fetchone()[0]
    active = db.execute("SELECT COUNT(*) FROM agents WHERE status = 'active'").fetchone()[0]
    
    # Get agents with recent heartbeats (last 5 min)
    five_min_ago = (datetime.utcnow() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
    healthy = db.execute('''
        SELECT COUNT(DISTINCT agent_id) FROM heartbeats 
        WHERE timestamp > ? AND status = 'healthy'
    ''', (five_min_ago,)).fetchone()[0]
    
    # Recent incidents
    incidents = db.execute('''
        SELECT COUNT(*) FROM incidents 
        WHERE detected_at > datetime('now', '-24 hours') AND status = 'open'
    ''').fetchone()[0]
    
    db.close()
    return {
        "total_agents": total,
        "active_agents": active,
        "healthy_agents": healthy,
        "open_incidents": incidents
    }

def get_agent(agent_id: str):
    """Get detailed info for a specific agent"""
    db = get_db()
    agent = db.execute('SELECT * FROM agents WHERE agent_id = ?', (agent_id,)).fetchone()
    if not agent:
        db.close()
        return None
    
    agent_dict = dict(agent)
    
    # Get recent heartbeats
    heartbeats = db.execute('''
        SELECT * FROM heartbeats WHERE agent_id = ? 
        ORDER BY timestamp DESC LIMIT 20
    ''', (agent_id,)).fetchall()
    agent_dict['heartbeats'] = [dict(h) for h in heartbeats]
    
    # Get recent audit log
    logs = db.execute('''
        SELECT * FROM audit_log WHERE agent_id = ? 
        ORDER BY timestamp DESC LIMIT 50
    ''', (agent_id,)).fetchall()
    agent_dict['audit_log'] = [dict(l) for l in logs]
    
    # Get incidents
    incidents = db.execute('''
        SELECT * FROM incidents WHERE agent_id = ? 
        ORDER BY detected_at DESC LIMIT 10
    ''', (agent_id,)).fetchall()
    agent_dict['incidents'] = [dict(i) for i in incidents]
    
    db.close()
    return agent_dict

def register_agent(agent_id: str, display_name: str, host: str, agent_type: str = "ai-assistant", capabilities: list = None):
    """Register a new agent or update existing"""
    db = get_db()
    db.execute('''
        INSERT INTO agents (agent_id, display_name, host, agent_type, capabilities, status, registered_at)
        VALUES (?, ?, ?, ?, ?, 'active', datetime('now'))
        ON CONFLICT(agent_id) DO UPDATE SET
            display_name = excluded.display_name,
            host = excluded.host,
            agent_type = excluded.agent_type,
            capabilities = excluded.capabilities
    ''', (agent_id, display_name, host, agent_type, json.dumps(capabilities or [])))
    db.commit()
    db.close()
    return {"registered": agent_id}

def record_heartbeat(agent_id: str, status: str, uptime_seconds: int = 0, memory_mb: int = 0, active_tasks: int = 0, data: dict = None):
    """Record agent heartbeat"""
    db = get_db()
    db.execute('''
        INSERT INTO heartbeats (agent_id, timestamp, status, uptime_seconds, memory_mb, active_tasks, data)
        VALUES (?, datetime('now'), ?, ?, ?, ?, ?)
    ''', (agent_id, status, uptime_seconds, memory_mb, active_tasks, json.dumps(data or {})))
    db.commit()
    db.close()
    return {"ok": True}

def log_action(agent_id: str, action: str, details: dict = None, user: str = None):
    """Log an agent action for audit trail"""
    db = get_db()
    db.execute('''
        INSERT INTO audit_log (agent_id, timestamp, action, details, user)
        VALUES (?, datetime('now'), ?, ?, ?)
    ''', (agent_id, action, json.dumps(details or {}), user))
    db.commit()
    db.close()
    return {"logged": True}

def create_incident(agent_id: str, severity: str, title: str, description: str = ""):
    """Create a new incident"""
    db = get_db()
    cursor = db.execute('''
        INSERT INTO incidents (agent_id, severity, title, description, status, detected_at)
        VALUES (?, ?, ?, ?, 'open', datetime('now'))
    ''', (agent_id, severity, title, description))
    incident_id = cursor.lastrowid
    db.commit()
    db.close()
    return {"incident_id": incident_id}
