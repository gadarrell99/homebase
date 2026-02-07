"""
Guardrails Service - AI Agent Behavior Enforcement
Checks requests against defined rules before allowing actions.
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("/home/rizeadmin/homebase/data/agents.db")

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db

def get_all_rules(enabled_only=True):
    """Get all guardrail rules."""
    db = get_db()
    query = "SELECT * FROM guardrail_rules"
    if enabled_only:
        query += " WHERE enabled = 1"
    query += " ORDER BY rule_type, rule_name"
    cur = db.execute(query)
    rules = [dict(row) for row in cur.fetchall()]
    db.close()
    return rules

def get_rule(rule_id):
    """Get a single rule by ID."""
    db = get_db()
    cur = db.execute("SELECT * FROM guardrail_rules WHERE id = ?", (rule_id,))
    row = cur.fetchone()
    db.close()
    return dict(row) if row else None

def check_rate_limit(agent_id, config):
    """Check if agent has exceeded rate limit."""
    db = get_db()
    max_requests = config.get('max_requests', 100)
    window_minutes = config.get('window_minutes', 60)
    
    cutoff = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()
    
    cur = db.execute("""
        SELECT COUNT(*) as count FROM request_log 
        WHERE agent_id = ? AND timestamp > ?
    """, (agent_id, cutoff))
    
    count = cur.fetchone()['count']
    db.close()
    
    if count >= max_requests:
        return False, f"Rate limit exceeded: {count}/{max_requests} requests in {window_minutes} min"
    return True, f"Rate OK: {count}/{max_requests}"

def check_action_block(request_text, config):
    """Check if request contains blocked patterns."""
    patterns = config.get('patterns', [])
    request_lower = request_text.lower()
    
    for pattern in patterns:
        if re.search(pattern.lower(), request_lower):
            return False, f"Blocked pattern detected: {pattern}"
    return True, "No blocked patterns"

def check_time_restrict(config):
    """Check if current time is in restricted hours."""
    blocked_hours = config.get('blocked_hours', [])
    # Use UTC for simplicity
    current_hour = datetime.utcnow().hour
    
    # Adjust for Bermuda (UTC-4 or UTC-3 DST)
    bermuda_hour = (current_hour - 4) % 24
    
    if bermuda_hour in blocked_hours:
        return False, f"Quiet hours active (hour {bermuda_hour} Bermuda time)"
    return True, "Within allowed hours"

def check_approval_required(request_text, config):
    """Check if request needs approval."""
    patterns = config.get('patterns', [])
    request_lower = request_text.lower()
    
    for pattern in patterns:
        if re.search(pattern.lower(), request_lower):
            return False, f"Approval required for: {pattern}"
    return True, "No approval needed"

def check_request(agent_id: str, request_text: str) -> dict:
    """
    Main guardrail check function.
    Returns: {allowed: bool, warnings: [], blocks: [], triggered_rules: []}
    """
    result = {
        'allowed': True,
        'warnings': [],
        'blocks': [],
        'triggered_rules': []
    }
    
    rules = get_all_rules(enabled_only=True)
    
    for rule in rules:
        # Skip rules for other agents
        if rule['agent_id'] and rule['agent_id'] != agent_id:
            continue
        # Skip if this is an agent-specific rule and we have a general one
        if not rule['agent_id']:
            # Check if there's an agent-specific override
            agent_rule = next((r for r in rules if r['agent_id'] == agent_id 
                              and r['rule_type'] == rule['rule_type']), None)
            if agent_rule:
                continue  # Use agent-specific rule instead
        
        config = json.loads(rule['config'])
        passed = True
        message = ""
        
        if rule['rule_type'] == 'rate_limit':
            passed, message = check_rate_limit(agent_id, config)
        elif rule['rule_type'] == 'action_block':
            passed, message = check_action_block(request_text, config)
        elif rule['rule_type'] == 'time_restrict':
            passed, message = check_time_restrict(config)
        elif rule['rule_type'] == 'approval_required':
            passed, message = check_approval_required(request_text, config)
        
        if not passed:
            trigger = {
                'rule_id': rule['id'],
                'rule_name': rule['rule_name'],
                'rule_type': rule['rule_type'],
                'severity': rule['severity'],
                'message': message
            }
            result['triggered_rules'].append(trigger)
            
            if rule['severity'] == 'block':
                result['blocks'].append(message)
                result['allowed'] = False
            elif rule['severity'] == 'warning':
                result['warnings'].append(message)
            elif rule['severity'] == 'kill':
                result['blocks'].append(f"KILL TRIGGER: {message}")
                result['allowed'] = False
    
    return result

def log_trigger(agent_id: str, rule_id: int, rule_name: str, 
                request_summary: str, action_taken: str, details: str = None):
    """Log a guardrail trigger event."""
    db = get_db()
    db.execute("""
        INSERT INTO guardrail_triggers 
        (agent_id, rule_id, rule_name, request_summary, action_taken, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (agent_id, rule_id, rule_name, request_summary, action_taken, details))
    db.commit()
    db.close()

def get_recent_triggers(limit=50):
    """Get recent guardrail trigger events."""
    db = get_db()
    cur = db.execute("""
        SELECT * FROM guardrail_triggers 
        ORDER BY timestamp DESC LIMIT ?
    """, (limit,))
    triggers = [dict(row) for row in cur.fetchall()]
    db.close()
    return triggers

def update_rule(rule_id: int, updates: dict, updated_by: str = 'web'):
    """Update a guardrail rule."""
    db = get_db()
    
    allowed_fields = ['rule_name', 'agent_id', 'rule_type', 'config', 
                      'severity', 'enabled']
    
    set_clauses = []
    values = []
    
    for field, value in updates.items():
        if field in allowed_fields:
            set_clauses.append(f"{field} = ?")
            values.append(value)
    
    if set_clauses:
        set_clauses.append("updated_at = datetime('now')")
        set_clauses.append("updated_by = ?")
        values.append(updated_by)
        values.append(rule_id)
        
        query = f"UPDATE guardrail_rules SET {', '.join(set_clauses)} WHERE id = ?"
        db.execute(query, values)
        db.commit()
    
    db.close()
    return True

def create_rule(rule_name: str, rule_type: str, config: dict, 
                agent_id: str = None, severity: str = 'warning',
                created_by: str = 'web'):
    """Create a new guardrail rule."""
    db = get_db()
    db.execute("""
        INSERT INTO guardrail_rules 
        (rule_name, agent_id, rule_type, config, severity, updated_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (rule_name, agent_id, rule_type, json.dumps(config), severity, created_by))
    db.commit()
    rule_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return rule_id

def delete_rule(rule_id: int):
    """Delete a guardrail rule."""
    db = get_db()
    db.execute("DELETE FROM guardrail_rules WHERE id = ?", (rule_id,))
    db.commit()
    db.close()
    return True
