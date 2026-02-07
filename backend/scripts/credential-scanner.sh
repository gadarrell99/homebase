#!/bin/bash
# Scans all servers for .env files, API keys, SSH configs, logins
# Runs every 60 min from Rize-Apps cron
cd "$(dirname "$0")/../.."
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
OUTFILE="data/credential-scan.json"
LOGFILE="logs/credential-scanner.log"

echo "[$TIMESTAMP] Credential scan starting" >> "$LOGFILE"

# ACTIVE SERVER LIST (as of 2026-02-06): name|user@host|project_path
SERVERS=(
    "talos|talosadmin@192.168.65.237|~"
    "agents|agents@192.168.65.241|~/.openclaw"
    "rize-apps|rizeadmin@192.168.65.245|~/homebase"
    "demos|demos@192.168.65.246|~"
    "vector|betadmin@192.168.65.249|~/bet"
)

SSH_OPTS="-o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no"

# Collect everything into temp files
SSH_CREDS="[]"
API_KEYS="[]"
WEB_LOGINS="[]"
ENV_FILES="[]"
SCAN_LOG="[]"

for entry in "${SERVERS[@]}"; do
    IFS='|' read -r SNAME SHOST SPATH <<< "$entry"
    echo "  Scanning $SNAME ($SHOST)..." >> "$LOGFILE"

    # Find all .env files
    ENVS=$(ssh $SSH_OPTS "$SHOST" "find $SPATH -maxdepth 3 -name '.env' -o -name '.env.*' -o -name '*.env' 2>/dev/null | head -20" 2>/dev/null)

    for ENVFILE in $ENVS; do
        [ -z "$ENVFILE" ] && continue

        # Read env file and extract key-value pairs
        CONTENTS=$(ssh $SSH_OPTS "$SHOST" "cat '$ENVFILE' 2>/dev/null" 2>/dev/null)
        [ -z "$CONTENTS" ] && continue

        # Parse each line for API keys, tokens, secrets, passwords
        while IFS= read -r line; do
            # Skip comments and empty lines
            [[ "$line" =~ ^#.*$ ]] && continue
            [[ -z "$line" ]] && continue
            [[ ! "$line" =~ = ]] && continue

            KEY=$(echo "$line" | cut -d= -f1 | tr -d ' "'"'"'')
            VAL=$(echo "$line" | cut -d= -f2- | tr -d ' "'"'"'' | head -c 200)

            # Skip empty values
            [ -z "$VAL" ] || [ "$VAL" = '""' ] || [ "$VAL" = "''" ] && continue

            # Classify
            KEY_UPPER=$(echo "$KEY" | tr '[:lower:]' '[:upper:]')
            case "$KEY_UPPER" in
                *API_KEY*|*APIKEY*|*SECRET*|*TOKEN*|*ANTHROPIC*|*OPENAI*|*GEMINI*|*FRESHSALES*)
                    # Mask middle of value
                    VLEN=${#VAL}
                    if [ "$VLEN" -gt 12 ]; then
                        MASKED="${VAL:0:6}...${VAL: -4}"
                    else
                        MASKED="${VAL:0:3}***"
                    fi
                    API_KEYS=$(echo "$API_KEYS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
d.append({'server':'$SNAME','file':'$ENVFILE','key_name':'$KEY','masked_value':'$MASKED','full_length':$VLEN,'scan_time':'$TIMESTAMP'})
print(json.dumps(d))")
                    ;;
                *PASSWORD*|*PASSWD*|*PWD*)
                    API_KEYS=$(echo "$API_KEYS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
d.append({'server':'$SNAME','file':'$ENVFILE','key_name':'$KEY','masked_value':'***password***','full_length':${#VAL},'scan_time':'$TIMESTAMP'})
print(json.dumps(d))")
                    ;;
            esac
        done <<< "$CONTENTS"

        ENV_FILES=$(echo "$ENV_FILES" | python3 -c "
import json,sys
d=json.load(sys.stdin)
d.append({'server':'$SNAME','path':'$ENVFILE'})
print(json.dumps(d))")
    done

    # Check for service account JSON files
    SA_FILES=$(ssh $SSH_OPTS "$SHOST" "find $SPATH -maxdepth 3 -name '*service-account*.json' -o -name '*credentials*.json' 2>/dev/null | head -5" 2>/dev/null)
    for SAF in $SA_FILES; do
        [ -z "$SAF" ] && continue
        SA_EMAIL=$(ssh $SSH_OPTS "$SHOST" "python3 -c \"import json;d=json.load(open('$SAF'));print(d.get('client_email',''))\" 2>/dev/null" 2>/dev/null)
        if [ -n "$SA_EMAIL" ]; then
            API_KEYS=$(echo "$API_KEYS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
d.append({'server':'$SNAME','file':'$SAF','key_name':'Google SA','masked_value':'$SA_EMAIL','full_length':0,'scan_time':'$TIMESTAMP'})
print(json.dumps(d))")
        fi
    done

    # SSH user info
    SSH_CREDS=$(echo "$SSH_CREDS" | python3 -c "
import json,sys
d=json.load(sys.stdin)
d.append({'server':'$SNAME','host':'$(echo $SHOST|cut -d@ -f2)','user':'$(echo $SHOST|cut -d@ -f1)'})
print(json.dumps(d))")
done

# Build final report
python3 << PYEOF
import json
from datetime import datetime

report = {
    "scan_time": "$TIMESTAMP",
    "ssh": $SSH_CREDS,
    "api_keys": $API_KEYS,
    "env_files": $ENV_FILES,
    "web_logins": [
        {"service":"BPS AI","url":"https://bpsai.rize.bm","username":"rizeadmin@bps.bm","note":"Demo account"},
        {"service":"Best Shipping","url":"https://bestshipping.rize.bm","username":"cornell@bestshipping.bm","note":"demo2026"},
        {"service":"Best Shipping Admin","url":"https://bestshipping.rize.bm","username":"admin@bestshipping.bm","note":"admin2026"},
    ],
    "summary": {
        "servers_scanned": len($SSH_CREDS),
        "env_files_found": len($ENV_FILES),
        "api_keys_found": len($API_KEYS),
        "scan_duration_note": "auto-scan every 60 min"
    }
}

with open("$OUTFILE", "w") as f:
    json.dump(report, f, indent=2)
print(f"  Scan complete: {len($SSH_CREDS)} servers, {len($ENV_FILES)} env files, {len($API_KEYS)} keys")
PYEOF

echo "[$TIMESTAMP] Scan complete" >> "$LOGFILE"
