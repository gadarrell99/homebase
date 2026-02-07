"""Cron Monitor Service - Collects cron jobs from Rize-Apps and agents"""
import subprocess
import re
from datetime import datetime

# Known agent hosts with SSH access
AGENT_HOSTS = [
    {"name": "Rize-Apps", "user": "rizeadmin", "host": "localhost"},
    {"name": "David", "user": "david", "host": "192.168.65.241"},
]

def parse_cron_line(line, source):
    """Parse a single crontab line into structured data."""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    # Match cron schedule pattern
    match = re.match(r'^([\*0-9,\-/]+\s+[\*0-9,\-/]+\s+[\*0-9,\-/]+\s+[\*0-9,\-/]+\s+[\*0-9,\-/]+)\s+(.+)$', line)
    if not match:
        return None
    
    schedule = match.group(1)
    command = match.group(2)
    
    # Extract script name from command
    script = command
    # Try to find the actual script file
    script_match = re.search(r'([^\s/]+\.(sh|py))', command)
    if script_match:
        script = script_match.group(1)
    elif '&&' in command:
        # Get the last command after &&
        parts = command.split('&&')
        script = parts[-1].strip().split()[0] if parts else command
    
    return {
        "schedule": schedule,
        "command": command,
        "script": script,
        "source": source,
        "status": "ok"  # We'll enhance this later
    }

def get_local_crons():
    """Get cron jobs from local system."""
    jobs = []
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                job = parse_cron_line(line, "Rize-Apps")
                if job:
                    jobs.append(job)
    except Exception as e:
        pass
    return jobs

def get_remote_crons(host_info):
    """Get cron jobs from a remote host via SSH."""
    jobs = []
    try:
        cmd = ['ssh', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no',
               f"{host_info['user']}@{host_info['host']}", 'crontab -l']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                job = parse_cron_line(line, host_info['name'])
                if job:
                    jobs.append(job)
    except Exception as e:
        pass
    return jobs

def get_all_crons():
    """Get all cron jobs from Rize-Apps and known agents."""
    all_jobs = []
    
    # Get local crons (Rize-Apps)
    all_jobs.extend(get_local_crons())
    
    # Get remote crons from agents
    for host in AGENT_HOSTS:
        if host['host'] != 'localhost':
            all_jobs.extend(get_remote_crons(host))
    
    return {
        "jobs": all_jobs,
        "total": len(all_jobs),
        "sources": list(set(j['source'] for j in all_jobs)),
        "collected_at": datetime.utcnow().isoformat() + "Z"
    }

def get_cron_summary():
    """Get summary of cron job status."""
    jobs = get_all_crons()
    return {
        "total": jobs["total"],
        "by_source": {src: len([j for j in jobs["jobs"] if j["source"] == src]) for src in jobs["sources"]},
        "collected_at": jobs["collected_at"]
    }
