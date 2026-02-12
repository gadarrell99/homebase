"""Sentinel - AI Agent Oversight System"""
import sqlite3
import json
from datetime import datetime, time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agents.db"

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db

def get_config(key=None):
    db = get_db()
    if key:
        row = db.execute('SELECT value FROM sentinel_config WHERE key = ?', (key,)).fetchone()
        db.close()
        return row['value'] if row else None
    rows = db.execute('SELECT key, value, updated_at FROM sentinel_config').fetchall()
    db.close()
    return {r['key']: r['value'] for r in rows}

def set_config(key, value, updated_by='system'):
    db = get_db()
    db.execute('''
        INSERT INTO sentinel_config (key, value, updated_at, updated_by) 
        VALUES (?, ?, datetime('now'), ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at, updated_by=excluded.updated_by
    ''', (key, value, updated_by))
    db.commit()
    db.close()
    return True

def get_maintenance_window():
    db = get_db()
    row = db.execute('SELECT * FROM maintenance_windows WHERE active = 1 ORDER BY id LIMIT 1').fetchone()
    db.close()
    return dict(row) if row else None

def set_maintenance_window(start_time, duration_minutes, days_of_week, active=1):
    db = get_db()
    db.execute('''
        INSERT OR REPLACE INTO maintenance_windows (id, start_time, duration_minutes, days_of_week, active)
        VALUES (1, ?, ?, ?, ?)
    ''', (start_time, duration_minutes, json.dumps(days_of_week), active))
    db.commit()
    db.close()
    return True

def is_maintenance_active():
    window = get_maintenance_window()
    if not window or not window['active']:
        return False
    now = datetime.utcnow()
    day_abbr = now.strftime('%a').lower()
    days = json.loads(window['days_of_week']) if window['days_of_week'] else []
    if day_abbr not in days:
        return False
    start_parts = window['start_time'].split(':')
    start = time(int(start_parts[0]), int(start_parts[1]))
    end_hour = (int(start_parts[0]) + window['duration_minutes'] // 60) % 24
    end_min = (int(start_parts[1]) + window['duration_minutes'] % 60) % 60
    end = time(end_hour, end_min)
    current = now.time()
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end

def get_maintenance_status():
    window = get_maintenance_window()
    return {
        'active': is_maintenance_active(),
        'window': window,
        'current_time_utc': datetime.utcnow().strftime('%H:%M')
    }

# ═══════════════════════════════════════════════════════════
# ESCALATION PIPELINE — Added 2026-02-09
# ═══════════════════════════════════════════════════════════

ESCALATION_LEVELS = {
    1: {"name": "Warning", "action": "log", "description": "Missed 1 heartbeat"},
    2: {"name": "Auto-Restart", "action": "restart", "description": "Missed 3 heartbeats"},
    3: {"name": "Alert CEO", "action": "email", "description": "Restart failed or 3+ restarts in 10 min"},
    4: {"name": "Kill Switch", "action": "manual", "description": "Manual intervention required"}
}

def init_escalation_tables():
    """Create escalation tracking tables if they do not exist"""
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS agent_escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 1,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            resolved_by TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS agent_restart_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            restart_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success INTEGER DEFAULT 0,
            error_message TEXT
        )
    """)
    db.commit()
    db.close()

def get_current_escalation(agent_id):
    """Get current escalation level for an agent"""
    db = get_db()
    row = db.execute("""
        SELECT * FROM agent_escalations 
        WHERE agent_id = ? AND resolved_at IS NULL 
        ORDER BY created_at DESC LIMIT 1
    """, (agent_id,)).fetchone()
    db.close()
    return dict(row) if row else None

def escalate_agent(agent_id, level, reason):
    """Create or update escalation for an agent"""
    db = get_db()
    # Resolve any existing escalations first
    db.execute("""
        UPDATE agent_escalations 
        SET resolved_at = datetime(now), resolved_by = system-auto 
        WHERE agent_id = ? AND resolved_at IS NULL
    """, (agent_id,))
    # Create new escalation
    db.execute("""
        INSERT INTO agent_escalations (agent_id, level, reason) VALUES (?, ?, ?)
    """, (agent_id, level, reason))
    db.commit()
    db.close()
    return True

def resolve_escalation(agent_id, resolved_by='system'):
    """Resolve current escalation for an agent"""
    db = get_db()
    db.execute("""
        UPDATE agent_escalations 
        SET resolved_at = datetime(now), resolved_by = ? 
        WHERE agent_id = ? AND resolved_at IS NULL
    """, (resolved_by, agent_id))
    db.commit()
    db.close()
    return True

def log_restart(agent_id, success, error_message=None):
    """Log an agent restart attempt"""
    db = get_db()
    db.execute("""
        INSERT INTO agent_restart_log (agent_id, success, error_message) VALUES (?, ?, ?)
    """, (agent_id, 1 if success else 0, error_message))
    db.commit()
    db.close()

def get_recent_restarts(agent_id, minutes=10):
    """Get restart count in last N minutes"""
    db = get_db()
    row = db.execute("""
        SELECT COUNT(*) as count FROM agent_restart_log 
        WHERE agent_id = ? AND restart_time > datetime(now, - || ? ||  minutes)
    """, (agent_id, minutes)).fetchone()
    db.close()
    return row[count] if row else 0

def get_all_escalations():
    """Get all current escalations"""
    db = get_db()
    rows = db.execute("""
        SELECT e.*, 
               (SELECT COUNT(*) FROM agent_restart_log r 
                WHERE r.agent_id = e.agent_id 
                AND r.restart_time > datetime(now, -10 minutes)) as recent_restarts
        FROM agent_escalations e 
        WHERE e.resolved_at IS NULL
        ORDER BY e.level DESC, e.created_at DESC
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]

def check_heartbeat_escalation(agent_id, missed_beats):
    """Determine escalation level based on missed heartbeats"""
    current = get_current_escalation(agent_id)
    current_level = current[level] if current else 0
    
    if missed_beats >= 3:
        new_level = 2
        reason = f"Missed {missed_beats} consecutive heartbeats"
    elif missed_beats >= 1:
        new_level = 1
        reason = f"Missed {missed_beats} heartbeat(s)"
    else:
        # No missed beats, resolve any escalation
        if current_level > 0:
            resolve_escalation(agent_id, heartbeat-restored)
        return None
    
    # Check if restart count is high
    recent_restarts = get_recent_restarts(agent_id)
    if recent_restarts >= 3:
        new_level = 3
        reason = f"Too many restarts ({recent_restarts}) in 10 minutes"
    
    if new_level > current_level:
        escalate_agent(agent_id, new_level, reason)
        return {"agent_id": agent_id, "level": new_level, "reason": reason, "action": ESCALATION_LEVELS[new_level]}
    
    return None

# Initialize tables on module load
try:
    init_escalation_tables()
except:
    pass  # Tables may already exist
