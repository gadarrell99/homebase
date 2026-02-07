"""
Sentinel Kill Switch Module
Emergency stop for AI agents with safety controls and audit logging.

Safety Rules (HARDCODED - DO NOT MODIFY):
1. Sentinel can NEVER kill itself
2. David Bishop requires CEO pre-approval (LIVE production)
3. All kills logged with full context
"""
import os
import sqlite3
import subprocess
import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path

log = logging.getLogger("sentinel.kill_switch")

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agents.db"

# Agent host mapping
AGENT_HOSTS = {
    "david-bishop": "agents@192.168.65.241",
    "apex": "agents@192.168.65.241",
    "aegis": "agents@192.168.65.241",
    "cortex": "talosadmin@192.168.65.237",
}

# Service names for systemctl
AGENT_SERVICES = {
    "david-bishop": "openclaw-gateway",
    "apex": "apex",
    "aegis": "aegis",
    "cortex": "cortex",
}

# Agents requiring CEO pre-approval to kill
PROTECTED_AGENTS = {"david-bishop", "sentinel"}

# Auto-trigger thresholds
THRESHOLDS = {
    "malformed_responses": 10,        # 10+ in sequence
    "error_rate_percent": 50,          # >50% sustained for 5 min
    "response_time_seconds": 60,       # >60s sustained
    "complaints_per_hour": 3,          # 3+ user complaints
}

CEO_EMAILS = ["artiedarrell@gmail.com", "gadarrell@rize.bm"]


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def _ssh_command(host: str, cmd: str, timeout: int = 30) -> tuple:
    """Execute SSH command and return (success, output)."""
    full_cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host, cmd]
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "SSH command timed out"
    except Exception as e:
        return False, str(e)


def _send_ceo_alert(subject: str, body: str) -> bool:
    """Send alert to CEO via email script on .241."""
    try:
        recipients = " ".join(CEO_EMAILS)
        cmd = f"python3 ~/scripts/send-email.py dbishop@rize.bm {recipients} '{subject}' '{body}'"
        success, output = _ssh_command("agents@192.168.65.241", cmd)
        if success:
            log.info(f"CEO alert sent: {subject}")
        else:
            log.error(f"CEO alert failed: {output}")
        return success
    except Exception as e:
        log.error(f"CEO alert error: {e}")
        return False


async def kill_agent(agent_id: str, reason: str, triggered_by: str = "auto") -> Dict[str, Any]:
    """
    Kill an agent. Returns dict with success status and details.
    
    Safety checks:
    1. Cannot kill sentinel (self)
    2. Cannot kill protected agents without CEO pre-approval
    """
    result = {
        "agent_id": agent_id,
        "action": "kill",
        "success": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Safety check: Never kill self
    if agent_id == "sentinel":
        result["error"] = "SAFETY: Sentinel cannot kill itself"
        log.error(result["error"])
        return result
    
    # Safety check: Protected agents require CEO approval
    if agent_id in PROTECTED_AGENTS and triggered_by == "auto":
        result["error"] = f"SAFETY: {agent_id} is protected - requires CEO pre-approval"
        log.warning(result["error"])
        _send_ceo_alert(
            f"[SENTINEL] Kill Request Blocked: {agent_id}",
            f"Auto-kill of {agent_id} was blocked.\nReason: {reason}\n\nCEO approval required."
        )
        return result
    
    # Get host and service
    host = AGENT_HOSTS.get(agent_id)
    service = AGENT_SERVICES.get(agent_id)
    if not host or not service:
        result["error"] = f"Unknown agent: {agent_id}"
        return result
    
    # Execute kill via systemctl
    if agent_id == "david-bishop":
        # David uses user service
        cmd = f"systemctl --user stop {service}"
    else:
        cmd = f"sudo systemctl stop {service}"
    
    success, output = _ssh_command(host, cmd)
    
    # Log to database
    db = get_db()
    context = json.dumps({
        "reason": reason,
        "output": output[:500],
        "host": host,
        "service": service,
    })
    
    db.execute("""
        INSERT INTO incidents (agent_id, incident_type, reason, triggered_by, status, context)
        VALUES (?, 'kill', ?, ?, 'active', ?)
    """, (agent_id, reason, triggered_by, context))
    
    # Update agent status
    db.execute("UPDATE agents SET status = 'killed' WHERE agent_id = ?", (agent_id,))
    db.commit()
    db.close()
    
    result["success"] = success
    result["output"] = output[:200]
    
    # Alert CEO
    _send_ceo_alert(
        f"[SENTINEL] Agent Killed: {agent_id}",
        f"Agent {agent_id} has been killed.\nReason: {reason}\nTriggered by: {triggered_by}\n\nUse POST /api/kill-switch/{agent_id}/resume to restart."
    )
    
    log.info(f"Kill executed: {agent_id} - success={success}")
    return result


async def resume_agent(agent_id: str, approved_by: str) -> Dict[str, Any]:
    """Resume a killed agent. Requires CEO approval."""
    result = {
        "agent_id": agent_id,
        "action": "resume",
        "success": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Check if agent is actually killed
    db = get_db()
    row = db.execute("SELECT status FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    if not row:
        result["error"] = f"Agent not found: {agent_id}"
        db.close()
        return result
    
    if row["status"] != "killed":
        result["error"] = f"Agent {agent_id} is not in killed state (current: {row['status']})"
        db.close()
        return result
    
    # Get host and service
    host = AGENT_HOSTS.get(agent_id)
    service = AGENT_SERVICES.get(agent_id)
    if not host or not service:
        result["error"] = f"Unknown agent: {agent_id}"
        db.close()
        return result
    
    # Execute restart
    if agent_id == "david-bishop":
        cmd = f"systemctl --user start {service}"
    else:
        cmd = f"sudo systemctl start {service}"
    
    success, output = _ssh_command(host, cmd)
    
    if success:
        # Update status
        db.execute("UPDATE agents SET status = 'healthy' WHERE agent_id = ?", (agent_id,))
        
        # Resolve incident
        db.execute("""
            UPDATE incidents SET status = 'resolved', resolved_at = datetime('now'), resolved_by = ?
            WHERE agent_id = ? AND status = 'active' AND incident_type = 'kill'
        """, (approved_by, agent_id))
        db.commit()
        
        result["success"] = True
        log.info(f"Agent {agent_id} resumed by {approved_by}")
    else:
        result["error"] = output[:200]
    
    db.close()
    return result


async def get_kill_status(agent_id: str) -> Dict[str, Any]:
    """Get current kill/status info for an agent."""
    db = get_db()
    agent = db.execute("SELECT agent_id, status FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    incident = db.execute("""
        SELECT * FROM incidents WHERE agent_id = ? AND incident_type = 'kill' 
        ORDER BY created_at DESC LIMIT 1
    """, (agent_id,)).fetchone()
    db.close()
    
    return {
        "agent_id": agent_id,
        "status": dict(agent) if agent else None,
        "last_incident": dict(incident) if incident else None,
    }


async def check_auto_triggers(agent_id: str) -> Optional[str]:
    """
    Check if auto-kill triggers are met. Returns reason string if should kill, None otherwise.
    """
    db = get_db()
    
    # Get recent heartbeats
    heartbeats = db.execute("""
        SELECT status, error_count_1h, data FROM heartbeats
        WHERE agent_id = ? ORDER BY timestamp DESC LIMIT 10
    """, (agent_id,)).fetchall()
    
    db.close()
    
    if not heartbeats:
        return None
    
    # Check error rate
    error_count = sum(1 for h in heartbeats if h["status"] != "healthy")
    if error_count >= 5:  # 5 out of last 10 heartbeats unhealthy
        return f"High error rate: {error_count}/10 heartbeats unhealthy"
    
    # Check cumulative errors
    total_errors = sum(h["error_count_1h"] or 0 for h in heartbeats[:3])
    if total_errors >= THRESHOLDS["malformed_responses"]:
        return f"Error threshold exceeded: {total_errors} errors in last 3 heartbeats"
    
    return None


# Ensure tables exist
def init_tables():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            incident_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            triggered_by TEXT DEFAULT 'auto',
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT,
            resolved_by TEXT,
            status TEXT DEFAULT 'active',
            context TEXT
        )
    """)
    db.commit()
    db.close()


if __name__ == "__main__":
    init_tables()
    print("Kill switch tables initialized")
