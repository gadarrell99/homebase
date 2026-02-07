"""Request Tracker - Logs agent interactions for analysis"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agents.db"

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db

def log_request(agent_id, user_id, channel, request_summary, fulfilled, outcome=None, unfulfilled_reason=None, guardrail_triggered=None, response_time_ms=None, tokens_used=None):
    db = get_db()
    db.execute('''
        INSERT INTO request_log (agent_id, user_id, channel, request_summary, fulfilled, outcome, unfulfilled_reason, guardrail_triggered, response_time_ms, tokens_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (agent_id, user_id, channel, request_summary, fulfilled, outcome, unfulfilled_reason, guardrail_triggered, response_time_ms, tokens_used))
    db.commit()
    db.close()
    return True

def get_requests(agent_id=None, hours=24, limit=100):
    db = get_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    if agent_id:
        rows = db.execute('SELECT * FROM request_log WHERE agent_id = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT ?', (agent_id, since, limit)).fetchall()
    else:
        rows = db.execute('SELECT * FROM request_log WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?', (since, limit)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def get_unfulfilled_summary(hours=24):
    db = get_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    rows = db.execute('''
        SELECT unfulfilled_reason, COUNT(*) as count 
        FROM request_log 
        WHERE fulfilled = 'no' AND timestamp > ? 
        GROUP BY unfulfilled_reason 
        ORDER BY count DESC
    ''', (since,)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def get_stats(agent_id=None, hours=24):
    db = get_db()
    since = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    q = 'SELECT COUNT(*) as total, SUM(CASE WHEN fulfilled="yes" THEN 1 ELSE 0 END) as fulfilled, AVG(response_time_ms) as avg_response_ms, SUM(tokens_used) as total_tokens FROM request_log WHERE timestamp > ?'
    params = [since]
    if agent_id:
        q += ' AND agent_id = ?'
        params.append(agent_id)
    row = db.execute(q, params).fetchone()
    db.close()
    return dict(row) if row else {}
