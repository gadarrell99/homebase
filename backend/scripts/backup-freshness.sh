#!/bin/bash
cd "$(dirname "$0")/../.."
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
declare -A P
P[helios]="heliosdev@192.168.65.240:~/helios-ai"
P[agents]="agents@192.168.65.241:~/.openclaw"
P[homebase]="rizeadmin@192.168.65.245:~/homebase"
P[bps-ai]="demos@192.168.65.246:~/bps-ai"
P[nexus]="nexusadmin@192.168.65.247:~/nexus"
P[relay]="relayadmin@192.168.65.248:~/relay"
P[vector]="betadmin@192.168.65.249:~/bet"
P[dockyard]="dockyardadmin@192.168.65.252:~/dockyard-wifi-portal"
P[premier-emr]="emradmin@192.168.65.239:~/premier-emr"
R="{\"timestamp\":\"$TS\",\"projects\":{"
F=true
for PID in "${!P[@]}"; do
    E="${P[$PID]}"; H=$(echo "$E"|cut -d: -f1); D=$(echo "$E"|cut -d: -f2)
    LC=$(ssh -o ConnectTimeout=3 -o BatchMode=yes "$H" "cd $D && git log -1 --format='%ci' 2>/dev/null" 2>/dev/null)
    LT=$(ssh -o ConnectTimeout=3 -o BatchMode=yes "$H" "cd $D && git describe --tags --abbrev=0 2>/dev/null" 2>/dev/null)
    DR=$(ssh -o ConnectTimeout=3 -o BatchMode=yes "$H" "cd $D && git status --porcelain 2>/dev/null | wc -l" 2>/dev/null || echo "0")
    [ "$F" = true ] && F=false || R="$R,"
    R="$R\"$PID\":{\"last_commit\":\"${LC:-null}\",\"last_tag\":\"${LT:-null}\",\"dirty_files\":$DR}"
done
R="$R}}"
echo "$R" | python3 -m json.tool > data/backup-freshness.json 2>/dev/null || echo "$R" > data/backup-freshness.json
