import json, sqlite3, os
BASE = os.path.join(os.path.dirname(__file__), '..', '..')
def get_enriched_servers():
    with open(os.path.join(BASE, "data", "servers.json")) as f:
        data = json.load(f)
    return data.get("servers", data if isinstance(data, list) else [])
