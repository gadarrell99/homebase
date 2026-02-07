"""
Shared navbar and page wrapper for Homebase.
All static HTML pages should use these helpers for consistency.
"""

def get_navbar(active="home"):
    """
    Returns HTML string for the shared navbar.
    active param highlights the current page.
    Valid values: home, servers, projects, agents, metrics, security
    """
    nav_items = [
        ("home", "/", "Home"),
        ("servers", "/servers", "Servers"),
        ("projects", "/projects", "Projects"),
        ("agents", "/agents", "Agents"),
        ("sentinel", "/sentinel", "Sentinel"),
        ("metrics", "/metrics", "Metrics"),
        ("security", "/security", "Security"),
        ("project-status", "/project-status", "Status"),
    ]
    
    items_html = []
    for key, href, label in nav_items:
        active_class = ' class="active"' if key == active else ''
        items_html.append(f'<a href="{href}"{active_class}>{label}</a>')
    
    return f'''<nav class="main-nav">
    <a href="/" class="logo">🏠 Homebase</a>
    <div class="nav-links">
        {' '.join(items_html)}
    </div>
    <div class="nav-right">
        <button class="theme-toggle" onclick="toggleTheme()" title="Toggle Theme">🌓</button>
        <button class="print-btn" onclick="window.print()" title="Export PDF">🖨️</button>
        <div class="dropdown">
            <button class="dropdown-btn">⚙️</button>
            <div class="dropdown-content">
                <a href="/credentials">🔐 Credentials</a>
                <a href="/settings">⚙️ Settings</a>
                <a href="/backups">💾 Backups</a>
                <a href="/audit-tracker">📋 Audit Tracker</a>
            </div>
        </div>
    </div>
</nav>'''


def get_base_css():
    """Returns the base CSS shared across all pages."""
    return '''
:root {
    --bg-body: #0f172a; --bg-nav: #1e293b; --bg-card: #1e293b; --bg-hover: #334155;
    --text-main: #e2e8f0; --text-muted: #94a3b8; --border-color: #334155;
    --link-color: #60a5fa; --link-hover: #93c5fd; --shadow: 0 10px 25px rgba(0,0,0,0.3);
}
[data-theme="light"] {
    --bg-body: #f1f5f9; --bg-nav: #ffffff; --bg-card: #ffffff; --bg-hover: #e2e8f0;
    --text-main: #0f172a; --text-muted: #64748b; --border-color: #cbd5e1;
    --link-color: #2563eb; --link-hover: #1d4ed8; --shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg-body); color: var(--text-main); min-height: 100vh; transition: background 0.3s, color 0.3s; }
a { color: var(--link-color); text-decoration: none; }
a:hover { color: var(--link-hover); }

/* Nav */
.main-nav { display: flex; align-items: center; padding: 0.75rem 1.5rem; background: var(--bg-nav); border-bottom: 1px solid var(--border-color); position: sticky; top: 0; z-index: 100; }
.main-nav .logo { font-size: 1.1rem; font-weight: 600; color: var(--text-main); margin-right: 2rem; }
.main-nav .nav-links { display: flex; gap: 0.25rem; flex: 1; }
.main-nav .nav-links a { color: var(--text-muted); padding: 0.5rem 0.75rem; border-radius: 0.375rem; font-size: 0.875rem; transition: all 0.15s; }
.main-nav .nav-links a:hover, .main-nav .nav-links a.active { color: var(--text-main); background: var(--bg-hover); }
.main-nav .nav-right { display: flex; gap: 0.5rem; align-items: center; }

/* Controls */
.theme-toggle, .print-btn, .dropdown-btn { background: transparent; border: none; color: var(--text-muted); font-size: 1.2rem; cursor: pointer; padding: 0.5rem; border-radius: 0.375rem; transition: all 0.15s; }
.theme-toggle:hover, .print-btn:hover, .dropdown-btn:hover { background: var(--bg-hover); color: var(--text-main); }
.dropdown { position: relative; display: inline-block; }
.dropdown-content { display: none; position: absolute; right: 0; top: 100%; background: var(--bg-nav); border: 1px solid var(--border-color); border-radius: 0.5rem; min-width: 180px; box-shadow: var(--shadow); z-index: 200; }
.dropdown:hover .dropdown-content { display: block; }
.dropdown-content a { display: block; padding: 0.75rem 1rem; color: var(--text-muted); font-size: 0.875rem; }
.dropdown-content a:hover { background: var(--bg-hover); color: var(--text-main); }

/* Layout */
.page-container { padding: 1.5rem; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 1.5rem; }
.page-header h1 { font-size: 1.75rem; font-weight: 600; margin-bottom: 0.25rem; color: var(--text-main); }
.page-header p { color: var(--text-muted); font-size: 0.875rem; }
.summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.summary-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 0.5rem; padding: 1rem; text-align: center; }
.summary-card .num { font-size: 2rem; font-weight: 700; }
.summary-card .lbl { color: var(--text-muted); font-size: 0.75rem; margin-top: 0.25rem; }

/* Components */
.btn { display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.5rem 0.875rem; border-radius: 0.375rem; font-size: 0.8rem; font-weight: 500; border: none; cursor: pointer; transition: all 0.15s; }
.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { background: var(--bg-hover); color: var(--text-main); }
.btn-secondary:hover { background: var(--border-color); }
.card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1.5rem; }

/* Status Badges */
.status { 
    display: inline-block;
    padding: 0.25rem 0.625rem; 
    border-radius: 1rem; 
    font-size: 0.7rem; 
    font-weight: 600; 
    text-transform: uppercase;
}
.status-ok, .status-healthy, .status-online { background: #166534; color: #86efac; }
.status-warning, .status-degraded { background: #854d0e; color: #fde047; }
.status-error, .status-critical, .status-offline { background: #991b1b; color: #fca5a5; }
.status-building, .status-new { background: #1e40af; color: #93c5fd; }
.status-stale { background: #374151; color: #9ca3af; }

/* Mobile */
@media (max-width: 768px) {
    .main-nav { flex-wrap: wrap; padding: 0.75rem 1rem; }
    .main-nav .logo { margin-right: auto; }
    .main-nav .nav-links { order: 3; width: 100%; margin-top: 0.75rem; overflow-x: auto; flex-wrap: nowrap; padding-bottom: 0.5rem; }
    .page-container { padding: 1rem; }
    .summary-cards { grid-template-columns: repeat(2, 1fr); }
}

/* Print */
@media print {
    .main-nav, .btn, .server-actions, .quick-actions { display: none !important; }
    body { background: white; color: black; }
    .page-container { max-width: 100%; padding: 0; }
    .server-card, .summary-card, .card { border: 1px solid #ccc; break-inside: avoid; box-shadow: none; }
    * { color: black !important; background: transparent !important; }
}
'''


def wrap_page(title, active, body_html, extra_css="", extra_js=""):
    """
    Returns a complete HTML page with navbar and base styling.
    
    Args:
        title: Page title (shown in browser tab)
        active: Active nav item (home, servers, projects, agents, metrics, security)
        body_html: The main page content HTML
        extra_css: Additional CSS specific to this page
        extra_js: Additional JavaScript for this page
    """
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Homebase</title>
    <style>
{get_base_css()}
{extra_css}
    </style>
</head>
<body>
    {get_navbar(active)}
    <div class="page-container">
        {body_html}
    </div>
    <script>
    function toggleTheme() {{
        const body = document.body;
        const current = body.getAttribute('data-theme');
        const next = current === 'light' ? 'dark' : 'light';
        body.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    }}
    (function() {{
        const saved = localStorage.getItem('theme') || 'dark';
        document.body.setAttribute('data-theme', saved);
    }})();
{extra_js}
    </script>
</body>
</html>'''
