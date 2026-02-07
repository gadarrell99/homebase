#!/bin/bash
cd "$(dirname "$0")/../.."
START=$(date +%s)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TOMORROW=$(date -u -d "+1 day" +"%Y-%m-%dT03:00:00Z" 2>/dev/null || date -u +"%Y-%m-%dT03:00:00Z")
OUTFILE="data/security-scans.json"
TMPDIR=$(mktemp -d)

SERVERS=(
    "talos|talosadmin@192.168.65.237"
    "agents|agents@192.168.65.241"
    "rize-apps|rizeadmin@192.168.65.245"
    "demos|demos@192.168.65.246"
    "vector|betadmin@192.168.65.249"
)

run_remote() {
  local user_host="$1"
  local cmd="$2"
  local timeout="${3:-8}"
  ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes \
    "$user_host" "timeout $timeout bash -c '$cmd'" 2>/dev/null
}

run_check() {
  local name="$1" status="$2" detail="$3"
  echo "{\"name\":\"$name\",\"status\":\"$status\",\"detail\":\"$detail\"}"
}

scan_server() {
  local SID="$1" IP="$2" USER="$3"
  local UH="$USER@$IP"
  local CHECKS=()
  local PASS=0 WARN=0 FAIL=0

  if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$UH" "echo ok" >/dev/null 2>&1; then
    CHECKS+=("$(run_check "SSH Reachable" "pass" "Connected to $IP")")
    PASS=$((PASS+1))
  else
    echo "{\"score\":0,\"reachable\":false,\"checks\":[$(run_check "SSH Reachable" "fail" "Connection timed out")]}"
    return
  fi

  local UFW=$(run_remote "$UH" "sudo ufw status 2>/dev/null | head -1" 3)
  if echo "$UFW" | grep -qi "active"; then
    RULES=$(run_remote "$UH" "sudo ufw status | grep -c ALLOW" 3)
    CHECKS+=("$(run_check "UFW Active" "pass" "Active, $RULES rules")")
    PASS=$((PASS+1))
  elif echo "$UFW" | grep -qi "inactive"; then
    CHECKS+=("$(run_check "UFW Active" "fail" "Firewall inactive")")
    FAIL=$((FAIL+1))
  else
    CHECKS+=("$(run_check "UFW Active" "warn" "Could not determine UFW status")")
    WARN=$((WARN+1))
  fi

  local SSHPA=$(run_remote "$UH" "grep -i '^PasswordAuthentication' /etc/ssh/sshd_config 2>/dev/null | tail -1")
  if echo "$SSHPA" | grep -qi "no"; then
    CHECKS+=("$(run_check "SSH Password Auth" "pass" "Disabled")")
    PASS=$((PASS+1))
  else
    CHECKS+=("$(run_check "SSH Password Auth" "warn" "Password auth enabled")")
    WARN=$((WARN+1))
  fi

  local ROOT=$(run_remote "$UH" "grep -i '^PermitRootLogin' /etc/ssh/sshd_config 2>/dev/null | tail -1")
  if echo "$ROOT" | grep -qi "no\|prohibit"; then
    CHECKS+=("$(run_check "Root Login" "pass" "Disabled")")
    PASS=$((PASS+1))
  elif [ -z "$ROOT" ]; then
    CHECKS+=("$(run_check "Root Login" "warn" "Not explicitly set")")
    WARN=$((WARN+1))
  else
    CHECKS+=("$(run_check "Root Login" "fail" "Root login permitted")")
    FAIL=$((FAIL+1))
  fi

  local DISK=$(run_remote "$UH" "df / | awk 'NR==2{print \$5}' | tr -d '%'")
  if [ -n "$DISK" ] && [ "$DISK" -lt 85 ] 2>/dev/null; then
    CHECKS+=("$(run_check "Disk Usage" "pass" "${DISK}% used")")
    PASS=$((PASS+1))
  elif [ -n "$DISK" ] && [ "$DISK" -lt 95 ] 2>/dev/null; then
    CHECKS+=("$(run_check "Disk Usage" "warn" "${DISK}% used")")
    WARN=$((WARN+1))
  else
    CHECKS+=("$(run_check "Disk Usage" "fail" "${DISK:-?}% used")")
    FAIL=$((FAIL+1))
  fi

  local MEM=$(run_remote "$UH" "free | awk '/Mem:/{printf \"%.0f\", \$3/\$2*100}'")
  if [ -n "$MEM" ] && [ "$MEM" -lt 85 ] 2>/dev/null; then
    CHECKS+=("$(run_check "Memory Usage" "pass" "${MEM}% used")")
    PASS=$((PASS+1))
  elif [ -n "$MEM" ] && [ "$MEM" -lt 95 ] 2>/dev/null; then
    CHECKS+=("$(run_check "Memory Usage" "warn" "${MEM}% used")")
    WARN=$((WARN+1))
  else
    CHECKS+=("$(run_check "Memory Usage" "fail" "${MEM:-?}% used")")
    FAIL=$((FAIL+1))
  fi

  local AVAHI=$(run_remote "$UH" "systemctl is-active avahi-daemon 2>/dev/null")
  if [ "$AVAHI" = "active" ]; then
    CHECKS+=("$(run_check "Avahi/mDNS" "warn" "Running — should disable")")
    WARN=$((WARN+1))
  else
    CHECKS+=("$(run_check "Avahi/mDNS" "pass" "Not running")")
    PASS=$((PASS+1))
  fi

  local CUPS=$(run_remote "$UH" "systemctl is-active cups 2>/dev/null")
  if [ "$CUPS" = "active" ]; then
    CHECKS+=("$(run_check "CUPS" "warn" "Running — should disable")")
    WARN=$((WARN+1))
  else
    CHECKS+=("$(run_check "CUPS" "pass" "Not running")")
    PASS=$((PASS+1))
  fi

  local PORTS=$(run_remote "$UH" "ss -tlnp 2>/dev/null | tail -n+2 | wc -l")
  if [ -n "$PORTS" ] && [ "$PORTS" -lt 15 ] 2>/dev/null; then
    CHECKS+=("$(run_check "Open Ports" "pass" "$PORTS listening")")
    PASS=$((PASS+1))
  else
    CHECKS+=("$(run_check "Open Ports" "warn" "${PORTS:-?} listening")")
    WARN=$((WARN+1))
  fi

  local UNATT=$(run_remote "$UH" "dpkg -l 2>/dev/null | grep -c unattended-upgrades")
  if [ "$UNATT" -gt 0 ] 2>/dev/null; then
    CHECKS+=("$(run_check "Auto Updates" "pass" "unattended-upgrades installed")")
    PASS=$((PASS+1))
  else
    CHECKS+=("$(run_check "Auto Updates" "warn" "unattended-upgrades not found")")
    WARN=$((WARN+1))
  fi

  local TOTAL=$((PASS+WARN+FAIL))
  local SCORE=0
  if [ "$TOTAL" -gt 0 ]; then
    SCORE=$(( (PASS * 10 + WARN * 5) * 100 / (TOTAL * 10) ))
  fi

  local CHECKS_JSON=$(IFS=,; echo "${CHECKS[*]}")
  echo "{\"score\":$SCORE,\"reachable\":true,\"checks\":[$CHECKS_JSON]}"
}

echo "Starting security scan at $TIMESTAMP"

TOTAL_PASS=0 TOTAL_WARN=0 TOTAL_FAIL=0 TOTAL_CHECKS=0
SERVER_JSON=""

for entry in "${SERVERS[@]}"; do
  SID=$(echo "$entry" | cut -d: -f1)
  IP=$(echo "$entry" | cut -d: -f2)
  USER=$(echo "$entry" | cut -d: -f3)
  echo "  Scanning $SID ($IP)..."
  RESULT=$(scan_server "$SID" "$IP" "$USER")
  echo "$RESULT" > "$TMPDIR/$SID.json"
  [ -n "$SERVER_JSON" ] && SERVER_JSON="$SERVER_JSON,"
  SERVER_JSON="$SERVER_JSON\"$SID\":$RESULT"
done

END=$(date +%s)
DURATION=$((END-START))

for f in "$TMPDIR"/*.json; do
  P=$(cat "$f" | python3 -c "import json,sys;d=json.load(sys.stdin);print(sum(1 for c in d.get('checks',[]) if c['status']=='pass'))" 2>/dev/null || echo 0)
  W=$(cat "$f" | python3 -c "import json,sys;d=json.load(sys.stdin);print(sum(1 for c in d.get('checks',[]) if c['status']=='warn'))" 2>/dev/null || echo 0)
  F=$(cat "$f" | python3 -c "import json,sys;d=json.load(sys.stdin);print(sum(1 for c in d.get('checks',[]) if c['status']=='fail'))" 2>/dev/null || echo 0)
  TOTAL_PASS=$((TOTAL_PASS+P)); TOTAL_WARN=$((TOTAL_WARN+W)); TOTAL_FAIL=$((TOTAL_FAIL+F))
done
TOTAL_CHECKS=$((TOTAL_PASS+TOTAL_WARN+TOTAL_FAIL))
OVERALL=0
if [ "$TOTAL_CHECKS" -gt 0 ]; then
  OVERALL=$(( (TOTAL_PASS * 10 + TOTAL_WARN * 5) * 100 / (TOTAL_CHECKS * 10) ))
fi

cat > "$OUTFILE" << JSONEOF
{"last_scan":"$TIMESTAMP","next_scan":"$TOMORROW","scan_duration_s":$DURATION,"overall_score":$OVERALL,"servers":{$SERVER_JSON},"summary":{"total_checks":$TOTAL_CHECKS,"pass":$TOTAL_PASS,"warn":$TOTAL_WARN,"fail":$TOTAL_FAIL}}
JSONEOF

python3 -m json.tool "$OUTFILE" > /dev/null 2>&1 && echo "  ✅ Valid JSON written" || echo "  ⚠️ JSON may have issues"
echo "Scan complete: score=$OVERALL, checks=$TOTAL_CHECKS (${DURATION}s)"

rm -rf "$TMPDIR"
