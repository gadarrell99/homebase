"""
Authentication Service
TOTP-based 2FA with session management.
"""

import os
import secrets
import hashlib
import base64
import time
import io
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pyotp
import qrcode
from pydantic import BaseModel
from .database import get_connection, DB_PATH
from .keyManager import encrypt_value, decrypt_value


# Session settings
SESSION_DURATION_HOURS = 24
REMEMBER_DEVICE_DAYS = 30
BACKUP_CODE_COUNT = 10


def init_auth_tables():
    """Initialize authentication tables."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email TEXT,
                totp_secret_encrypted TEXT,
                totp_enabled BOOLEAN DEFAULT FALSE,
                totp_verified BOOLEAN DEFAULT FALSE,
                backup_codes_encrypted TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT NOT NULL UNIQUE,
                device_fingerprint TEXT,
                ip_address TEXT,
                user_agent TEXT,
                is_trusted_device BOOLEAN DEFAULT FALSE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Trusted devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trusted_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_token TEXT NOT NULL UNIQUE,
                device_fingerprint TEXT,
                device_name TEXT,
                ip_address TEXT,
                user_agent TEXT,
                expires_at TIMESTAMP NOT NULL,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Auth logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        print("[Auth] Tables initialized")


def hash_password(password: str) -> str:
    """Hash password with salt."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{pwd_hash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    try:
        salt, stored_hash = password_hash.split(':')
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return pwd_hash.hex() == stored_hash
    except:
        return False


def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def generate_qr_code(secret: str, username: str, issuer: str = "Homebase") -> str:
    """Generate QR code as base64 PNG."""
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=username, issuer_name=issuer)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
    """Verify TOTP code."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> list:
    """Generate backup codes."""
    codes = []
    for _ in range(count):
        code = '-'.join([secrets.token_hex(2).upper() for _ in range(3)])
        codes.append(code)
    return codes


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(64)


def generate_device_token() -> str:
    """Generate a device trust token."""
    return secrets.token_urlsafe(48)


# User Management
def create_user(username: str, password: str, email: str = None) -> dict:
    """Create a new user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise ValueError("Username already exists")
        
        password_hash = hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, email)
            VALUES (?, ?, ?)
        ''', (username, password_hash, email))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        log_auth_action(user_id, username, "user_created", True)
        
        return {"id": user_id, "username": username, "email": email}


def get_user(username: str) -> Optional[dict]:
    """Get user by username."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, email, password_hash, totp_secret_encrypted, 
                   totp_enabled, totp_verified, backup_codes_encrypted
            FROM users WHERE username = ?
        ''', (username,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, email, totp_enabled, totp_verified
            FROM users WHERE id = ?
        ''', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# 2FA Setup
def setup_2fa(user_id: int) -> dict:
    """Initialize 2FA setup - generates secret and QR code."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, totp_enabled FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise ValueError("User not found")
        
        # Generate new secret
        secret = generate_totp_secret()
        encrypted_secret = encrypt_value(secret)
        backup_codes = generate_backup_codes()
        encrypted_codes = encrypt_value(','.join(backup_codes))
        
        cursor.execute('''
            UPDATE users 
            SET totp_secret_encrypted = ?, backup_codes_encrypted = ?, 
                totp_enabled = FALSE, totp_verified = FALSE
            WHERE id = ?
        ''', (encrypted_secret, encrypted_codes, user_id))
        conn.commit()
        
        qr_code = generate_qr_code(secret, user['username'])
        
        return {
            "qr_code": qr_code,
            "secret": secret,  # For manual entry
            "backup_codes": backup_codes
        }


def verify_2fa_setup(user_id: int, code: str) -> bool:
    """Verify 2FA setup with initial code."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT totp_secret_encrypted FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user or not user['totp_secret_encrypted']:
            return False
        
        secret = decrypt_value(user['totp_secret_encrypted'])
        
        if verify_totp(secret, code):
            cursor.execute('''
                UPDATE users SET totp_enabled = TRUE, totp_verified = TRUE
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            log_auth_action(user_id, None, "2fa_enabled", True)
            return True
        
        return False


# Authentication
def authenticate_password(username: str, password: str, ip_address: str = None, user_agent: str = None) -> Tuple[bool, Optional[dict]]:
    """Authenticate user with password (step 1)."""
    user = get_user(username)
    
    if not user:
        log_auth_action(None, username, "login_failed", False, ip_address, user_agent, "User not found")
        return False, None
    
    if not verify_password(password, user['password_hash']):
        log_auth_action(user['id'], username, "login_failed", False, ip_address, user_agent, "Invalid password")
        return False, None
    
    log_auth_action(user['id'], username, "password_verified", True, ip_address, user_agent)
    
    return True, {
        "id": user['id'],
        "username": user['username'],
        "totp_enabled": user['totp_enabled'],
        "requires_2fa": user['totp_enabled']
    }


def authenticate_2fa(user_id: int, code: str, ip_address: str = None, user_agent: str = None, 
                     trust_device: bool = False, device_fingerprint: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """Authenticate with 2FA code (step 2). Returns (success, session_token, device_token)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, totp_secret_encrypted, backup_codes_encrypted, totp_enabled
            FROM users WHERE id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return False, None, None
        
        if not user['totp_enabled']:
            # 2FA not enabled, create session directly
            session_token = create_session(user_id, ip_address, user_agent, device_fingerprint)
            return True, session_token, None
        
        secret = decrypt_value(user['totp_secret_encrypted'])
        code = code.replace('-', '').replace(' ', '')
        
        # Try TOTP first
        if verify_totp(secret, code):
            session_token = create_session(user_id, ip_address, user_agent, device_fingerprint)
            device_token = None
            
            if trust_device:
                device_token = create_trusted_device(user_id, ip_address, user_agent, device_fingerprint)
            
            log_auth_action(user_id, user['username'], "2fa_verified", True, ip_address, user_agent)
            return True, session_token, device_token
        
        # Try backup codes
        if user['backup_codes_encrypted']:
            codes = decrypt_value(user['backup_codes_encrypted']).split(',')
            if code.upper() in [c.upper() for c in codes]:
                # Remove used backup code
                codes = [c for c in codes if c.upper() != code.upper()]
                encrypted_codes = encrypt_value(','.join(codes))
                cursor.execute('''
                    UPDATE users SET backup_codes_encrypted = ? WHERE id = ?
                ''', (encrypted_codes, user_id))
                conn.commit()
                
                session_token = create_session(user_id, ip_address, user_agent, device_fingerprint)
                device_token = None
                
                if trust_device:
                    device_token = create_trusted_device(user_id, ip_address, user_agent, device_fingerprint)
                
                log_auth_action(user_id, user['username'], "backup_code_used", True, ip_address, user_agent,
                               f"{len(codes)} codes remaining")
                return True, session_token, device_token
        
        log_auth_action(user_id, user['username'], "2fa_failed", False, ip_address, user_agent)
        return False, None, None


def check_trusted_device(user_id: int, device_token: str, device_fingerprint: str = None) -> bool:
    """Check if device is trusted and skip 2FA if so."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, device_fingerprint, expires_at FROM trusted_devices
            WHERE user_id = ? AND device_token = ? AND expires_at > datetime('now')
        ''', (user_id, device_token))
        device = cursor.fetchone()
        
        if device:
            # Update last used
            cursor.execute('''
                UPDATE trusted_devices SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (device['id'],))
            conn.commit()
            return True
        
        return False


def create_session(user_id: int, ip_address: str = None, user_agent: str = None, 
                   device_fingerprint: str = None) -> str:
    """Create a new session."""
    session_token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (user_id, session_token, device_fingerprint, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, session_token, device_fingerprint, ip_address, user_agent, expires_at))
        conn.commit()
    
    return session_token


def create_trusted_device(user_id: int, ip_address: str = None, user_agent: str = None,
                          device_fingerprint: str = None, device_name: str = None) -> str:
    """Create a trusted device entry."""
    device_token = generate_device_token()
    expires_at = datetime.utcnow() + timedelta(days=REMEMBER_DEVICE_DAYS)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trusted_devices (user_id, device_token, device_fingerprint, device_name, 
                                         ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, device_token, device_fingerprint, device_name, ip_address, user_agent, expires_at))
        conn.commit()
    
    return device_token


def validate_session(session_token: str) -> Optional[dict]:
    """Validate session and return user info."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.user_id, s.expires_at, u.username, u.email, u.totp_enabled
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ? AND s.expires_at > datetime('now')
        ''', (session_token,))
        row = cursor.fetchone()
        
        if row:
            return {
                "user_id": row['user_id'],
                "username": row['username'],
                "email": row['email'],
                "totp_enabled": row['totp_enabled']
            }
        return None


def logout(session_token: str):
    """Invalidate a session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
        conn.commit()


def log_auth_action(user_id: int, username: str, action: str, success: bool, 
                    ip_address: str = None, user_agent: str = None, details: str = None):
    """Log authentication action."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO auth_logs (user_id, username, action, success, ip_address, user_agent, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, action, success, ip_address, user_agent, details))
        conn.commit()


def get_auth_logs(user_id: int = None, limit: int = 100) -> list:
    """Get authentication logs."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute('''
                SELECT * FROM auth_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
            ''', (user_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM auth_logs ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_user_devices(user_id: int) -> list:
    """Get user's trusted devices."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, device_name, ip_address, user_agent, last_used_at, expires_at, created_at
            FROM trusted_devices
            WHERE user_id = ? AND expires_at > datetime('now')
            ORDER BY last_used_at DESC
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def revoke_device(user_id: int, device_id: int) -> bool:
    """Revoke a trusted device."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM trusted_devices WHERE id = ? AND user_id = ?
        ''', (device_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def regenerate_backup_codes(user_id: int) -> list:
    """Regenerate backup codes for a user."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        backup_codes = generate_backup_codes()
        encrypted_codes = encrypt_value(','.join(backup_codes))
        
        cursor.execute('''
            UPDATE users SET backup_codes_encrypted = ? WHERE id = ?
        ''', (encrypted_codes, user_id))
        conn.commit()
        
        log_auth_action(user_id, None, "backup_codes_regenerated", True)
        
        return backup_codes


def send_new_device_notification(user_id: int, ip_address: str, user_agent: str):
    """Send email notification for new device login."""
    import subprocess
    
    user = get_user_by_id(user_id)
    if not user or not user.get('email'):
        return
    
    subject = f"[Homebase] New device login for {user['username']}"
    body = f"""A new device logged into your Homebase account.

Username: {user['username']}
IP Address: {ip_address or 'Unknown'}
Device: {user_agent or 'Unknown'}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

If this was not you, please change your password immediately and review your trusted devices.
"""
    
    try:
        subprocess.run(['/home/rizeadmin/bin/notify', subject, body], check=True, capture_output=True)
    except Exception as e:
        print(f"[Auth] Failed to send notification: {e}")


# Initialize tables on import
init_auth_tables()

# Create default admin if no users exist
def ensure_admin_exists():
    """Ensure at least one admin user exists."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        row = cursor.fetchone()
        if row['count'] == 0:
            # Create default admin with secure random password
            default_password = secrets.token_urlsafe(16)
            create_user('admin', default_password, 'artiedarrell@gmail.com')
            print(f"[Auth] Default admin created with password: {default_password}")
            print("[Auth] Please change this password immediately!")
            return default_password
    return None

