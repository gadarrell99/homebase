"""
Sentinel Comms Gateway
Routes all agent outbound communications for PII scanning and compliance.

PII Patterns Detected:
- SSN (XXX-XX-XXXX)
- Credit cards (16-digit)
- Phone numbers (US/Bermuda)
- Email addresses (flagged, not redacted)
- National ID numbers
"""
import os
import re
import sqlite3
import subprocess
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

log = logging.getLogger("sentinel.comms_gateway")

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agents.db"

# PII Detection Patterns
PII_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "phone_bm": r"\b\+?1?[\s-]?441[\s-]?\d{3}[\s-]?\d{4}\b",
    "phone_us": r"\b\+?1?[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}\b",
    "national_id": r"\b[A-Z]{2}\d{6,9}\b",  # Common national ID format
}

# Patterns to flag but not redact
FLAG_ONLY_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
}


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def scan_for_pii(text: str) -> List[Dict[str, Any]]:
    """
    Scan text for PII patterns.
    Returns list of findings with pattern type and location.
    """
    findings = []
    
    for pattern_name, pattern in PII_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append({
                "type": pattern_name,
                "match": match.group(),
                "start": match.start(),
                "end": match.end(),
                "action": "redact",
            })
    
    # Flag-only patterns
    for pattern_name, pattern in FLAG_ONLY_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append({
                "type": pattern_name,
                "match": match.group(),
                "start": match.start(),
                "end": match.end(),
                "action": "flag",
            })
    
    # Sort by start position (descending for safe replacement)
    findings.sort(key=lambda x: x["start"], reverse=True)
    return findings


def redact_pii(text: str, findings: List[Dict[str, Any]]) -> str:
    """
    Replace PII with [REDACTED] markers.
    Only redacts items with action='redact'.
    """
    result = text
    for finding in findings:
        if finding["action"] == "redact":
            result = result[:finding["start"]] + f"[REDACTED-{finding['type'].upper()}]" + result[finding["end"]:]
    return result


def _log_pii_scan(
    agent_id: str,
    findings: List[Dict],
    action_taken: str,
    destination: str,
) -> None:
    """Log PII scan result to database."""
    db = get_db()
    patterns = json.dumps([{"type": f["type"], "action": f["action"]} for f in findings])
    db.execute("""
        INSERT INTO pii_scan_log (agent_id, pii_found, patterns, action_taken, destination)
        VALUES (?, ?, ?, ?, ?)
    """, (agent_id, len(findings), patterns, action_taken, destination))
    db.commit()
    db.close()


def _ssh_command(host: str, cmd: str, timeout: int = 30) -> Tuple[bool, str]:
    """Execute SSH command."""
    full_cmd = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host, cmd]
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


async def scan_and_send_email(
    from_agent: str,
    to_address: str,
    subject: str,
    body: str,
) -> Dict[str, Any]:
    """
    Scan email body for PII, redact if needed, and send.
    Returns result dict with scan findings and send status.
    """
    result = {
        "from_agent": from_agent,
        "to_address": to_address,
        "subject": subject,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pii_found": False,
        "redacted": False,
        "sent": False,
    }
    
    # Scan for PII
    findings = scan_for_pii(body)
    
    if findings:
        result["pii_found"] = True
        result["findings"] = [
            {"type": f["type"], "action": f["action"]} 
            for f in findings
        ]
        
        # Separate redact vs flag
        redact_count = sum(1 for f in findings if f["action"] == "redact")
        flag_count = sum(1 for f in findings if f["action"] == "flag")
        
        if redact_count > 0:
            result["redacted"] = True
            body = redact_pii(body, findings)
            log.warning(f"PII redacted from {from_agent} email to {to_address}: {redact_count} items")
        
        if flag_count > 0:
            log.info(f"PII flagged (not redacted) in {from_agent} email: {flag_count} items")
        
        # Log to database
        _log_pii_scan(
            from_agent,
            findings,
            "redacted" if redact_count > 0 else "flagged",
            to_address,
        )
    else:
        # Log clean scan
        _log_pii_scan(from_agent, [], "clean", to_address)
    
    # Send email via David's send-email.py script
    # Escape quotes in subject and body
    safe_subject = subject.replace("'", "'\\''" )
    safe_body = body.replace("'", "'\\''")
    
    cmd = f"python3 ~/scripts/send-email.py {from_agent}@rize.bm {to_address} '{safe_subject}' '{safe_body}'"
    success, output = _ssh_command("agents@192.168.65.241", cmd, timeout=60)
    
    result["sent"] = success
    if not success:
        result["error"] = output[:200]
        log.error(f"Email send failed from {from_agent}: {output[:100]}")
    else:
        log.info(f"Email sent from {from_agent} to {to_address}")
    
    return result


async def scan_text(agent_id: str, text: str) -> Dict[str, Any]:
    """
    Scan any text for PII (for general use, not just email).
    Returns scan results without sending anything.
    """
    findings = scan_for_pii(text)
    
    result = {
        "agent_id": agent_id,
        "text_length": len(text),
        "pii_found": len(findings) > 0,
        "findings": [
            {"type": f["type"], "action": f["action"], "preview": f["match"][:4] + "***"} 
            for f in findings
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    if findings:
        _log_pii_scan(agent_id, findings, "scanned", "internal")
    
    return result


async def get_pii_report(agent_id: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
    """Get PII scan statistics for an agent or all agents."""
    db = get_db()
    
    if agent_id:
        rows = db.execute("""
            SELECT agent_id, pii_found, action_taken, destination, scanned_at
            FROM pii_scan_log 
            WHERE agent_id = ? AND scanned_at > datetime('now', ?)
            ORDER BY scanned_at DESC
        """, (agent_id, f"-{days} days")).fetchall()
    else:
        rows = db.execute("""
            SELECT agent_id, pii_found, action_taken, destination, scanned_at
            FROM pii_scan_log 
            WHERE scanned_at > datetime('now', ?)
            ORDER BY scanned_at DESC
        """, (f"-{days} days",)).fetchall()
    
    db.close()
    
    total_scans = len(rows)
    pii_detections = sum(1 for r in rows if r["pii_found"] > 0)
    redactions = sum(1 for r in rows if r["action_taken"] == "redacted")
    
    return {
        "period_days": days,
        "agent_id": agent_id,
        "total_scans": total_scans,
        "pii_detections": pii_detections,
        "redactions": redactions,
        "detection_rate": round(pii_detections / total_scans * 100, 1) if total_scans > 0 else 0,
        "recent_scans": [dict(r) for r in rows[:20]],
    }


# Ensure tables exist
def init_tables():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS pii_scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            scanned_at TEXT DEFAULT (datetime('now')),
            pii_found INTEGER DEFAULT 0,
            patterns TEXT,
            action_taken TEXT,
            destination TEXT
        )
    """)
    db.commit()
    db.close()


if __name__ == "__main__":
    init_tables()
    print("Comms gateway tables initialized")
    
    # Test PII detection
    test_text = """
    Customer SSN: 123-45-6789
    Card: 4111-1111-1111-1111
    Phone: +1-441-555-1234
    Email: test@example.com
    """
    
    findings = scan_for_pii(test_text)
    print(f"\nTest scan found {len(findings)} items:")
    for f in findings:
        print(f"  - {f['type']}: {f['match'][:10]}... ({f['action']})")
    
    redacted = redact_pii(test_text, findings)
    print(f"\nRedacted text:\n{redacted}")
