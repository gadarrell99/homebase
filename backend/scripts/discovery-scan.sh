#!/bin/bash
cd "$(dirname "$0")/../.."
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
QUEUE_FILE="data/discovery-queue.json"
SERVERS_FILE="data/servers.json"

KNOWN_IPS=$(python3 -c "
import json
with open('$SERVERS_FILE') as f:
    d = json.load(f)
ips = [s['ip'] for s in d.get('servers', [])]
print(' '.join(ips))
" 2>/dev/null)

echo "Known IPs: $KNOWN_IPS"
echo "Scanning 192.168.65.0/24..."

DISCOVERED=""
for i in $(seq 1 254); do
  IP="192.168.65.$i"
  if echo " $KNOWN_IPS " | grep -q " $IP "; then
    continue
  fi
  if ping -c 1 -W 1 "$IP" > /dev/null 2>&1; then
    echo "  Found unknown: $IP"
    PORTS=""
    for PORT in 22 80 443 3000 3389 5000 8000 8080 8443; do
      if timeout 1 bash -c "echo >/dev/tcp/$IP/$PORT" 2>/dev/null; then
        [ -n "$PORTS" ] && PORTS="$PORTS,"
        PORTS="${PORTS}${PORT}"
      fi
    done
    HOSTNAME=$(ssh -o ConnectTimeout=2 -o BatchMode=yes -o StrictHostKeyChecking=no "root@$IP" "hostname" 2>/dev/null || echo "")
    [ -z "$HOSTNAME" ] && HOSTNAME=$(nslookup "$IP" 2>/dev/null | grep "name =" | awk '{print $NF}' | sed 's/\.$//')
    DISCOVERED="${DISCOVERED}{\"ip\":\"$IP\",\"ports\":[$PORTS],\"hostname\":\"$HOSTNAME\",\"first_seen\":\"$TIMESTAMP\"},"
  fi
done

python3 << PYEOF
import json, os

queue_file = "$QUEUE_FILE"
discovered_raw = '''[${DISCOVERED%,}]'''

try:
    discovered = json.loads(discovered_raw) if discovered_raw.strip() != '[]' else []
except:
    discovered = []

existing = {"discovered": [], "dismissed": []}
if os.path.exists(queue_file):
    try:
        with open(queue_file) as f:
            existing = json.load(f)
    except:
        pass

existing_ips = {d["ip"] for d in existing.get("discovered", [])}
dismissed_ips = {d["ip"] for d in existing.get("dismissed", [])}

new_count = 0
for d in discovered:
    if d["ip"] not in existing_ips and d["ip"] not in dismissed_ips:
        d["id"] = f"disc-{d['ip'].split('.')[-1]}"
        d["status"] = "new"
        existing.setdefault("discovered", []).append(d)
        new_count += 1

existing["last_scan"] = "$TIMESTAMP"
existing["known_ips"] = "$KNOWN_IPS".split()

with open(queue_file, 'w') as f:
    json.dump(existing, f, indent=2)

total = len(existing.get("discovered", []))
print(f"Discovery complete: {new_count} new, {total} total in queue")
PYEOF
