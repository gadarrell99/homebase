"""
Sentinel Auto-Restart Module
Automatically restarts agents that have become unresponsive.

Restart Conditions (ALL must be true):
1. Agent missed 3+ consecutive heartbeats (15+ minutes)
2. Process confirmed dead via SSH check
3. NOT in maintenance window (03:00-04:00 UTC)
4. Agent NOT in 'killed' state (CEO must approve killed agents)
5. Agent NOT restarted more than 3 times in the last hour
"""
import os
import sqlite3
import subprocess
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

log = logging.getLogger("sentinel.auto_restart")

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agents.db"

# Agent configuration
AGENT_HOSTS = {
    "david-bishop": "agents@192.168.65.241",
    "apex": "agents@192.168.65.241",
    "aegis": "agents@192.168.65.241",
    "cortex": "talosadmin@192.168.65.237",
}

AGENT_SERVICES = {
    "david-bishop": "openclaw-gateway",
    "apex": "apex",
    "aegis": "aegis",
    "cortex": "cortex",
}

AGENT_HEALTH_URLS = {
    "apex": "http://localhost:9002/health",
    "aegis": "http://localhost:9003/health",
    "cortex": "http://localhost:9100/health",
}

CEO_EMAILS = ["artiedarrell@gmail.com", "gadarrell@rize.bm"]

# Configuration
MISSED_HEARTBEATS_THRESHOLD = 3
MAX_RESTARTS_PER_HOUR = 3
MAINTENANCE_START_HOUR = 3  # 03:00 UTC
MAINTENANCE_END_HOUR = 4    # 04:00 UTC


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
    """Send alert to CEO."""
    try:
        recipients = " ".join(CEO_EMAILS)
        cmd = f"python3 ~/scripts/send-email.py dbishop@rize.bm {recipients} '{subject}' '{body}'"
        success, output = _ssh_command("agents@192.168.65.241", cmd)
        return success
    except Exception as e:
        log.error(f"CEO alert error: {e}")
        return False


async def is_maintenance_window() -> bool:
    """Check if currently in maintenance window."""
    now = datetime.now(timezone.utc)
    return MAINTENANCE_START_HOUR <= now.hour < MAINTENANCE_END_HOUR


async def get_restart_count(agent_id: str, hours: int = 1) -> int:
    """Get number of restart attempts in the last N hours."""
    db = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    row = db.execute("""
        SELECT COUNT(*) as cnt FROM restart_log 
        WHERE agent_id = ? AND attempted_at > ?
    """, (agent_id, cutoff)).fetchone()
    db.close()
    return row["cnt"] if row else 0


async def verify_process_alive(agent_id: str) -> bool:
    """SSH to host and check if the process is running."""
    host = AGENT_HOSTS.get(agent_id)
    service = AGENT_SERVICES.get(agent_id)
    if not host or not service:
        return False
    
    if agent_id == "david-bishop":
        cmd = f"systemctl --user is-active {service}"
    else:
        cmd = f"systemctl is-active {service}"
    
    success, output = _ssh_command(host, cmd)
    return success and "active" in output.lower()


async def check_health_endpoint(agent_id: str) -> bool:
    """Check if agent's health endpoint responds."""
    url = AGENT_HEALTH_URLS.get(agent_id)
    if not url:
        return True  # No health endpoint defined, assume OK
    
    host = AGENT_HOSTS.get(agent_id)
    if not host:
        return False
    
    cmd = f"curl -s -o /dev/null -w '%{{http_code}}' {url}"
    success, output = _ssh_command(host, cmd, timeout=15)
    return success and output.strip() == "200"


def _get_missed_heartbeat_count(agent_id: str) -> int:
    """Get count of missed consecutive heartbeats."""
    db = get_db()
    # Get last 5 heartbeats
    rows = db.execute("""
        SELECT status FROM heartbeats 
        WHERE agent_id = ? ORDER BY timestamp DESC LIMIT 5
    """, (agent_id,)).fetchall()
    db.close()
    
    if not rows:
        return 5  # No heartbeats = consider all missed
    
    # Count consecutive non-healthy from most recent
    missed = 0
    for row in rows:
        if row["status"] != "healthy":
            missed += 1
        else:
            break
    return missed


async def check_and_restart(agent_id: str) -> Dict[str, Any]:
    """
    Check if agent needs restart and attempt if conditions are met.
    Returns status dict with action taken.
    """
    result = {
        "agent_id": agent_id,
        "action": "none",
        "success": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {},
    }
    
    # Check 1: Get agent status
    db = get_db()
    agent = db.execute("SELECT status FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    db.close()
    
    if not agent:
        result["error"] = f"Agent not found: {agent_id}"
        return result
    
    # Check 2: Skip if killed (requires CEO approval)
    if agent["status"] == "killed":
        result["details"]["skipped"] = "Agent in killed state - CEO approval required"
        return result
    
    # Check 3: Skip if in maintenance window
    if await is_maintenance_window():
        result["details"]["skipped"] = "Maintenance window active"
        return result
    
    # Check 4: Get missed heartbeat count
    missed = _get_missed_heartbeat_count(agent_id)
    result["details"]["missed_heartbeats"] = missed
    
    if missed < MISSED_HEARTBEATS_THRESHOLD:
        result["details"]["skipped"] = f"Only {missed} missed heartbeats (threshold: {MISSED_HEARTBEATS_THRESHOLD})"
        return result
    
    # Check 5: Verify process is actually dead
    if await verify_process_alive(agent_id):
        result["details"]["skipped"] = "Process is still running"
        return result
    
    # Check 6: Rate limit restarts
    restart_count = await get_restart_count(agent_id)
    result["details"]["recent_restarts"] = restart_count
    
    if restart_count >= MAX_RESTARTS_PER_HOUR:
        result["action"] = "blocked"
        result["error"] = f"Max restarts ({MAX_RESTARTS_PER_HOUR}) reached in last hour"
        
        # Alert CEO - too many restarts
        _send_ceo_alert(
            f"[SENTINEL] Restart Limit: {agent_id}",
            f"Agent {agent_id} has been restarted {restart_count} times in the last hour.\nManual intervention required."
        )
        return result
    
    # All checks passed - attempt restart
    result["action"] = "restart"
    
    host = AGENT_HOSTS.get(agent_id)
    service = AGENT_SERVICES.get(agent_id)
    
    if agent_id == "david-bishop":
        cmd = f"systemctl --user restart {service}"
    else:
        cmd = f"sudo systemctl restart {service}"
    
    success, output = _ssh_command(host, cmd)
    
    # Log restart attempt
    db = get_db()
    db.execute("""
        INSERT INTO restart_log (agent_id, success, method, notes)
        VALUES (?, ?, ?, ?)
    """, (agent_id, 1 if success else 0, "systemctl", output[:200]))
    db.commit()
    db.close()
    
    if success:
        # Wait and verify
        import time
        time.sleep(5)  # Wait for service to start
        
        if await check_health_endpoint(agent_id):
            result["success"] = True
            result["details"]["health_check"] = "passed"
            
            # Update agent status
            db = get_db()
            db.execute("UPDATE agents SET status = 'healthy' WHERE agent_id = ?", (agent_id,))
            db.commit()
            db.close()
            
            log.info(f"Agent {agent_id} restarted successfully")
        else:
            result["details"]["health_check"] = "failed"
            
            # Alert CEO - restart didn't work
            _send_ceo_alert(
                f"[SENTINEL] Restart Failed: {agent_id}",
                f"Agent {agent_id} was restarted but health check failed.\nManual intervention required."
            )
            
            # Update status to failed
            db = get_db()
            db.execute("UPDATE agents SET status = 'failed' WHERE agent_id = ?", (agent_id,))
            db.commit()
            db.close()
    else:
        result["error"] = output[:200]
        
        # Alert CEO - restart command failed
        _send_ceo_alert(
            f"[SENTINEL] Restart Error: {agent_id}",
            f"Failed to restart {agent_id}.\nError: {output[:200]}"
        )
    
    return result


# Ensure tables exist
def init_tables():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS restart_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            attempted_at TEXT DEFAULT (datetime('now')),
            success INTEGER DEFAULT 0,
            method TEXT,
            notes TEXT
        )
    """)
    db.commit()
    db.close()


if __name__ == "__main__":
    init_tables()
    print("Auto-restart tables initialized")
