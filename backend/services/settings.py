"""
Homebase Settings Service
Manages alert thresholds and notification settings
"""
import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'homebase.db')

# Default settings
DEFAULT_SETTINGS = {
    'cpu_threshold': 90,
    'memory_threshold': 90,
    'disk_threshold': 90,
    'cooldown_minutes': 15,
    'alert_recipients': 'artiedarrell@gmail.com',
    'alerts_enabled': True
}


def init_settings_table():
    """Create settings table if not exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Seed defaults if empty
    cursor.execute('SELECT COUNT(*) FROM settings')
    if cursor.fetchone()[0] == 0:
        for key, value in DEFAULT_SETTINGS.items():
            cursor.execute(
                'INSERT INTO settings (key, value) VALUES (?, ?)',
                (key, json.dumps(value) if not isinstance(value, str) else value)
            )
        conn.commit()
    
    conn.close()


def get_setting(key: str, default=None):
    """Get a single setting by key"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return row[0]
        return default if default is not None else DEFAULT_SETTINGS.get(key)
    except:
        return default if default is not None else DEFAULT_SETTINGS.get(key)


def get_all_settings() -> dict:
    """Get all settings as a dictionary"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT key, value, updated_at FROM settings')
        rows = cursor.fetchall()
        conn.close()
        
        settings = {}
        for key, value, updated_at in rows:
            try:
                settings[key] = json.loads(value)
            except json.JSONDecodeError:
                settings[key] = value
        
        # Fill in any missing defaults
        for key, default in DEFAULT_SETTINGS.items():
            if key not in settings:
                settings[key] = default
        
        return settings
    except Exception as e:
        return DEFAULT_SETTINGS.copy()


def update_setting(key: str, value) -> bool:
    """Update a single setting"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        ''', (key, value_str))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'Error updating setting {key}: {e}')
        return False


def update_settings(updates: dict) -> bool:
    """Update multiple settings at once"""
    success = True
    for key, value in updates.items():
        if not update_setting(key, value):
            success = False
    return success


# Initialize table on import
init_settings_table()
