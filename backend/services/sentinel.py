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
