"""
Log Collector Service
Fetches and stores logs from remote servers.
"""

import asyncio
import asyncssh
import re
from datetime import datetime
from typing import Optional

from .database import get_connection, get_server_by_ip


# Common error patterns to detect
ERROR_PATTERNS = [
    (r'error', 'error'),
    (r'ERROR', 'error'),
    (r'exception', 'exception'),
    (r'Exception', 'exception'),
    (r'CRITICAL', 'critical'),
    (r'fatal', 'fatal'),
    (r'FATAL', 'fatal'),
    (r'failed', 'failed'),
    (r'Failed', 'failed'),
    (r'timeout', 'timeout'),
    (r'Timeout', 'timeout'),
    (r'refused', 'connection_refused'),
    (r'denied', 'access_denied'),
    (r'OOM', 'out_of_memory'),
    (r'out of memory', 'out_of_memory'),
    (r'segmentation fault', 'crash'),
    (r'killed', 'process_killed'),
]


async def fetch_logs(server_ip: str, user: str, service: str, lines: int = 100) -> dict:
    """
    SSH to a server and get logs for a service.
    
    Args:
        server_ip: Server IP address
        user: SSH username
        service: Service name (for journalctl) or log file path
        lines: Number of lines to fetch
    
    Returns:
        Dict with logs and metadata
    """
    result = {
        "server_ip": server_ip,
        "service": service,
        "fetched_at": datetime.utcnow().isoformat(),
        "lines": [],
        "line_count": 0,
        "error": None,
    }
    
    try:
        async with asyncssh.connect(
            server_ip,
            username=user,
            known_hosts=None,
            connect_timeout=15
        ) as conn:
            # Check if service name looks like a file path
            if service.startswith('/'):
                # It's a log file path
                cmd = f"sudo tail -{lines} {service} 2>/dev/null"
            else:
                # It's a systemd service
                cmd = f"journalctl -u {service} -n {lines} --no-pager 2>/dev/null"
            
            log_result = await conn.run(cmd, check=False)
            
            if log_result.exit_status == 0:
                result["lines"] = log_result.stdout.strip().split('\n')
                result["line_count"] = len(result["lines"])
            else:
                # Try alternative: pm2 logs
                pm2_result = await conn.run(
                    f"pm2 logs {service} --lines {lines} --nostream 2>/dev/null",
                    check=False
                )
                if pm2_result.exit_status == 0:
                    result["lines"] = pm2_result.stdout.strip().split('\n')
                    result["line_count"] = len(result["lines"])
                else:
                    result["error"] = f"Could not fetch logs for {service}"
                    
    except Exception as e:
        result["error"] = str(e)
    
    return result


def detect_error_patterns(log_text: str) -> list[dict]:
    """
    Scan log text for common error patterns.
    
    Args:
        log_text: The log content to analyze
    
    Returns:
        List of detected errors with context
    """
    errors = []
    lines = log_text.split('\n')
    
    for i, line in enumerate(lines):
        for pattern, error_type in ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                errors.append({
                    "type": error_type,
                    "line_number": i + 1,
                    "line": line.strip()[:500],  # Limit line length
                    "pattern": pattern,
                })
                break  # Only match first pattern per line
    
    return errors


def store_log_snapshot(server_id: int, service: str, logs: list[str]) -> int:
    """
    Save a log snapshot to the database.
    
    Args:
        server_id: The server ID
        service: Service name
        logs: List of log lines
    
    Returns:
        The snapshot ID
    """
    log_content = '\n'.join(logs)
    errors = detect_error_patterns(log_content)
    error_count = len(errors)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO log_snapshots (server_id, service, log_content, error_count)
            VALUES (?, ?, ?, ?)
        ''', (server_id, service, log_content, error_count))
        conn.commit()
        return cursor.lastrowid


def get_recent_errors(hours: int = 24) -> list[dict]:
    """
    Query stored logs for recent errors.
    
    Args:
        hours: How far back to look
    
    Returns:
        List of errors with server and service info
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.*, s.name as server_name
            FROM log_snapshots ls
            JOIN servers s ON ls.server_id = s.id
            WHERE ls.captured_at >= datetime('now', ? || ' hours')
              AND ls.error_count > 0
            ORDER BY ls.captured_at DESC
            LIMIT 100
        ''', (-hours,))
        
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Parse errors from stored log content
            if row_dict.get('log_content'):
                row_dict['errors'] = detect_error_patterns(row_dict['log_content'])
                # Don't return full log content, just summary
                del row_dict['log_content']
            results.append(row_dict)
        
        return results


def get_log_snapshot(snapshot_id: int) -> Optional[dict]:
    """Get a specific log snapshot by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ls.*, s.name as server_name
            FROM log_snapshots ls
            JOIN servers s ON ls.server_id = s.id
            WHERE ls.id = ?
        ''', (snapshot_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


async def collect_logs_from_server(server_ip: str, user: str, services: list[str]) -> list[dict]:
    """
    Collect logs from multiple services on a server.
    
    Args:
        server_ip: Server IP
        user: SSH username
        services: List of services to collect from
    
    Returns:
        List of log results
    """
    tasks = [fetch_logs(server_ip, user, svc) for svc in services]
    results = await asyncio.gather(*tasks)
    return results


# Common services to check per server type
DEFAULT_SERVICES = {
    "default": ["ssh", "nginx"],
    "relay": ["relay", "relay-worker"],
    "homebase": ["homebase"],
    "bpsai": ["bpsai"],
    "context": ["nexus"],
    "dockyard": ["dockyard"],
    "vector": ["bet-transport"],
}


async def collect_all_logs(server_ip: str, user: str, server_name: str = "default") -> list[dict]:
    """
    Collect logs from all relevant services on a server.
    
    Args:
        server_ip: Server IP
        user: SSH username
        server_name: Server name for service mapping
    
    Returns:
        Combined log results
    """
    # Get services for this server type
    server_key = server_name.lower().replace(" ", "")
    services = DEFAULT_SERVICES.get(server_key, DEFAULT_SERVICES["default"])
    
    results = await collect_logs_from_server(server_ip, user, services)
    
    # Store snapshots in database
    server = get_server_by_ip(server_ip)
    if server:
        for result in results:
            if result.get("lines") and not result.get("error"):
                store_log_snapshot(server["id"], result["service"], result["lines"])
    
    return results


async def analyze_logs(server_ip: str, user: str, service: str, lines: int = 200) -> dict:
    """
    Fetch and analyze logs for errors.
    
    Args:
        server_ip: Server IP
        user: SSH username
        service: Service name
        lines: Number of lines to analyze
    
    Returns:
        Analysis results with error summary
    """
    logs = await fetch_logs(server_ip, user, service, lines)
    
    if logs.get("error"):
        return logs
    
    log_text = '\n'.join(logs["lines"])
    errors = detect_error_patterns(log_text)
    
    # Group errors by type
    error_summary = {}
    for error in errors:
        error_type = error["type"]
        if error_type not in error_summary:
            error_summary[error_type] = {"count": 0, "examples": []}
        error_summary[error_type]["count"] += 1
        if len(error_summary[error_type]["examples"]) < 3:
            error_summary[error_type]["examples"].append(error["line"][:200])
    
    return {
        **logs,
        "analysis": {
            "total_errors": len(errors),
            "by_type": error_summary,
        }
    }
