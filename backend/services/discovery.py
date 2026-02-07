"""
Project Auto-Discovery Service
Scans known servers to find and register projects automatically.
"""

import asyncio
import asyncssh
from typing import Optional
from datetime import datetime


# Known servers in the Rize infrastructure
KNOWN_SERVERS = [
    {"name": "Relay", "ip": "192.168.65.248", "user": "relayadmin"},
    {"name": "Demos", "ip": "192.168.65.246", "user": "demos"},
    {"name": "Nexus", "ip": "192.168.65.247", "user": "contextadmin"},
    {"name": "Dockyard", "ip": "192.168.65.252", "user": "dockyardadmin"},
    {"name": "Vector", "ip": "192.168.65.249", "user": "betadmin"},
    {"name": "Claude Code", "ip": "192.168.65.245", "user": "claudedevadmin"},
]

# Common project directories to search
PROJECT_SEARCH_PATHS = [
    "~",  # Home directory
    "~/projects",
    "/opt",
]

# Files that indicate a project
PROJECT_INDICATORS = [
    "package.json",
    "requirements.txt", 
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".git",
]


async def scan_servers() -> list[dict]:
    """Check which servers are reachable via SSH."""
    results = []
    
    async def check_server(server: dict) -> dict:
        result = {
            "name": server["name"],
            "ip": server["ip"],
            "user": server["user"],
            "reachable": False,
            "checked_at": datetime.utcnow().isoformat(),
        }
        try:
            async with asyncssh.connect(
                server["ip"],
                username=server["user"],
                known_hosts=None,
                connect_timeout=10
            ) as conn:
                # Simple test command
                test_result = await conn.run("echo ok", check=False)
                result["reachable"] = test_result.exit_status == 0
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    tasks = [check_server(s) for s in KNOWN_SERVERS]
    results = await asyncio.gather(*tasks)
    return results


async def detect_projects(server_ip: str, user: str) -> list[dict]:
    """SSH to a server and find project directories."""
    projects = []
    
    try:
        async with asyncssh.connect(
            server_ip,
            username=user,
            known_hosts=None,
            connect_timeout=15
        ) as conn:
            # Build find command for project indicators
            indicators_pattern = " -o ".join([f'-name "{ind}"' for ind in PROJECT_INDICATORS])
            
            for search_path in PROJECT_SEARCH_PATHS:
                # Expand ~ to actual home directory
                expanded_path = search_path.replace("~", f"/home/{user}")
                
                # Find directories containing project indicators (max depth 3)
                find_cmd = f'find {expanded_path} -maxdepth 3 \\( {indicators_pattern} \\) 2>/dev/null | head -50'
                result = await conn.run(find_cmd, check=False)
                
                if result.exit_status == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        # Get the parent directory (the project root)
                        project_path = '/'.join(line.split('/')[:-1])
                        if project_path and project_path not in [p["path"] for p in projects]:
                            # Get project metadata
                            metadata = await read_project_metadata(conn, project_path)
                            projects.append({
                                "path": project_path,
                                "server_ip": server_ip,
                                "detected_via": line.split('/')[-1],
                                **metadata
                            })
    except Exception as e:
        pass
    
    return projects


async def read_project_metadata(conn, path: str) -> dict:
    """Parse README and VERSION files for project info."""
    metadata = {
        "name": path.split('/')[-1],  # Default to directory name
        "version": None,
        "description": None,
        "has_readme": False,
        "has_git": False,
    }
    
    # Check for VERSION file
    version_result = await conn.run(f'cat {path}/VERSION 2>/dev/null', check=False)
    if version_result.exit_status == 0:
        metadata["version"] = version_result.stdout.strip()
    
    # Check for package.json version
    if not metadata["version"]:
        pkg_result = await conn.run(f'cat {path}/package.json 2>/dev/null | grep \'"version"\'', check=False)
        if pkg_result.exit_status == 0:
            # Extract version from "version": "1.0.0"
            import re
            match = re.search(r'"version":\s*"([^"]+)"', pkg_result.stdout)
            if match:
                metadata["version"] = match.group(1)
    
    # Check for README
    readme_result = await conn.run(f'test -f {path}/README.md && echo yes', check=False)
    metadata["has_readme"] = readme_result.stdout.strip() == "yes"
    
    # Extract description from README first line (after title)
    if metadata["has_readme"]:
        desc_result = await conn.run(f'head -5 {path}/README.md 2>/dev/null | grep -v "^#" | grep -v "^$" | head -1', check=False)
        if desc_result.exit_status == 0 and desc_result.stdout.strip():
            metadata["description"] = desc_result.stdout.strip()[:200]
    
    # Check for .git
    git_result = await conn.run(f'test -d {path}/.git && echo yes', check=False)
    metadata["has_git"] = git_result.stdout.strip() == "yes"
    
    # Get git remote URL if available
    if metadata["has_git"]:
        remote_result = await conn.run(f'cd {path} && git remote get-url origin 2>/dev/null', check=False)
        if remote_result.exit_status == 0:
            metadata["git_remote"] = remote_result.stdout.strip()
    
    return metadata


# In-memory project registry (will be replaced with DB later)
_discovered_projects = []


async def register_project(name: str, server: str, path: str, version: Optional[str] = None, **kwargs) -> dict:
    """Add a discovered project to the registry."""
    project = {
        "id": len(_discovered_projects) + 1,
        "name": name,
        "server": server,
        "path": path,
        "version": version,
        "registered_at": datetime.utcnow().isoformat(),
        "last_scanned_at": datetime.utcnow().isoformat(),
        **kwargs
    }
    
    # Check if already registered
    existing = next((p for p in _discovered_projects if p["path"] == path and p["server"] == server), None)
    if existing:
        # Update existing
        existing.update(project)
        return existing
    
    _discovered_projects.append(project)
    return project


async def discover_all_projects() -> list[dict]:
    """Full discovery scan across all reachable servers."""
    results = []
    
    # First check which servers are reachable
    servers = await scan_servers()
    reachable_servers = [s for s in servers if s["reachable"]]
    
    # Scan each reachable server for projects
    for server in reachable_servers:
        projects = await detect_projects(server["ip"], server["user"])
        for project in projects:
            registered = await register_project(
                name=project["name"],
                server=server["ip"],
                path=project["path"],
                version=project.get("version"),
                description=project.get("description"),
                has_readme=project.get("has_readme"),
                has_git=project.get("has_git"),
                git_remote=project.get("git_remote"),
                server_name=server["name"],
            )
            results.append(registered)
    
    return results


def get_registered_projects() -> list[dict]:
    """Return all registered projects."""
    return _discovered_projects.copy()


def clear_registry():
    """Clear the in-memory registry (for testing)."""
    global _discovered_projects
    _discovered_projects = []
