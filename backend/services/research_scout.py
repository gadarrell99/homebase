"""Research Scout - Finds useful AI tools, plugins, and ideas"""
import sqlite3
import json
import urllib.request
import ssl
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "agents.db"

# Subreddits focused on tools and building, not complaints
SUBREDDITS = [
    'LocalLLaMA',        # Local AI models, tools
    'SelfHosted',        # Self-hosted tools
    'AutoGPT',           # Agent frameworks
    'LangChain',         # LLM tooling
    'MachineLearning',   # ML tools and papers
    'OpenAI',            # API tips, tools
    'ClaudeAI',          # Claude tools
    'ChatGPTPro',        # Power user tips
    'AItools',           # AI tool discoveries
    'coding',            # Dev tools
    'devops',            # Automation
    'homelab'            # Self-hosted infra
]

# Keywords that indicate USEFUL content
POSITIVE_KEYWORDS = [
    'tool', 'plugin', 'extension', 'library', 'framework',
    'workflow', 'automation', 'script', 'integration',
    'tutorial', 'guide', 'how to', 'tip', 'trick',
    'released', 'launched', 'announcing', 'new version',
    'open source', 'github', 'self-hosted',
    'api', 'sdk', 'cli', 'dashboard',
    'agent', 'assistant', 'bot', 'mcp', 'langchain',
    'productivity', 'efficiency', 'faster',
    'code generation', 'coding assistant',
    'sales', 'crm', 'customer', 'support',
    'monitor', 'alert', 'logging', 'observability'
]

# Keywords that indicate COMPLAINTS (skip these)
NEGATIVE_KEYWORDS = [
    'rant', 'vent', 'frustrated', 'angry', 'hate',
    'worst', 'terrible', 'awful', 'garbage', 'trash',
    'why does', 'why is', 'anyone else',
    'unpopular opinion', 'am i the only',
    'disappointed', 'let down', 'misleading',
    'paywall', 'too expensive', 'rip off',
    'banned', 'suspended', 'account',
    'meme', 'funny', 'joke', 'lol', 'lmao'
]

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db

def score_relevance(title, text=''):
    """Score based on usefulness, filter out complaints"""
    content = (title + ' ' + text).lower()
    
    # Check for negative keywords first - skip if found
    for neg in NEGATIVE_KEYWORDS:
        if neg in content:
            return -1  # Skip this item
    
    score = 0
    
    # Score positive keywords
    for pos in POSITIVE_KEYWORDS:
        if pos in content:
            score += 10
    
    # Bonus for action words
    if any(w in content for w in ['released', 'launched', 'announcing', 'introducing']):
        score += 20
    
    # Bonus for tools/repos
    if 'github.com' in content or 'github' in content:
        score += 15
    
    # Bonus for tutorials
    if any(w in content for w in ['tutorial', 'guide', 'how to', 'step by step']):
        score += 15
    
    # Bonus for open source
    if 'open source' in content or 'opensource' in content:
        score += 10
    
    return min(score, 100)

def fetch_reddit(subreddit, limit=10):
    """Fetch recent posts from a subreddit"""
    items = []
    try:
        url = f'https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}'
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'Sentinel/1.0 (Research Scout)'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            for post in data.get('data', {}).get('children', []):
                p = post.get('data', {})
                # Skip if low upvotes (probably not useful)
                if p.get('ups', 0) < 10:
                    continue
                items.append({
                    'source': f'reddit/r/{subreddit}',
                    'title': p.get('title', ''),
                    'url': f"https://reddit.com{p.get('permalink', '')}",
                    'summary': p.get('selftext', '')[:500],
                    'created': datetime.fromtimestamp(p.get('created_utc', 0)).isoformat(),
                    'upvotes': p.get('ups', 0)
                })
    except Exception as e:
        print(f'Reddit fetch error for {subreddit}: {e}')
    return items

def scan_all_subreddits():
    """Scan all configured subreddits"""
    all_items = []
    for sub in SUBREDDITS:
        items = fetch_reddit(sub, limit=10)
        all_items.extend(items)
    return all_items

def save_item(source, title, url, summary, relevance_score):
    """Save a research item to database"""
    db = get_db()
    existing = db.execute('SELECT id FROM research_items WHERE url = ?', (url,)).fetchone()
    if existing:
        db.close()
        return None
    db.execute('''
        INSERT INTO research_items (source, title, url, summary, relevance_score)
        VALUES (?, ?, ?, ?, ?)
    ''', (source, title, url, summary, relevance_score))
    db.commit()
    item_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    db.close()
    return item_id

def get_items(status='new', limit=50):
    """Get research items by status"""
    db = get_db()
    rows = db.execute(
        'SELECT * FROM research_items WHERE status = ? ORDER BY relevance_score DESC, discovered_at DESC LIMIT ?',
        (status, limit)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

def update_item_status(item_id, status, reviewed_by='system'):
    """Update item status"""
    db = get_db()
    db.execute(
        'UPDATE research_items SET status = ?, reviewed_by = ?, reviewed_at = datetime("now") WHERE id = ?',
        (status, reviewed_by, item_id)
    )
    db.commit()
    db.close()
    return True

def get_daily_summary():
    """Get summary for daily digest"""
    db = get_db()
    since = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    new_count = db.execute('SELECT COUNT(*) FROM research_items WHERE discovered_at > ?', (since,)).fetchone()[0]
    high_relevance = db.execute(
        'SELECT * FROM research_items WHERE discovered_at > ? AND relevance_score >= 20 ORDER BY relevance_score DESC LIMIT 10',
        (since,)
    ).fetchall()
    db.close()
    return {
        'new_items_24h': new_count,
        'high_relevance': [dict(r) for r in high_relevance]
    }

def run_scan():
    """Run full research scan - only saves useful items"""
    results = {'scanned': 0, 'saved': 0, 'skipped': 0, 'filtered': 0}
    
    items = scan_all_subreddits()
    results['scanned'] = len(items)
    
    for item in items:
        score = score_relevance(item['title'], item['summary'])
        
        if score < 0:
            # Filtered out (complaint/rant)
            results['filtered'] += 1
        elif score >= 15:
            # Useful enough to save
            saved = save_item(
                item['source'],
                item['title'],
                item['url'],
                item['summary'],
                score
            )
            if saved:
                results['saved'] += 1
            else:
                results['skipped'] += 1  # Duplicate
        else:
            results['skipped'] += 1  # Too low score
    
    return results
