#!/bin/bash
echo "=== BACKUP AUDIT $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo ""
echo "GIT STATUS PER REPO:"
for repo_dir in /home/rizeadmin/nexus /home/rizeadmin/homebase /home/rizeadmin/finance-dashboard /home/rizeadmin/sales-dashboard /home/rizeadmin/dockyard-wifi-portal; do
    REPO=$(basename $repo_dir)
    if [ -d "$repo_dir/.git" ]; then
        cd "$repo_dir"
        AHEAD=$(git rev-list --count @{upstream}..HEAD 2>/dev/null || echo "no-upstream")
        DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
        LAST=$(git log -1 --format='%ci' 2>/dev/null | cut -d' ' -f1)
        echo "  $REPO: $AHEAD ahead, $DIRTY dirty, last: $LAST"
    else
        echo "  $REPO: not a git repo"
    fi
done

echo ""
echo "LIFEBOAT BACKUP (Talos):"
ssh -o ConnectTimeout=3 talosadmin@192.168.65.237 "ls -lt ~/backups/lifeboat/ 2>/dev/null | head -5" 2>/dev/null || echo "  Cannot reach Talos"

echo ""
echo "DISK USAGE:"
df -h / | tail -1 | awk '{print "  .245: " $5 " used (" $4 " free)"}'
