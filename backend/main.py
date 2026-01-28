import asyncio
import asyncssh
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
import time
import os

app = FastAPI(title="Homebase API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVERS = [
    {"name": "Cobalt", "ip": "192.168.65.243", "user": "cobaltadmin", "web_url": "homebase.rize.bm", "ssh_url": "cobalt-ssh.rize.bm", "os": "linux"},
    {"name": "Relay", "ip": "192.168.65.248", "user": "relayadmin", "web_url": "relay.rize.bm", "ssh_url": "relay-ssh.rize.bm", "os": "linux"},
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
                # Windows-specific commands for Hyper-V

                # Get hostname to verify connection
                hostname_result = await conn.run("hostname", check=False)
                if hostname_result.exit_status != 0:
                    raise Exception("Could not get hostname")

                # Get uptime via PowerShell
                uptime_result = await conn.run('powershell -Command "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | ForEach-Object { \'{0}d {1}h {2}m\' -f $_.Days, $_.Hours, $_.Minutes }"', check=False)
                if uptime_result.exit_status == 0:
                    result["uptime"] = uptime_result.stdout.strip()

                # Get memory via PowerShell (in MB)
                mem_result = await conn.run('powershell -Command "$os = Get-CimInstance Win32_OperatingSystem; $total = [math]::Round($os.TotalVisibleMemorySize/1024); $free = [math]::Round($os.FreePhysicalMemory/1024); Write-Output (\'{0} {1}\' -f $total, ($total - $free))"', check=False)
                if mem_result.exit_status == 0:
                    parts = mem_result.stdout.strip().split()
                    if len(parts) == 2:
                        result["memory_total"] = int(parts[0])
                        result["memory_used"] = int(parts[1])

                # Get disk usage (C: drive) via PowerShell (in GB)
                disk_result = await conn.run('powershell -Command "$d = Get-PSDrive C; $total = [math]::Round(($d.Used + $d.Free)/1GB); $used = [math]::Round($d.Used/1GB); Write-Output (\'{0} {1}\' -f $total, $used)"', check=False)
                if disk_result.exit_status == 0:
                    parts = disk_result.stdout.strip().split()
                    if len(parts) == 2:
                        result["disk_total"] = int(parts[0])
                        result["disk_used"] = int(parts[1])

                # Get CPU via PowerShell
                cpu_result = await conn.run('powershell -Command "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"', check=False)
                if cpu_result.exit_status == 0:
                    try:
                        result["cpu_percent"] = float(cpu_result.stdout.strip())
                    except:
                        pass

                # Get VM status for Hyper-V
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
                # Linux commands (existing logic)
                # Get uptime
                uptime_result = await conn.run("uptime -p", check=False)
                if uptime_result.exit_status == 0:
                    result["uptime"] = uptime_result.stdout.strip().replace("up ", "")

                # Get memory
                mem_result = await conn.run("free -m | awk 'NR==2{print $2,$3}'", check=False)
                if mem_result.exit_status == 0:
                    parts = mem_result.stdout.strip().split()
                    if len(parts) == 2:
                        result["memory_total"] = int(parts[0])
                        result["memory_used"] = int(parts[1])

                # Get disk
                disk_result = await conn.run("df -BG / | awk 'NR==2{gsub(/G/,\"\"); print $2,$3}'", check=False)
                if disk_result.exit_status == 0:
                    parts = disk_result.stdout.strip().split()
                    if len(parts) == 2:
                        result["disk_total"] = int(parts[0])
                        result["disk_used"] = int(parts[1])

                # Get CPU
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

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/api/servers")
async def get_servers():
    tasks = [get_server_stats(s) for s in SERVERS]
    results = await asyncio.gather(*tasks)
    return {"servers": results, "timestamp": time.time()}

# Serve static files from frontend/dist
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
