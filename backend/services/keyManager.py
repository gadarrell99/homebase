"""
Key Management Service
Secure credential storage using Fernet encryption.
"""

import os
import base64
from datetime import datetime
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .database import get_connection, DB_PATH


# Key derivation settings
SALT_FILE = os.path.join(os.path.dirname(DB_PATH), ".homebase_salt")
KEY_FILE = os.path.join(os.path.dirname(DB_PATH), ".homebase_key")


def _get_or_create_salt() -> bytes:
    """Get or create a salt for key derivation."""
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, 'rb') as f:
            return f.read()
    else:
        salt = os.urandom(16)
        with open(SALT_FILE, 'wb') as f:
            f.write(salt)
        os.chmod(SALT_FILE, 0o600)
        return salt


def _get_or_create_master_key() -> bytes:
    """Get or create the master encryption key."""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        # Generate a new Fernet key
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        os.chmod(KEY_FILE, 0o600)
        return key


def _get_fernet() -> Fernet:
    """Get a Fernet instance for encryption/decryption."""
    key = _get_or_create_master_key()
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value."""
    f = _get_fernet()
    encrypted = f.encrypt(plaintext.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')


def decrypt_value(encrypted: str) -> str:
    """Decrypt an encrypted value."""
    f = _get_fernet()
    encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode('utf-8'))
    decrypted = f.decrypt(encrypted_bytes)
    return decrypted.decode('utf-8')


def store_credential(name: str, cred_type: str, value: str, server_id: Optional[int] = None, description: Optional[str] = None) -> dict:
    """
    Store a new credential with encryption.
    
    Args:
        name: Unique name for the credential
        cred_type: Type of credential (ssh_key, api_key, password, token)
        value: The secret value to store
        server_id: Optional server association
        description: Optional description
    
    Returns:
        The stored credential metadata (without the value)
    """
    encrypted_value = encrypt_value(value)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if credential already exists
        cursor.execute("SELECT id FROM credentials WHERE name = ?", (name,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            cursor.execute('''
                UPDATE credentials 
                SET encrypted_value = ?, type = ?, server_id = ?, description = ?, 
                    updated_at = CURRENT_TIMESTAMP, last_rotated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            ''', (encrypted_value, cred_type, server_id, description, name))
            cred_id = existing['id']
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO credentials (name, type, encrypted_value, server_id, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, cred_type, encrypted_value, server_id, description))
            cred_id = cursor.lastrowid
        
        conn.commit()
        
        # Log the access
        log_credential_access(cred_id, "store", "system")
        
        return {
            "id": cred_id,
            "name": name,
            "type": cred_type,
            "server_id": server_id,
            "description": description,
            "stored_at": datetime.utcnow().isoformat()
        }


def get_credential(name: str) -> Optional[str]:
    """
    Retrieve and decrypt a credential by name.
    
    Args:
        name: The credential name
    
    Returns:
        The decrypted value, or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, encrypted_value FROM credentials WHERE name = ?", (name,))
        row = cursor.fetchone()
        
        if row:
            # Update last used timestamp
            cursor.execute(
                "UPDATE credentials SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
                (row['id'],)
            )
            conn.commit()
            
            # Log the access
            log_credential_access(row['id'], "retrieve", "system")
            
            return decrypt_value(row['encrypted_value'])
        
        return None


def rotate_credential(cred_id: int, new_value: str) -> dict:
    """
    Rotate a credential with a new value.
    
    Args:
        cred_id: The credential ID
        new_value: The new secret value
    
    Returns:
        Updated credential metadata
    """
    encrypted_value = encrypt_value(new_value)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE credentials 
            SET encrypted_value = ?, last_rotated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (encrypted_value, cred_id))
        
        cursor.execute("SELECT name, type FROM credentials WHERE id = ?", (cred_id,))
        row = cursor.fetchone()
        
        conn.commit()
        
        # Log the rotation
        log_credential_access(cred_id, "rotate", "system")
        
        return {
            "id": cred_id,
            "name": row['name'] if row else None,
            "type": row['type'] if row else None,
            "rotated_at": datetime.utcnow().isoformat()
        }


def list_credentials() -> list[dict]:
    """
    List all credentials with metadata (NOT values).
    
    Returns:
        List of credential metadata
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.type, c.server_id, c.description,
                   c.last_rotated_at, c.last_used_at, c.created_at,
                   s.name as server_name
            FROM credentials c
            LEFT JOIN servers s ON c.server_id = s.id
            ORDER BY c.name
        ''')
        
        return [dict(row) for row in cursor.fetchall()]


def delete_credential(name: str) -> bool:
    """Delete a credential by name."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get ID first for logging
        cursor.execute("SELECT id FROM credentials WHERE name = ?", (name,))
        row = cursor.fetchone()
        
        if row:
            log_credential_access(row['id'], "delete", "system")
            cursor.execute("DELETE FROM credentials WHERE name = ?", (name,))
            conn.commit()
            return True
        
        return False


def log_credential_access(credential_id: int, action: str, user: str, ip_address: Optional[str] = None):
    """
    Log access to a credential.
    
    Args:
        credential_id: The credential ID
        action: The action performed (store, retrieve, rotate, delete)
        user: The user or system that accessed
        ip_address: Optional IP address
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO credential_access_logs (credential_id, action, user, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (credential_id, action, user, ip_address))
        conn.commit()


def get_credential_access_logs(credential_id: Optional[int] = None, limit: int = 100) -> list[dict]:
    """
    Get credential access logs.
    
    Args:
        credential_id: Optional filter by credential
        limit: Maximum number of logs to return
    
    Returns:
        List of access log entries
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if credential_id:
            cursor.execute('''
                SELECT l.*, c.name as credential_name
                FROM credential_access_logs l
                JOIN credentials c ON l.credential_id = c.id
                WHERE l.credential_id = ?
                ORDER BY l.created_at DESC
                LIMIT ?
            ''', (credential_id, limit))
        else:
            cursor.execute('''
                SELECT l.*, c.name as credential_name
                FROM credential_access_logs l
                JOIN credentials c ON l.credential_id = c.id
                ORDER BY l.created_at DESC
                LIMIT ?
            ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
