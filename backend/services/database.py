"""
Database Service
SQLite database for Homebase with migrations support.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "homebase.db")


def get_db_path() -> str:
    """Return the database file path."""
    return DB_PATH


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize the database with all required tables."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Servers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                ip TEXT NOT NULL,
                username TEXT NOT NULL,
                os TEXT DEFAULT 'linux',
                web_url TEXT,
                ssh_url TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                server_id INTEGER,
                path TEXT NOT NULL,
                version TEXT,
                description TEXT,
                has_readme BOOLEAN DEFAULT FALSE,
                has_git BOOLEAN DEFAULT FALSE,
                git_remote TEXT,
                last_scanned_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id),
                UNIQUE(server_id, path)
            )
        ''')
        
        # Credentials table (encrypted storage)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('ssh_key', 'api_key', 'password', 'token')),
                encrypted_value TEXT NOT NULL,
                server_id INTEGER,
                description TEXT,
                last_rotated_at TIMESTAMP,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        ''')
        
        # Credential access logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credential_access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                credential_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                user TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (credential_id) REFERENCES credentials(id)
            )
        ''')
        
        # Security scan results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                total_updates INTEGER DEFAULT 0,
                critical_updates INTEGER DEFAULT 0,
                failed_auth_count INTEGER DEFAULT 0,
                alerts TEXT,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        ''')
        
        # Log snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                log_content TEXT,
                error_count INTEGER DEFAULT 0,
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        ''')
        
        conn.commit()
        print(f"Database initialized at {DB_PATH}")


def seed_servers():
    """Seed the servers table with known infrastructure."""
    servers = [
        ("Relay", "192.168.65.248", "relayadmin", "linux", "relay.rize.bm", "relay-ssh.rize.bm", "AI Orchestration"),
        ("Demos", "192.168.65.246", "demos", "linux", "bpsai.rize.bm", "bpsai-ssh.rize.bm", "Demo Showcase Server"),
        ("Nexus", "192.168.65.247", "contextadmin", "linux", "context.rize.bm", "context-ssh.rize.bm", "IT Support Platform"),
        ("Dockyard", "192.168.65.252", "dockyardadmin", "linux", "dockyard-admin.rize.bm", "dockyard-ssh.rize.bm", "WiFi Captive Portal"),
        ("Vector", "192.168.65.249", "betadmin", "linux", "app.bet.bm", "vector-ssh.bet.bm", "BET Transport"),
        ("Claude Code", "192.168.65.245", "claudedevadmin", "linux", None, "claude-dev-ssh.rize.bm", "AI Worker Host"),
        ("Hyper-V", "192.168.65.253", "Administrator", "windows", None, "hyperv-ssh.rize.bm", "VM Host"),
    ]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        for server in servers:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO servers (name, ip, username, os, web_url, ssh_url, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', server)
            except sqlite3.IntegrityError:
                pass
        conn.commit()


def get_server_by_ip(ip: str) -> Optional[dict]:
    """Get server record by IP address."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE ip = ?", (ip,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_server_by_name(name: str) -> Optional[dict]:
    """Get server record by name."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_servers() -> list[dict]:
    """Get all servers."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]


# Initialize on import
if not os.path.exists(DB_PATH):
    init_database()
    seed_servers()


# Uptime Events Table
def init_uptime_tables():
    """Initialize uptime tracking tables"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uptime_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_name TEXT NOT NULL,
            server_ip TEXT NOT NULL,
            status TEXT NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_uptime_server_time
        ON uptime_events(server_name, recorded_at)
    ''')

    conn.commit()
    conn.close()
    print('[Uptime] Tables initialized')


def record_uptime_event(server_name: str, server_ip: str, status: str):
    """Record a status change event"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check last status
    cursor.execute('''
        SELECT status FROM uptime_events
        WHERE server_name = ?
        ORDER BY recorded_at DESC LIMIT 1
    ''', (server_name,))
    row = cursor.fetchone()
    last_status = row[0] if row else None

    # Only record if status changed
    if last_status != status:
        cursor.execute('''
            INSERT INTO uptime_events (server_name, server_ip, status)
            VALUES (?, ?, ?)
        ''', (server_name, server_ip, status))
        conn.commit()
        print(f'[Uptime] {server_name}: {last_status} -> {status}')

    conn.close()


def get_uptime_percentage(server_name: str, hours: int = 24) -> float:
    """Calculate uptime percentage for a server"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        SELECT status, recorded_at FROM uptime_events
        WHERE server_name = ? AND recorded_at > ?
        ORDER BY recorded_at ASC
    ''', (server_name, cutoff))

    events = cursor.fetchall()
    conn.close()

    if not events:
        return 100.0  # No events = assume online

    # Calculate uptime from events
    total_time = timedelta(hours=hours)
    downtime = timedelta()
    last_offline = None

    for status, timestamp in events:
        event_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        if status == 'offline' and last_offline is None:
            last_offline = event_time
        elif status == 'online' and last_offline is not None:
            downtime += event_time - last_offline
            last_offline = None

    # If still offline
    if last_offline:
        downtime += datetime.now() - last_offline

    uptime_seconds = total_time.total_seconds() - downtime.total_seconds()
    return max(0, min(100, (uptime_seconds / total_time.total_seconds()) * 100))


# Initialize on import
init_uptime_tables()
