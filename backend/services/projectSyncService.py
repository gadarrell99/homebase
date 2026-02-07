"""
Project Docs Sync Service
SSH to servers and pull markdown documentation files.
"""

import asyncio
import asyncssh
import sqlite3
import re
import os
from datetime import datetime
from typing import Optional, List, Dict

# Database path (same as database.py)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "homebase.db")

# Project configurations
PROJECTS = [
    {"name": "demos", "server_ip": "192.168.65.246", "user": "demos", "path": "~/bps-ai"},
    {"name": "nexus", "server_ip": "192.168.65.247", "user": "contextadmin", "path": "/opt/it-nexus"},
    {"name": "property-rize", "server_ip": "192.168.65.245", "user": "rizeadmin", "path": "~/property-rize"},
    {"name": "homebase", "server_ip": "192.168.65.245", "user": "rizeadmin", "path": "~/homebase"},
    {"name": "relay", "server_ip": "192.168.65.248", "user": "relayadmin", "path": "~/relay"},
    {"name": "dockyard", "server_ip": "192.168.65.252", "user": "dockyardadmin", "path": "~/dockyard-wifi-portal"},
    {"name": "vector", "server_ip": "192.168.65.249", "user": "betadmin", "path": "~/bet"},
    {"name": "premier-emr", "server_ip": "192.168.65.239", "user": "emradmin", "path": "~/premier-emr"},
]

DOC_TYPES = ["README", "TODO", "CHANGELOG", "PROJECT_PLAN", "CLAUDE"]


def init_project_tables():
    """Initialize project docs tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Project docs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            server_ip TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            content TEXT,
            version TEXT,
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project, doc_type)
        )
    ''')

    # Project TODOs table (parsed from TODO.md)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            priority TEXT,
            status TEXT DEFAULT 'open',
            description TEXT,
            completed_version TEXT,
            completed_date TEXT,
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_project_todos_project
        ON project_todos(project)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_project_todos_status
        ON project_todos(status)
    ''')

    conn.commit()
    conn.close()
    print('[ProjectSync] Tables initialized')


async def fetch_doc_content(server_ip: str, user: str, path: str, doc_type: str) -> Optional[str]:
    """SSH to server and fetch a single doc file."""
    try:
        async with asyncssh.connect(
            server_ip,
            username=user,
            known_hosts=None,
            connect_timeout=10
        ) as conn:
            result = await conn.run(f"cat {path}/{doc_type}.md 2>/dev/null", check=False)
            if result.exit_status == 0 and result.stdout.strip():
                return result.stdout.strip()
    except Exception as e:
        print(f"[ProjectSync] Error fetching {doc_type}.md from {server_ip}: {e}")
    return None


def extract_version(content: str) -> Optional[str]:
    """Extract version from CHANGELOG.md content."""
    if not content:
        return None

    # Look for patterns like [1.2.3], v1.2.3, version 1.2.3
    patterns = [
        r'\[(\d+\.\d+\.\d+)\]',  # [1.2.3]
        r'v(\d+\.\d+\.\d+)',      # v1.2.3
        r'version\s+(\d+\.\d+\.\d+)',  # version 1.2.3
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def parse_todos(content: str, project: str) -> List[Dict]:
    """Parse TODO.md content into individual todo items."""
    todos = []
    if not content:
        return todos

    current_priority = None
    current_status = 'open'

    lines = content.split('\n')
    for line in lines:
        line_stripped = line.strip()

        # Check for priority headers
        if '### P0' in line or '## P0' in line:
            current_priority = 'P0'
            current_status = 'open'
        elif '### P1' in line or '## P1' in line:
            current_priority = 'P1'
            current_status = 'open'
        elif '### P2' in line or '## P2' in line:
            current_priority = 'P2'
            current_status = 'open'
        elif '### P3' in line or '## P3' in line:
            current_priority = 'P3'
            current_status = 'open'
        elif '## Completed' in line or '### Completed' in line:
            current_status = 'completed'
            current_priority = None
        elif '## Open' in line or '### Open' in line:
            current_status = 'open'

        # Check for todo items
        if line_stripped.startswith('- [ ]') or line_stripped.startswith('- [x]'):
            is_completed = line_stripped.startswith('- [x]')
            description = line_stripped[5:].strip()

            # Extract version if in completed section
            version_match = re.search(r'\(v?(\d+\.\d+\.\d+)\)', description)
            completed_version = version_match.group(1) if version_match else None

            # Extract date if present
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', description)
            completed_date = date_match.group(1) if date_match else None

            todos.append({
                'project': project,
                'priority': current_priority,
                'status': 'completed' if is_completed else current_status,
                'description': description,
                'completed_version': completed_version,
                'completed_date': completed_date
            })

    return todos


def save_doc(project: str, server_ip: str, doc_type: str, content: str, version: str = None):
    """Save or update a document in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO project_docs (project, server_ip, doc_type, content, version, last_synced)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (project, server_ip, doc_type, content, version, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()


def save_todos(project: str, todos: List[Dict]):
    """Replace all todos for a project with new ones."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete old todos for this project
    cursor.execute('DELETE FROM project_todos WHERE project = ?', (project,))

    # Insert new todos
    for todo in todos:
        cursor.execute('''
            INSERT INTO project_todos (project, priority, status, description, completed_version, completed_date, last_synced)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            todo['project'],
            todo.get('priority'),
            todo.get('status', 'open'),
            todo.get('description'),
            todo.get('completed_version'),
            todo.get('completed_date'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))

    conn.commit()
    conn.close()


async def sync_project(project_config: Dict) -> Dict:
    """Sync all docs for a single project."""
    project = project_config['name']
    server_ip = project_config['server_ip']
    user = project_config['user']
    path = project_config['path']

    result = {
        'project': project,
        'server_ip': server_ip,
        'synced_docs': [],
        'version': None,
        'todo_count': {'open': 0, 'completed': 0}
    }

    print(f"[ProjectSync] Syncing {project} from {server_ip}:{path}")

    # Fetch all doc types
    for doc_type in DOC_TYPES:
        content = await fetch_doc_content(server_ip, user, path, doc_type)
        if content:
            version = None
            if doc_type == 'CHANGELOG':
                version = extract_version(content)
                result['version'] = version

            save_doc(project, server_ip, doc_type, content, version)
            result['synced_docs'].append(doc_type)

            # Parse TODOs
            if doc_type == 'TODO':
                todos = parse_todos(content, project)
                save_todos(project, todos)
                result['todo_count']['open'] = sum(1 for t in todos if t['status'] == 'open')
                result['todo_count']['completed'] = sum(1 for t in todos if t['status'] == 'completed')

    return result


async def sync_all_projects() -> List[Dict]:
    """Sync all projects in parallel."""
    print("[ProjectSync] Starting full sync...")
    tasks = [sync_project(p) for p in PROJECTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    valid_results = [r for r in results if isinstance(r, dict)]

    print(f"[ProjectSync] Sync complete: {len(valid_results)}/{len(PROJECTS)} projects")
    return valid_results


def get_all_projects() -> List[Dict]:
    """Get summary of all projects from database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get distinct projects with their latest info
    cursor.execute('''
        SELECT DISTINCT
            pd.project,
            pd.server_ip,
            MAX(pd.last_synced) as last_synced,
            (SELECT version FROM project_docs WHERE project = pd.project AND doc_type = 'CHANGELOG' LIMIT 1) as version
        FROM project_docs pd
        GROUP BY pd.project
        ORDER BY pd.project
    ''')

    projects = []
    for row in cursor.fetchall():
        project_dict = dict(row)

        # Get doc types for this project
        cursor.execute('SELECT doc_type FROM project_docs WHERE project = ?', (row['project'],))
        project_dict['docs'] = [r[0] for r in cursor.fetchall()]

        # Get todo counts
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM project_todos
            WHERE project = ?
            GROUP BY status
        ''', (row['project'],))
        todo_counts = {r[0]: r[1] for r in cursor.fetchall()}
        project_dict['todo_open'] = todo_counts.get('open', 0)
        project_dict['todo_completed'] = todo_counts.get('completed', 0)

        # Determine status badge based on open todos
        open_todos = project_dict['todo_open']
        if open_todos == 0:
            project_dict['status'] = 'healthy'
        elif open_todos <= 5:
            project_dict['status'] = 'good'
        elif open_todos <= 10:
            project_dict['status'] = 'warning'
        else:
            project_dict['status'] = 'busy'

        projects.append(project_dict)

    conn.close()
    return projects


def get_project_detail(project_name: str) -> Optional[Dict]:
    """Get full details for a single project."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get docs
    cursor.execute('SELECT * FROM project_docs WHERE project = ?', (project_name,))
    docs = {row['doc_type']: dict(row) for row in cursor.fetchall()}

    if not docs:
        conn.close()
        return None

    # Get todos
    cursor.execute('SELECT * FROM project_todos WHERE project = ? ORDER BY priority, status', (project_name,))
    todos = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        'project': project_name,
        'docs': docs,
        'todos': todos
    }


def get_project_todos(project_name: str) -> List[Dict]:
    """Get all todos for a project."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM project_todos
        WHERE project = ?
        ORDER BY
            CASE priority
                WHEN 'P0' THEN 1
                WHEN 'P1' THEN 2
                WHEN 'P2' THEN 3
                WHEN 'P3' THEN 4
                ELSE 5
            END,
            status
    ''', (project_name,))

    todos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return todos


def get_overall_health() -> Dict:
    """Get overall health summary across all projects."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(DISTINCT project) FROM project_docs')
    total_projects = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM project_todos WHERE status = ?', ('open',))
    total_open_todos = cursor.fetchone()[0]

    cursor.execute('''
        SELECT priority, COUNT(*) as count
        FROM project_todos
        WHERE status = 'open'
        GROUP BY priority
    ''')
    priority_counts = {r[0]: r[1] for r in cursor.fetchall() if r[0]}

    cursor.execute('SELECT MAX(last_synced) FROM project_docs')
    last_sync = cursor.fetchone()[0]

    conn.close()

    return {
        'total_projects': total_projects,
        'total_open_todos': total_open_todos,
        'p0_count': priority_counts.get('P0', 0),
        'p1_count': priority_counts.get('P1', 0),
        'p2_count': priority_counts.get('P2', 0),
        'p3_count': priority_counts.get('P3', 0),
        'last_sync': last_sync
    }


# Initialize tables on import
init_project_tables()
