import asyncio
import asyncssh
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import time
import os

# Import services
from services.database import init_database, seed_servers, get_all_servers, get_server_by_ip
from services import discovery, security, logCollector
from services import keyManager

app = FastAPI(title="Homebase API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_database()
    seed_servers()

SERVERS = [
    {"name": "Cobalt", "ip": "192.168.65.243", "user": "cobaltadmin", "web_url": "homebase.rize.bm", "ssh_url": "cobalt-ssh.rize.bm", "os": "linux"},
    {"name": "Relay", "ip": "192.168.65.248", "user": "relayadmin", "web_url": "relay.rize.bm", "ssh_url": "relay-ssh.rize.bm", "os": "linux"},
    {"name": "Relay-v2", "ip": "192.168.65.248", "port": 8001, "user": "relayadmin", "web_url": "relay.rize.bm/v2", "ssh_url": "relay-ssh.rize.bm", "os": "linux", "health_endpoint": "/api/v2/health"},
    {"name": "BPS AI", "ip": "192.168.65.246", "user": "bpsaiadmin", "web_url": "bpsai.rize.bm", "ssh_url": "bpsai-ssh.rize.bm", "os": "linux"},
    {"name": "Context Hub", "ip": "192.168.65.247", "user": "contextadmin", "web_url": "context.rize.bm", "ssh_url": "context-ssh.rize.bm", "os": "linux"},
    {"name": "Dockyard", "ip": "192.168.65.252", "user": "dockyardadmin", "web_url": "dockyard-admin.rize.bm", "ssh_url": "dockyard-ssh.rize.bm", "os": "linux"},
    {"name": "Vector", "ip": "192.168.65.249", "user": "betadmin", "web_url": "app.bet.bm", "ssh_url": "vector-ssh.bet.bm", "os": "linux"},
    {"name": "Claude Code", "ip": "192.168.65.245", "user": "claudedevadmin", "web_url": None, "ssh_url": "claude-dev-ssh.rize.bm", "os": "linux"},
    {"name": "Hyper-V", "ip": "192.168.65.253", "user": "Administrator", "web_url": None, "ssh_url": "hyperv-ssh.rize.bm", "os": "windows"},
]

async def get_server_stats(server: dict) -> dict:
    """SSH to server and get stats."""
    result = {
        "name": server["name"],
        "ip": server["ip"],
        "web_url": server["web_url"],
        "ssh_url": server["ssh_url"],
        "status": "offline",
        "uptime": None,
        "memory_used": None,
        "memory_total": None,
        "disk_used": None,
        "disk_total": None,
        "cpu_percent": None,
        "vms": None,
    }

    server_os = server.get("os", "linux")

    try:
        async with asyncssh.connect(
            server["ip"],
            username=server["user"],
            known_hosts=None,
            connect_timeout=10
        ) as conn:
            if server_os == "windows":
                hostname_result = await conn.run("hostname", check=False)
                if hostname_result.exit_status != 0:
                    raise Exception("Could not get hostname")

                uptime_result = await conn.run('powershell -Command "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | ForEach-Object { \'{0}d {1}h {2}m\' -f $_.Days, $_.Hours, $_.Minutes }"', check=False)
                if uptime_result.exit_status == 0:
                    result["uptime"] = uptime_result.stdout.strip()

                mem_result = await conn.run('powershell -Command "$os = Get-CimInstance Win32_OperatingSystem; $total = [math]::Round($os.TotalVisibleMemorySize/1024); $free = [math]::Round($os.FreePhysicalMemory/1024); Write-Output (\'{0} {1}\' -f $total, ($total - $free))"', check=False)
                if mem_result.exit_status == 0:
                    parts = mem_result.stdout.strip().split()
                    if len(parts) == 2:
                        result["memory_total"] = int(parts[0])
                        result["memory_used"] = int(parts[1])

                disk_result = await conn.run('powershell -Command "$d = Get-PSDrive C; $total = [math]::Round(($d.Used + $d.Free)/1GB); $used = [math]::Round($d.Used/1GB); Write-Output (\'{0} {1}\' -f $total, $used)"', check=False)
                if disk_result.exit_status == 0:
                    parts = disk_result.stdout.strip().split()
                    if len(parts) == 2:
                        result["disk_total"] = int(parts[0])
                        result["disk_used"] = int(parts[1])

                cpu_result = await conn.run('powershell -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"', check=False)
                if cpu_result.exit_status == 0:
                    try:
                        result["cpu_percent"] = float(cpu_result.stdout.strip())
                    except:
                        pass

                vm_result = await conn.run('powershell -Command "Get-VM | Select-Object Name, State | ForEach-Object { \'{0}:{1}\' -f $_.Name, $_.State }"', check=False)
                if vm_result.exit_status == 0 and vm_result.stdout.strip():
                    vms = []
                    for line in vm_result.stdout.strip().split('\n'):
                        line = line.strip()
                        if ':' in line:
                            name, state = line.rsplit(':', 1)
                            vms.append({"name": name.strip(), "state": state.strip()})
                    result["vms"] = vms

            else:
                uptime_result = await conn.run("uptime -p", check=False)
                if uptime_result.exit_status == 0:
                    result["uptime"] = uptime_result.stdout.strip().replace("up ", "")

                mem_result = await conn.run("free -m | awk 'NR==2{print $2,$3}'", check=False)
                if mem_result.exit_status == 0:
                    parts = mem_result.stdout.strip().split()
                    if len(parts) == 2:
                        result["memory_total"] = int(parts[0])
                        result["memory_used"] = int(parts[1])

                disk_result = await conn.run("df -BG / | awk 'NR==2{gsub(/G/,\"\"); print $2,$3}'", check=False)
                if disk_result.exit_status == 0:
                    parts = disk_result.stdout.strip().split()
                    if len(parts) == 2:
                        result["disk_total"] = int(parts[0])
                        result["disk_used"] = int(parts[1])

                cpu_result = await conn.run("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1", check=False)
                if cpu_result.exit_status == 0:
                    try:
                        result["cpu_percent"] = float(cpu_result.stdout.strip())
                    except:
                        pass

            result["status"] = "online"
    except Exception as e:
        result["status"] = "offline"
        result["error"] = str(e)

    return result


# ============== HEALTH & SERVERS ==============

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.2.0", "timestamp": time.time()}

@app.get("/api/servers")
async def get_servers():
    tasks = [get_server_stats(s) for s in SERVERS]
    results = await asyncio.gather(*tasks)
    return {"servers": results, "timestamp": time.time()}


# ============== DISCOVERY ==============

@app.get("/api/discovery/scan")
async def scan_servers():
    """Check which servers are reachable."""
    results = await discovery.scan_servers()
    return {"servers": results, "timestamp": time.time()}

@app.get("/api/discovery/projects")
async def discover_projects():
    """Discover all projects across all servers."""
    projects = await discovery.discover_all_projects()
    return {"projects": projects, "count": len(projects), "timestamp": time.time()}

@app.get("/api/discovery/projects/{server_ip}")
async def discover_server_projects(server_ip: str):
    """Discover projects on a specific server."""
    server = get_server_by_ip(server_ip)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    projects = await discovery.detect_projects(server_ip, server["username"])
    return {"server": server_ip, "projects": projects, "count": len(projects)}

@app.get("/api/discovery/registered")
async def get_registered_projects():
    """Get all registered projects."""
    projects = discovery.get_registered_projects()
    return {"projects": projects, "count": len(projects)}


# ============== SECURITY ==============

@app.get("/api/security/scan")
async def scan_all_security():
    """Run security scan on all servers."""
    results = await security.scan_all_servers_security()
    return {"servers": results, "timestamp": time.time()}

@app.get("/api/security/updates/{server_ip}")
async def check_server_updates(server_ip: str):
    """Check for OS updates on a specific server."""
    server = get_server_by_ip(server_ip)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    updates = await security.check_os_updates(server_ip, server["username"])
    critical = await security.get_critical_updates(server_ip, server["username"])
    return {
        "server": server_ip,
        "updates": updates,
        "critical": critical
    }

@app.get("/api/security/auth-logs/{server_ip}")
async def get_auth_logs(server_ip: str):
    """Get authentication logs for a server."""
    server = get_server_by_ip(server_ip)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    logs = await security.scan_auth_logs(server_ip, server["username"])
    return {"server": server_ip, "auth_logs": logs}

@app.get("/api/security/service/{server_ip}/{service_name}")
async def check_service(server_ip: str, service_name: str):
    """Check status of a service on a server."""
    server = get_server_by_ip(server_ip)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    status = await security.check_service_status(server_ip, server["username"], service_name)
    return status


# ============== CREDENTIALS ==============

class CredentialCreate(BaseModel):
    name: str
    type: str  # ssh_key, api_key, password, token
    value: str
    server_id: Optional[int] = None
    description: Optional[str] = None

class CredentialRotate(BaseModel):
    new_value: str

@app.get("/api/credentials")
async def list_credentials():
    """List all credentials (without values)."""
    credentials = keyManager.list_credentials()
    return {"credentials": credentials, "count": len(credentials)}

@app.post("/api/credentials")
async def store_credential(cred: CredentialCreate):
    """Store a new credential."""
    if cred.type not in ['ssh_key', 'api_key', 'password', 'token']:
        raise HTTPException(status_code=400, detail="Invalid credential type")
    
    result = keyManager.store_credential(
        cred.name, cred.type, cred.value, cred.server_id, cred.description
    )
    return result

@app.get("/api/credentials/{name}")
async def get_credential(name: str):
    """Retrieve a credential value (authorized access only)."""
    value = keyManager.get_credential(name)
    if value is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"name": name, "value": value}

@app.put("/api/credentials/{cred_id}/rotate")
async def rotate_credential(cred_id: int, rotation: CredentialRotate):
    """Rotate a credential with a new value."""
    result = keyManager.rotate_credential(cred_id, rotation.new_value)
    return result

@app.delete("/api/credentials/{name}")
async def delete_credential(name: str):
    """Delete a credential."""
    success = keyManager.delete_credential(name)
    if not success:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"deleted": name}

@app.get("/api/credentials/logs")
async def get_credential_logs(credential_id: Optional[int] = None, limit: int = 100):
    """Get credential access logs."""
    logs = keyManager.get_credential_access_logs(credential_id, limit)
    return {"logs": logs, "count": len(logs)}


# ============== LOGS ==============

@app.get("/api/logs/{server_ip}/{service}")
async def fetch_service_logs(server_ip: str, service: str, lines: int = 100):
    """Fetch logs from a service."""
    server = get_server_by_ip(server_ip)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    logs = await logCollector.fetch_logs(server_ip, server["username"], service, lines)
    return logs

@app.get("/api/logs/{server_ip}/{service}/analyze")
async def analyze_service_logs(server_ip: str, service: str, lines: int = 200):
    """Fetch and analyze logs for errors."""
    server = get_server_by_ip(server_ip)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    analysis = await logCollector.analyze_logs(server_ip, server["username"], service, lines)
    return analysis

@app.get("/api/logs/errors/recent")
async def get_recent_errors(hours: int = 24):
    """Get recent errors from stored logs."""
    errors = logCollector.get_recent_errors(hours)
    return {"errors": errors, "count": len(errors)}




# ============== PULSE MONITORING ==============

from services.pulse_monitor import init_pulse_monitor, pulse_monitor

# Initialize pulse monitor when startup runs
_pulse_init_done = False

@app.on_event("startup")
async def init_pulse():
    global _pulse_init_done
    if not _pulse_init_done:
        init_pulse_monitor(SERVERS)
        _pulse_init_done = True

@app.get("/api/pulse/status")
async def get_pulse_status():
    """Get current pulse monitoring status."""
    from services.pulse_monitor import pulse_monitor
    if not pulse_monitor:
        raise HTTPException(status_code=503, detail="Pulse monitor not initialized")
    return pulse_monitor.get_status()

@app.post("/api/pulse/check")
async def run_pulse_check():
    """Trigger a health check on all servers."""
    from services.pulse_monitor import pulse_monitor
    if not pulse_monitor:
        raise HTTPException(status_code=503, detail="Pulse monitor not initialized")
    results = await pulse_monitor.run_health_check()
    return {"success": True, "results": results}

@app.get("/api/pulse/alerts")
async def get_pulse_alerts(acknowledged: Optional[bool] = None):
    """Get monitoring alerts."""
    from services.pulse_monitor import pulse_monitor
    if not pulse_monitor:
        raise HTTPException(status_code=503, detail="Pulse monitor not initialized")
    alerts = pulse_monitor.get_alerts(acknowledged)
    return {"alerts": alerts, "count": len(alerts)}

@app.post("/api/pulse/alerts/{alert_id}/acknowledge")
async def acknowledge_pulse_alert(alert_id: str):
    """Acknowledge an alert."""
    from services.pulse_monitor import pulse_monitor
    if not pulse_monitor:
        raise HTTPException(status_code=503, detail="Pulse monitor not initialized")
    success = pulse_monitor.acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True}

@app.get("/api/pulse/dashboard")
async def get_pulse_dashboard():
    """Get dashboard summary for pulse monitoring."""
    from services.pulse_monitor import pulse_monitor
    if not pulse_monitor:
        raise HTTPException(status_code=503, detail="Pulse monitor not initialized")
    
    status = pulse_monitor.get_status()
    alerts = pulse_monitor.get_alerts(acknowledged=False)
    
    return {
        "last_check": status["last_check"],
        "servers": {
            "monitored": status["servers_monitored"],
            "online": status["last_health"].get("summary", {}).get("online", 0),
            "offline": status["last_health"].get("summary", {}).get("offline", 0)
        },
        "alerts": {
            "total": status["total_alerts"],
            "unacknowledged": status["unacknowledged_alerts"],
            "critical": status["critical_alerts"]
        },
        "recent_alerts": alerts[:5]
    }




# ============== METRICS HISTORY ==============

from services import metrics_history

@app.get("/api/metrics/history/{server_name}")
async def get_server_history(server_name: str, hours: int = 24, interval: int = 30):
    """Get historical metrics for a specific server."""
    metrics = metrics_history.get_server_metrics(server_name, hours, interval)
    return {"server": server_name, "hours": hours, "metrics": metrics, "count": len(metrics)}

@app.get("/api/metrics/history")
async def get_all_history(hours: int = 24, interval: int = 30):
    """Get historical metrics for all servers."""
    all_metrics = metrics_history.get_all_servers_metrics(hours, interval)
    return {"hours": hours, "servers": all_metrics, "timestamp": time.time()}

@app.get("/api/metrics/summary")
async def get_metrics_summary(hours: int = 24):
    """Get metrics summary (avg, max) for all servers."""
    summary = metrics_history.get_metrics_summary(hours)
    return {"hours": hours, "summary": summary, "timestamp": time.time()}

@app.post("/api/metrics/record")
async def record_current_metrics():
    """Record current metrics (typically called by scheduler)."""
    tasks = [get_server_stats(s) for s in SERVERS]
    results = await asyncio.gather(*tasks)
    count = metrics_history.record_metrics(results)
    return {"recorded": count, "timestamp": time.time()}

@app.delete("/api/metrics/cleanup")
async def cleanup_metrics(days: int = 7):
    """Remove old metrics data."""
    deleted = metrics_history.cleanup_old_metrics(days)
    return {"deleted": deleted, "older_than_days": days}

# ============== STATIC FILES ==============

FRONTEND_DIR = "/home/cobaltadmin/homebase/frontend/dist"

if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_DIR}/assets"), name="assets")

    @app.get("/vite.svg")
    async def vite_svg():
        return FileResponse(f"{FRONTEND_DIR}/vite.svg")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(f"{FRONTEND_DIR}/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ============== METRICS HISTORY ==============

from services import metrics_history
