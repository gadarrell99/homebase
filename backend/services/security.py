"""
Security Monitoring Service
Checks for OS updates, service status, and authentication logs.
"""

import asyncio
import asyncssh
import re
from typing import Optional
from datetime import datetime


async def check_os_updates(server_ip: str, user: str) -> dict:
    """Run apt list --upgradable to check for available updates."""
    result = {
        "server_ip": server_ip,
        "checked_at": datetime.utcnow().isoformat(),
        "total_updates": 0,
        "upgradable": [],
        "error": None,
    }
    
    try:
        async with asyncssh.connect(
            server_ip,
            username=user,
            known_hosts=None,
            connect_timeout=15
        ) as conn:
            # Update package lists quietly
            await conn.run("sudo apt-get update -qq 2>/dev/null", check=False)
            
            # Get upgradable packages
            update_result = await conn.run("apt list --upgradable 2>/dev/null", check=False)
            
            if update_result.exit_status == 0:
                lines = update_result.stdout.strip().split('\n')
                for line in lines:
                    if '/' in line and 'Listing...' not in line:
                        # Parse: package/source version [upgradable from: old_version]
                        parts = line.split('/')
                        if parts:
                            package_name = parts[0]
                            result["upgradable"].append({
                                "package": package_name,
                                "full_line": line.strip()
                            })
                
                result["total_updates"] = len(result["upgradable"])
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def get_critical_updates(server_ip: str, user: str) -> dict:
    """Filter for security-only updates."""
    result = {
        "server_ip": server_ip,
        "checked_at": datetime.utcnow().isoformat(),
        "critical_count": 0,
        "critical_updates": [],
        "error": None,
    }
    
    try:
        async with asyncssh.connect(
            server_ip,
            username=user,
            known_hosts=None,
            connect_timeout=15
        ) as conn:
            # Check for security updates using apt
            # Look for packages from *-security repositories
            sec_result = await conn.run(
                "apt list --upgradable 2>/dev/null | grep -i security",
                check=False
            )
            
            if sec_result.exit_status == 0 and sec_result.stdout.strip():
                lines = sec_result.stdout.strip().split('\n')
                for line in lines:
                    if '/' in line:
                        parts = line.split('/')
                        if parts:
                            result["critical_updates"].append({
                                "package": parts[0],
                                "full_line": line.strip()
                            })
                
                result["critical_count"] = len(result["critical_updates"])
            
            # Also check unattended-upgrades log for recent security patches
            log_result = await conn.run(
                "tail -20 /var/log/unattended-upgrades/unattended-upgrades.log 2>/dev/null | grep -i security | tail -5",
                check=False
            )
            if log_result.exit_status == 0:
                result["recent_security_log"] = log_result.stdout.strip()
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def check_service_status(server_ip: str, user: str, service_name: str) -> dict:
    """Check systemctl status for a service."""
    result = {
        "server_ip": server_ip,
        "service": service_name,
        "checked_at": datetime.utcnow().isoformat(),
        "active": False,
        "enabled": False,
        "status": "unknown",
        "uptime": None,
        "error": None,
    }
    
    try:
        async with asyncssh.connect(
            server_ip,
            username=user,
            known_hosts=None,
            connect_timeout=10
        ) as conn:
            # Check if service is active
            active_result = await conn.run(
                f"systemctl is-active {service_name} 2>/dev/null",
                check=False
            )
            result["status"] = active_result.stdout.strip()
            result["active"] = result["status"] == "active"
            
            # Check if service is enabled
            enabled_result = await conn.run(
                f"systemctl is-enabled {service_name} 2>/dev/null",
                check=False
            )
            result["enabled"] = enabled_result.stdout.strip() == "enabled"
            
            # Get service uptime if active
            if result["active"]:
                status_result = await conn.run(
                    f"systemctl show {service_name} --property=ActiveEnterTimestamp 2>/dev/null",
                    check=False
                )
                if status_result.exit_status == 0:
                    timestamp_line = status_result.stdout.strip()
                    if '=' in timestamp_line:
                        result["started_at"] = timestamp_line.split('=')[1]
                        
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def scan_auth_logs(server_ip: str, user: str, lines: int = 100) -> dict:
    """Look for failed SSH attempts in auth logs."""
    result = {
        "server_ip": server_ip,
        "checked_at": datetime.utcnow().isoformat(),
        "failed_attempts": [],
        "failed_count": 0,
        "unique_ips": [],
        "error": None,
    }
    
    try:
        async with asyncssh.connect(
            server_ip,
            username=user,
            known_hosts=None,
            connect_timeout=10
        ) as conn:
            # Check auth.log for failed attempts
            log_result = await conn.run(
                f"sudo tail -{lines} /var/log/auth.log 2>/dev/null | grep -i 'failed\\|invalid\\|authentication failure' | tail -50",
                check=False
            )
            
            if log_result.exit_status == 0 and log_result.stdout.strip():
                for line in log_result.stdout.strip().split('\n'):
                    result["failed_attempts"].append(line.strip())
                    
                    # Extract IP addresses
                    ip_matches = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line)
                    for ip in ip_matches:
                        if ip not in result["unique_ips"] and not ip.startswith('192.168.'):
                            result["unique_ips"].append(ip)
                
                result["failed_count"] = len(result["failed_attempts"])
            
            # Check fail2ban status if available
            f2b_result = await conn.run(
                "sudo fail2ban-client status sshd 2>/dev/null",
                check=False
            )
            if f2b_result.exit_status == 0:
                result["fail2ban_status"] = f2b_result.stdout.strip()
                # Extract banned IPs
                banned_match = re.search(r'Banned IP list:\s*(.*)', f2b_result.stdout)
                if banned_match:
                    banned_ips = banned_match.group(1).strip().split()
                    result["banned_ips"] = banned_ips
                    
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def get_server_security_summary(server_ip: str, user: str) -> dict:
    """Get a comprehensive security summary for a server."""
    updates = await check_os_updates(server_ip, user)
    critical = await get_critical_updates(server_ip, user)
    auth_logs = await scan_auth_logs(server_ip, user)
    
    # Determine overall security status
    status = "healthy"
    alerts = []
    
    if critical["critical_count"] > 0:
        status = "warning"
        alerts.append(f"{critical['critical_count']} security updates available")
    
    if auth_logs["failed_count"] > 10:
        status = "warning"
        alerts.append(f"{auth_logs['failed_count']} failed login attempts")
    
    if len(auth_logs.get("unique_ips", [])) > 5:
        status = "critical"
        alerts.append(f"{len(auth_logs['unique_ips'])} unique external IPs with failed attempts")
    
    return {
        "server_ip": server_ip,
        "checked_at": datetime.utcnow().isoformat(),
        "status": status,
        "alerts": alerts,
        "updates": {
            "total": updates["total_updates"],
            "critical": critical["critical_count"],
        },
        "auth": {
            "failed_count": auth_logs["failed_count"],
            "unique_ips": len(auth_logs.get("unique_ips", [])),
            "banned_ips": len(auth_logs.get("banned_ips", [])),
        }
    }


# Known servers list (same as discovery.py)
KNOWN_SERVERS = [
    {"name": "Relay", "ip": "192.168.65.248", "user": "relayadmin"},
    {"name": "Demos", "ip": "192.168.65.246", "user": "demos"},
    {"name": "Nexus", "ip": "192.168.65.247", "user": "contextadmin"},
    {"name": "Dockyard", "ip": "192.168.65.252", "user": "dockyardadmin"},
    {"name": "Vector", "ip": "192.168.65.249", "user": "betadmin"},
    {"name": "Claude Code", "ip": "192.168.65.245", "user": "claudedevadmin"},
]


async def scan_all_servers_security() -> list[dict]:
    """Run security scan on all known servers."""
    async def scan_server(server: dict) -> dict:
        try:
            summary = await get_server_security_summary(server["ip"], server["user"])
            return {
                "name": server["name"],
                **summary
            }
        except Exception as e:
            return {
                "name": server["name"],
                "server_ip": server["ip"],
                "status": "error",
                "error": str(e)
            }
    
    tasks = [scan_server(s) for s in KNOWN_SERVERS]
    results = await asyncio.gather(*tasks)
    return results
