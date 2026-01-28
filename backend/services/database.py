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
        ("Cobalt", "192.168.65.243", "cobaltadmin", "linux", "homebase.rize.bm", "cobalt-ssh.rize.bm", "Homebase Dashboard"),
        ("Relay", "192.168.65.248", "relayadmin", "linux", "relay.rize.bm", "relay-ssh.rize.bm", "AI Orchestration"),
        ("BPS AI", "192.168.65.246", "bpsaiadmin", "linux", "bpsai.rize.bm", "bpsai-ssh.rize.bm", "Police Case Management"),
        ("Context Hub", "192.168.65.247", "contextadmin", "linux", "context.rize.bm", "context-ssh.rize.bm", "IT Support Platform"),
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
