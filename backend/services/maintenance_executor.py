#!/usr/bin/env python3
"""
Sentinel Maintenance Executor — Runs scheduled maintenance tasks
Processes maintenance_queue entries during maintenance window
"""
import subprocess
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / "homebase" / "data" / "agents.db"
MAX_TASKS = 10
CMD_TIMEOUT = 300  # 5 min per command

def log_event(conn, queue_id, event, details=None):
    """Log event to maintenance_log"""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO maintenance_log (queue_id, event, details) VALUES (?, ?, ?)",
        (queue_id, event, details)
    )
    conn.commit()

def run_command(target, cmd, timeout=CMD_TIMEOUT):
    """Run command on target server"""
    if target in ["Rize-Apps", "192.168.65.245", "localhost"]:
        full_cmd = cmd
    else:
        user_map = {
            "Talos": "talosadmin@192.168.65.237",
            "Agents": "agents@192.168.65.241",
            "Demos": "demos@192.168.65.246",
            "Vector": "betadmin@192.168.65.249",
        }
        ssh_target = user_map.get(target, target)
        full_cmd = f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {ssh_target} {repr(cmd)}"
    
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def execute_task(conn, task):
    """Execute a single maintenance task"""
    task_id = task[0]
    task_name = task[1]
    target = task[2]
    commands = json.loads(task[3])
    rollback_commands = json.loads(task[12]) if task[12] else []
    
    cur = conn.cursor()
    cur.execute("UPDATE maintenance_queue SET status='running', started_at=? WHERE id=?",
                (datetime.now().isoformat(), task_id))
    conn.commit()
    log_event(conn, task_id, "started", f"Executing {len(commands)} commands on {target}")
    
    output_log = []
    success = True
    
    for i, cmd in enumerate(commands):
        log_event(conn, task_id, "command_start", f"Step {i+1}: {cmd[:100]}")
        ok, output = run_command(target, cmd)
        output_log.append(f"Step {i+1}: {'OK' if ok else 'FAILED'}\n{output}")
        
        if not ok:
            success = False
            log_event(conn, task_id, "command_failed", output[:500])
            
            # Execute rollback if present
            if rollback_commands:
                log_event(conn, task_id, "rollback_start", f"Running {len(rollback_commands)} rollback commands")
                for rb_cmd in rollback_commands:
                    run_command(target, rb_cmd)
            break
        else:
            log_event(conn, task_id, "command_success", f"Step {i+1} completed")
    
    final_status = "complete" if success else "failed"
    cur.execute("""
        UPDATE maintenance_queue 
        SET status=?, completed_at=?, output=?, error=?
        WHERE id=?
    """, (final_status, datetime.now().isoformat(), 
          "\n".join(output_log), None if success else output_log[-1], task_id))
    conn.commit()
    log_event(conn, task_id, "finished", final_status)
    
    return success

def send_summary(completed, failed):
    """Send email summary"""
    if not completed and not failed:
        return
    
    subject = f"Maintenance Complete: {len(completed)} OK, {len(failed)} Failed"
    body = f"Maintenance run completed at {datetime.now().isoformat()}\n\n"
    body += f"Completed: {len(completed)}\nFailed: {len(failed)}\n\n"
    
    if failed:
        body += "FAILED TASKS:\n"
        for t in failed:
            body += f"  - {t}\n"
    
    try:
        subprocess.run([
            "ssh", "agents@192.168.65.241",
            f"python3 ~/scripts/send-email.py sentinel@rize.bm artiedarrell@gmail.com '{subject}' '{body}'"
        ], timeout=30)
    except:
        pass

def main():
    print("=" * 50)
    print(f"MAINTENANCE EXECUTOR — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get pending tasks that are due
    cur.execute("""
        SELECT * FROM maintenance_queue 
        WHERE status='pending' 
          AND (scheduled_time IS NULL OR scheduled_time <= datetime('now'))
        ORDER BY 
          CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END,
          created_at
        LIMIT ?
    """, (MAX_TASKS,))
    
    tasks = cur.fetchall()
    print(f"Found {len(tasks)} pending tasks")
    
    completed = []
    failed = []
    
    for task in tasks:
        print(f"\nExecuting: {task[1]} on {task[2]}")
        if execute_task(conn, task):
            completed.append(task[1])
            print("  ✅ Complete")
        else:
            failed.append(task[1])
            print("  ❌ Failed")
    
    conn.close()
    
    print("\n" + "-" * 50)
    print(f"Complete: {len(completed)}, Failed: {len(failed)}")
    
    send_summary(completed, failed)

if __name__ == "__main__":
    main()
