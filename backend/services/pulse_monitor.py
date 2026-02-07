"""
Homebase Pulse Monitor - Server and Project Health Monitoring
Ported from Relay Pulse with email alert system
"""
import asyncio
import asyncssh
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Configuration
EMAIL_TO = "artiedarrell@gmail.com"
EMAIL_FROM = "homebase@rize.bm"
SMTP_HOST = "localhost"
SMTP_PORT = 25

# Alert thresholds
CPU_WARNING = 80
CPU_CRITICAL = 95
MEMORY_WARNING = 80
MEMORY_CRITICAL = 95
DISK_WARNING = 85
DISK_CRITICAL = 95

DATA_DIR = Path.home() / "homebase" / "pulse_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Alert:
    """Represents a monitoring alert"""
    def __init__(self, server_name: str, alert_type: str, message: str, severity: str = "warning"):
        self.id = f"alert_{datetime.now().timestamp()}"
        self.server_name = server_name
        self.alert_type = alert_type
        self.message = message
        self.severity = severity  # info, warning, critical
        self.timestamp = datetime.now()
        self.acknowledged = False
        self.notified = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "server_name": self.server_name,
            "alert_type": self.alert_type,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "notified": self.notified
        }


class PulseMonitor:
    """Main monitoring class"""
    
    def __init__(self, servers: List[dict]):
        self.servers = servers
        self.alerts: List[Alert] = []
        self.last_check: Optional[datetime] = None
        self.last_health: Dict = {}
        self._load_alerts()
    
    def _load_alerts(self):
        """Load alerts from file"""
        alerts_file = DATA_DIR / "alerts.json"
        if alerts_file.exists():
            with open(alerts_file) as f:
                data = json.load(f)
                # Only load recent alerts (last 24h)
                cutoff = datetime.now() - timedelta(hours=24)
                for a in data:
                    ts = datetime.fromisoformat(a["timestamp"])
                    if ts > cutoff:
                        alert = Alert(a["server_name"], a["alert_type"], a["message"], a["severity"])
                        alert.id = a["id"]
                        alert.timestamp = ts
                        alert.acknowledged = a.get("acknowledged", False)
                        alert.notified = a.get("notified", False)
                        self.alerts.append(alert)
    
    def _save_alerts(self):
        """Save alerts to file"""
        alerts_file = DATA_DIR / "alerts.json"
        with open(alerts_file, 'w') as f:
            json.dump([a.to_dict() for a in self.alerts], f, indent=2)
    
    def add_alert(self, server_name: str, alert_type: str, message: str, severity: str = "warning"):
        """Add a new alert if not duplicate"""
        # Check for duplicate (same server + type within last hour)
        cutoff = datetime.now() - timedelta(hours=1)
        for existing in self.alerts:
            if (existing.server_name == server_name and 
                existing.alert_type == alert_type and 
                existing.timestamp > cutoff):
                return  # Duplicate, skip
        
        alert = Alert(server_name, alert_type, message, severity)
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        self.alerts = self.alerts[-100:]
        self._save_alerts()
        
        logger.warning(f"[{severity.upper()}] {server_name}: {message}")
        return alert
    
    async def check_server(self, server: dict) -> dict:
        """Check a single server's health"""
        result = {
            "name": server["name"],
            "ip": server["ip"],
            "status": "offline",
            "cpu_percent": None,
            "memory_percent": None,
            "disk_percent": None,
            "uptime": None,
            "alerts": []
        }
        
        server_os = server.get("os", "linux")
        
        try:
            async with asyncssh.connect(
                server["ip"],
                username=server["user"],
                known_hosts=None,
                connect_timeout=10
            ) as conn:
                result["status"] = "online"
                
                if server_os == "windows":
                    # Windows commands
                    cpu_result = await conn.run('powershell -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"', check=False)
                    if cpu_result.exit_status == 0:
                        try:
                            result["cpu_percent"] = float(cpu_result.stdout.strip())
                        except:
                            pass
                    
                    mem_result = await conn.run('powershell -Command "$os = Get-CimInstance Win32_OperatingSystem; [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100, 1)"', check=False)
                    if mem_result.exit_status == 0:
                        try:
                            result["memory_percent"] = float(mem_result.stdout.strip())
                        except:
                            pass
                    
                    disk_result = await conn.run('powershell -Command "$d = Get-PSDrive C; [math]::Round($d.Used / ($d.Used + $d.Free) * 100, 1)"', check=False)
                    if disk_result.exit_status == 0:
                        try:
                            result["disk_percent"] = float(disk_result.stdout.strip())
                        except:
                            pass
                else:
                    # Linux commands
                    cpu_result = await conn.run("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1", check=False)
                    if cpu_result.exit_status == 0:
                        try:
                            result["cpu_percent"] = float(cpu_result.stdout.strip())
                        except:
                            pass
                    
                    mem_result = await conn.run("free -m | awk 'NR==2{printf \"%.1f\", $3*100/$2}'", check=False)
                    if mem_result.exit_status == 0:
                        try:
                            result["memory_percent"] = float(mem_result.stdout.strip())
                        except:
                            pass
                    
                    disk_result = await conn.run("df -h / | awk 'NR==2{print $5}' | tr -d '%'", check=False)
                    if disk_result.exit_status == 0:
                        try:
                            result["disk_percent"] = float(disk_result.stdout.strip())
                        except:
                            pass
                    
                    uptime_result = await conn.run("uptime -p", check=False)
                    if uptime_result.exit_status == 0:
                        result["uptime"] = uptime_result.stdout.strip()
                
                # Check thresholds and create alerts
                cpu = result.get("cpu_percent", 0) or 0
                memory = result.get("memory_percent", 0) or 0
                disk = result.get("disk_percent", 0) or 0
                
                if cpu >= CPU_CRITICAL:
                    self.add_alert(server["name"], "cpu_critical", f"CPU at {cpu}% (critical)", "critical")
                elif cpu >= CPU_WARNING:
                    self.add_alert(server["name"], "cpu_warning", f"CPU at {cpu}% (warning)", "warning")
                
                if memory >= MEMORY_CRITICAL:
                    self.add_alert(server["name"], "memory_critical", f"Memory at {memory}% (critical)", "critical")
                elif memory >= MEMORY_WARNING:
                    self.add_alert(server["name"], "memory_warning", f"Memory at {memory}% (warning)", "warning")
                
                if disk >= DISK_CRITICAL:
                    self.add_alert(server["name"], "disk_critical", f"Disk at {disk}% (critical)", "critical")
                elif disk >= DISK_WARNING:
                    self.add_alert(server["name"], "disk_warning", f"Disk at {disk}% (warning)", "warning")
                
        except asyncio.TimeoutError:
            result["status"] = "timeout"
            self.add_alert(server["name"], "connection_timeout", f"Connection timed out", "critical")
        except Exception as e:
            result["status"] = "error"
            self.add_alert(server["name"], "connection_error", f"Connection failed: {str(e)}", "critical")
        
        return result
    
    async def run_health_check(self) -> dict:
        """Run health check on all servers"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "servers": [],
            "summary": {
                "total": len(self.servers),
                "online": 0,
                "offline": 0,
                "warning": 0,
                "critical": 0
            }
        }
        
        tasks = [self.check_server(server) for server in self.servers]
        server_results = await asyncio.gather(*tasks)
        
        for result in server_results:
            results["servers"].append(result)
            
            if result["status"] == "online":
                results["summary"]["online"] += 1
            else:
                results["summary"]["offline"] += 1
        
        # Count alerts by severity
        for alert in self.alerts:
            if not alert.acknowledged:
                if alert.severity == "critical":
                    results["summary"]["critical"] += 1
                elif alert.severity == "warning":
                    results["summary"]["warning"] += 1
        
        self.last_check = datetime.now()
        self.last_health = results
        
        # Save health data
        health_file = DATA_DIR / "latest_health.json"
        with open(health_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Send email alerts for critical issues
        await self.send_alert_emails()
        
        return results
    
    async def send_alert_emails(self):
        """Send email for unnotified critical alerts"""
        unnotified = [a for a in self.alerts if not a.notified and a.severity == "critical"]
        
        if not unnotified:
            return
        
        subject = f"[Homebase ALERT] {len(unnotified)} critical alert(s)"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h1 style="color: #dc3545;">Critical Server Alerts</h1>
            <p>The following critical alerts were detected at {datetime.now().strftime('%Y-%m-%d %H:%M')}:</p>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background: #f8d7da;">
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Server</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Alert</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Time</th>
                </tr>
        """
        
        for alert in unnotified:
            html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>{alert.server_name}</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{alert.message}</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{alert.timestamp.strftime('%H:%M:%S')}</td>
                </tr>
            """
        
        html += """
            </table>
            <p style="margin-top: 20px;">
                <a href="http://homebase.rize.bm" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Homebase Dashboard</a>
            </p>
            <hr>
            <p style="color: #666; font-size: 12px;">This is an automated alert from Homebase Infrastructure Monitor.</p>
        </body>
        </html>
        """
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO
            msg.attach(MIMEText(html, "html"))
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.send_message(msg)
            
            logger.info(f"Sent alert email for {len(unnotified)} critical alerts")
            
            # Mark as notified
            for alert in unnotified:
                alert.notified = True
            self._save_alerts()
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
    
    def get_alerts(self, acknowledged: bool = None) -> List[dict]:
        """Get alerts, optionally filtered"""
        alerts = self.alerts
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        return [a.to_dict() for a in alerts]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                self._save_alerts()
                return True
        return False
    
    def get_status(self) -> dict:
        """Get current monitoring status"""
        return {
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "servers_monitored": len(self.servers),
            "total_alerts": len(self.alerts),
            "unacknowledged_alerts": len([a for a in self.alerts if not a.acknowledged]),
            "critical_alerts": len([a for a in self.alerts if a.severity == "critical" and not a.acknowledged]),
            "last_health": self.last_health
        }


# Global instance will be initialized from main.py
pulse_monitor: Optional[PulseMonitor] = None

def init_pulse_monitor(servers: List[dict]):
    """Initialize the pulse monitor with servers"""
    global pulse_monitor
    pulse_monitor = PulseMonitor(servers)
    return pulse_monitor
