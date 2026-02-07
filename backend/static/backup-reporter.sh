#!/bin/bash
HOMEBASE="http://192.168.65.243:8000"
BACKUP_DIR=~/backups/$(date +%Y-%m-%d)
echo "Reporting backups to Homebase..."
for file in $BACKUP_DIR/*.tar.gz; do
    [ -f "$file" ] || continue
    NAME=$(basename "$file" | sed 's/-backup-.*//;s/-/_/g')
    SIZE_MB=$(du -m "$file" | cut -f1)
    case "$NAME" in agents) S="agents";;relay) S="relay";;homebase) S="homebase";;demos) S="demos";;nexus) S="nexus";;vector) S="vector";;dockyard) S="dockyard";;claudedev) S="claude-dev";;*) S="$NAME";;esac
    curl -s -X POST "$HOMEBASE/api/backups/$S/report" -H "Content-Type: application/json" -d "{\"status\":\"success\",\"size_mb\":$SIZE_MB,\"files\":[\"$file\"]}" >/dev/null
    echo "  ✅ $S: ${SIZE_MB}MB"
done
