"""
Red Team Security Service
Monitors security scans, vulnerabilities, and provides 7-day trend data for agent security.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

DATA_DIR = Path("/home/rizeadmin/homebase/data")
REDTEAM_FILE = DATA_DIR / "redteam_history.json"

def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not REDTEAM_FILE.exists():
        REDTEAM_FILE.write_text(json.dumps({"reports": [], "gateway_status": {}}, indent=2))

def load_data() -> dict:
    """Load redteam data from file."""
    ensure_data_dir()
    try:
        return json.loads(REDTEAM_FILE.read_text())
    except:
        return {"reports": [], "gateway_status": {}}

def save_data(data: dict):
    """Save redteam data to file."""
    ensure_data_dir()
    REDTEAM_FILE.write_text(json.dumps(data, indent=2))

def add_scan_report(report: dict) -> dict:
    """Add a new scan report to history."""
    data = load_data()
    
    # Add timestamp if not provided
    if "date" not in report:
        report["date"] = datetime.now().strftime("%Y-%m-%d")
    if "timestamp" not in report:
        report["timestamp"] = datetime.now().isoformat()
    
    # Determine severity based on vulnerabilities
    vulns = report.get("vulnerabilities", [])
    if any(v.get("severity") == "critical" for v in vulns):
        report["severity"] = "critical"
    elif any(v.get("severity") == "high" for v in vulns):
        report["severity"] = "high"
    elif any(v.get("severity") == "medium" for v in vulns):
        report["severity"] = "medium"
    elif len(vulns) > 0:
        report["severity"] = "low"
    else:
        report["severity"] = "clear"
    
    data["reports"].append(report)
    
    # Keep only last 100 reports
    data["reports"] = data["reports"][-100:]
    
    save_data(data)
    return report

def get_reports(limit: int = 30) -> List[dict]:
    """Get recent scan reports."""
    data = load_data()
    reports = data.get("reports", [])
    return reports[-limit:] if limit else reports

def get_summary() -> dict:
    """Get summary of all scan data."""
    data = load_data()
    reports = data.get("reports", [])
    
    if not reports:
        return {
            "total_scans": 0,
            "last_scan": None,
            "last_severity": None,
            "last_vuln_count": 0,
            "last_update_count": 0
        }
    
    latest = reports[-1]
    return {
        "total_scans": len(reports),
        "last_scan": latest.get("timestamp") or latest.get("date"),
        "last_severity": latest.get("severity", "unknown"),
        "last_vuln_count": len(latest.get("vulnerabilities", [])),
        "last_update_count": len(latest.get("updates_available", []))
    }

def get_7day_trend() -> List[dict]:
    """Get 7-day trend data for charting."""
    data = load_data()
    reports = data.get("reports", [])
    
    # Get the last 7 days
    today = datetime.now().date()
    trend = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        # Find report for this day
        day_report = None
        for r in reports:
            if r.get("date") == day_str:
                day_report = r
                break
        
        if day_report:
            severity_score = {"clear": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
            trend.append({
                "date": day_str,
                "day": day.strftime("%a"),
                "severity": day_report.get("severity", "unknown"),
                "severity_score": severity_score.get(day_report.get("severity"), 0),
                "vuln_count": len(day_report.get("vulnerabilities", [])),
                "update_count": len(day_report.get("updates_available", [])),
                "passed": day_report.get("passed", 0),
                "failed": day_report.get("failed", 0)
            })
        else:
            trend.append({
                "date": day_str,
                "day": day.strftime("%a"),
                "severity": None,
                "severity_score": None,
                "vuln_count": None,
                "update_count": None,
                "passed": None,
                "failed": None
            })
    
    return trend

def update_gateway_status(agent: str, status: dict) -> dict:
    """Update gateway uptime status for an agent."""
    data = load_data()
    if "gateway_status" not in data:
        data["gateway_status"] = {}
    
    status["last_check"] = datetime.now().isoformat()
    data["gateway_status"][agent] = status
    save_data(data)
    return status

def get_gateway_status(agent: str = None) -> dict:
    """Get gateway status for agent(s)."""
    data = load_data()
    gateway = data.get("gateway_status", {})
    
    if agent:
        return gateway.get(agent, {"status": "unknown", "uptime_percent": None})
    return gateway

async def check_david_gateway() -> dict:
    """Check David Bishop gateway status via SSH."""
    import asyncssh
    
    result = {
        "agent": "david",
        "status": "unknown",
        "uptime_percent": None,
        "gateway_url": "http://192.168.65.241:3000",
        "last_check": datetime.now().isoformat(),
        "services": {}
    }
    
    try:
        async with asyncssh.connect(
            "192.168.65.241",
            username="david",
            known_hosts=None,
            connect_timeout=10
        ) as conn:
            # Check if PM2 processes are running
            pm2_result = await conn.run("pm2 jlist 2>/dev/null || echo '[]'", check=False)
            if pm2_result.exit_status == 0:
                try:
                    processes = json.loads(pm2_result.stdout.strip())
                    result["services"]["pm2_processes"] = len(processes)
                    online_count = len([p for p in processes if p.get("pm2_env", {}).get("status") == "online"])
                    result["services"]["online"] = online_count
                    result["status"] = "online" if online_count > 0 else "degraded"
                except:
                    result["services"]["pm2_processes"] = 0
            
            # Check uptime
            uptime_result = await conn.run("uptime -p", check=False)
            if uptime_result.exit_status == 0:
                result["uptime"] = uptime_result.stdout.strip()
            
            # Check port 3000 (common for Node.js apps)
            port_check = await conn.run("netstat -tlnp 2>/dev/null | grep ':3000' || ss -tlnp | grep ':3000' || echo 'port not listening'", check=False)
            result["services"]["port_3000"] = "listening" if "3000" in port_check.stdout else "not listening"
            
            if result["services"].get("port_3000") == "listening":
                result["status"] = "online"
            elif result["status"] != "online":
                result["status"] = "degraded"
                
    except asyncssh.Error as e:
        result["status"] = "offline"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    # Update stored status
    update_gateway_status("david", result)
    
    return result

# Initialize with sample data if empty
def init_sample_data():
    """Initialize with sample 7-day data for demonstration."""
    data = load_data()
    if data.get("reports"):
        return  # Already has data
    
    today = datetime.now().date()
    sample_reports = []
    
    severities = ["clear", "clear", "low", "clear", "medium", "clear", "clear"]
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        severity = severities[6-i]
        
        vulns = []
        if severity == "low":
            vulns = [{"severity": "low", "description": "Minor configuration drift detected"}]
        elif severity == "medium":
            vulns = [{"severity": "medium", "description": "Outdated dependency detected"}]
        
        report = {
            "date": day.strftime("%Y-%m-%d"),
            "timestamp": datetime.combine(day, datetime.min.time()).isoformat(),
            "severity": severity,
            "passed": 12 if severity == "clear" else 10,
            "failed": 0 if severity == "clear" else (1 if severity == "low" else 2),
            "vulnerabilities": vulns,
            "updates_available": [] if i % 3 != 0 else ["package-update-1"],
            "full_report": f"Daily red team scan for {day.strftime('%Y-%m-%d')}\nStatus: {severity}"
        }
        sample_reports.append(report)
    
    data["reports"] = sample_reports
    save_data(data)

# Initialize sample data on import
init_sample_data()
