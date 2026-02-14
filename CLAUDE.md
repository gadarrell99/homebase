# READ ~/homebase/WORKFLOW-SPEC.md FIRST — System-wide 6-phase workflow rules
# Then read this file for Homebase-specific instructions.
---

# CLAUDE.md — HOMEBASE
# GITEA-DRIVEN WORKFLOW — READ THIS FIRST

## MANDATORY FIRST STEP
Fetch open issues from Gitea:

```bash
GITEA_TOKEN=$(cat ~/.gitea-token 2>/dev/null || echo "TOKEN_NOT_SET")
curl -s "http://localhost:3100/api/v1/repos/rize/homebase/issues?state=open&labels=P0&limit=50" \
  -H "Authorization: token $GITEA_TOKEN" | python3 -c "
import sys, json
issues = json.load(sys.stdin)
print(f'Open P0 issues: {len(issues)}')
for i in issues:
    labels = ','.join(l['name'] for l in i.get('labels',[]))
    print(f\"  #{i['number']}: {i['title']} [{labels}]\")
"
```

Also read HOMEBASE-REQUIREMENTS.md as secondary reference.

## WORKFLOW
1. Fetch open P0 issues from Gitea
2. Work through them in order
3. For each fix:
   a. Run Playwright test: USE_LOCAL=1 HB_URL=http://localhost:8000 npx playwright test homebase-tests.spec.js -g "REQ-HXXX"
   b. Commit: "Fixes rize/homebase#N"
   c. Push to Gitea
   d. Update HOMEBASE-REQUIREMENTS.md
4. Session DONE = zero open P0 issues

## CRITICAL: NAV BAR
Must be IDENTICAL HTML across all pages. Use shared component/include.

## RULES
- Talos (.237) NEVER rebooted during sessions
- Do NOT skip P0 for P1
- Email artiedarrell@gmail.com when done

## GIT: DUAL PUSH (GitHub + Gitea)
Every commit must be pushed to BOTH remotes:

Never push to only one remote. Both must stay in sync.


## Auto-Sync (Cron — Every 15 Minutes)
Script: `backend/auto_sync.py`
Cron: `*/15 * * * * cd /home/rizeadmin/homebase && python3 backend/auto_sync.py >> logs/auto_sync.log 2>&1`

### What It Syncs:
1. **Fleet Status** — Pings all 5 servers (.237, .241, .245, .246, .249), checks port availability
2. **Agent Status** — SSH to .241, checks David/Cortex/Apex/Aegis/Sentinel process status
3. **Gitea Repos** — Queries local Gitea API for repo list and open issue counts

### Data Files:
- `data/fleet_status.json` — Server online/offline + port status per server
- `data/agent_status.json` — Agent active/inactive status from .241
- `data/gitea_repos.json` — Repo list with open issue counts
- `data/sync_status.json` — Last sync timestamp and summary counts

### Notes:
- Runs as rizeadmin user on .245
- SSH timeout: 5 seconds per agent check
- Curl timeout: 3 seconds per port check
- Log: `logs/auto_sync.log`


## MANDATORY: Every session must end with verify-fix-retest cycle. See ~/AUDIT-TEMPLATE.md on Talos. Trust no self-reports. curl every endpoint, run Playwright, test logins. Fix broken, retest, then report.
