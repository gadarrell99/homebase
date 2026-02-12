# HOMEBASE REQUIREMENTS — SINGLE SOURCE OF TRUTH
# Last Updated: 2026-02-10
# Server: rizeadmin@192.168.65.245, Port: 8000
# URL: homebase.rize.bm

---

## P0 — NAVIGATION BAR (BROKEN)

REQ-H001 | OPEN | NAV: Consistent size across ALL 16 pages
  - Nav bar shrinks on Agents page, grows on Metrics
  - Must be identical HTML/CSS on every page
  - Pages: index, servers, projects, agents, metrics, sentinel,
    security, settings, research, backups, credentials,
    server-detail, project-detail, agent-detail

REQ-H002 | OPEN | NAV: Research link appears/disappears
  - Research shows on some pages, missing on others
  - Research page has completely different nav bar
  - Fix: sync nav across all pages

REQ-H003 | OPEN | NAV: Settings and Backups outside gear icon
  - Should be inside gear dropdown OR directly on nav
  - Pick one approach and apply consistently

---

## P0 — BROKEN FEATURES

REQ-H004 | OPEN | PROJECTS: Detail button loads empty page
  - Click detail on any project → page loads but no content
  - Tested multiple projects, all empty
  - Debug project-detail.html and its API calls

REQ-H005 | OPEN | METRICS: /api/metrics/summary returns 500
  - Metrics page broken because API errors
  - Fix backend endpoint
  - Everything on metrics should hyperlink to server SSH

REQ-H006 | OPEN | RESEARCH: Blank on first load
  - Research Scout shows nothing until manual refresh
  - Run Scan button does not work
  - Pre-cache data, show immediately

---

## P1 — DATA CACHING

REQ-H007 | OPEN | UX: All pages show pre-cached data on click
  - Never make user wait for initial load
  - Show cached data immediately, refresh in background
  - Loading skeleton while refreshing, not blank

---

## P1 — SENTINEL

REQ-H008 | OPEN | SENTINEL: Show heartbeat status in dashboard
  - Should show "Active - Oversight Mode" for live agents
  - Show last heartbeat timestamp per agent

REQ-H009 | OPEN | SENTINEL: Agent-specific security info
  - Protocol violations, guardrail breaches, flagged requests
  - Per-agent detail under /sentinel

---

## P1 — FLEET & AGENTS

REQ-H010 | OPEN | FLEET: Talos shows version and uptime
  - Currently not working for Talos entry
  - Fix data source

REQ-H011 | OPEN | FLEET: Deduplicate Talos entries
  - Shows "Talos C2 Dashboard" AND "Talos" separately
  - Should be one entry or clearly differentiated

REQ-H012 | OPEN | AGENTS: Add document viewer button
  - Click to view README, CLAUDE.md, SPEC.md etc.
  - In-page viewer, not just a link

REQ-H013 | OPEN | AGENTS: More in-depth agent information
  - Current display is surface-level
  - Add: mode, integrations, last action, error count

REQ-H014 | OPEN | MINDMAP: Add demo server and all servers
  - Demo server (.246) missing from mind map
  - Show servers on mind map too, not just agents
  - Mind map has old nav bar — sync it

---

## P1 — CREDENTIALS

REQ-H015 | OPEN | CREDENTIALS: Move to Infrastructure page
  - Currently under Security — should be under Infrastructure
  - Must include ALL creds: SSH (5 servers), demo logins (4 projects),
    API keys/tokens, service passwords
  - Hidden by default with reveal buttons

---

## CHANGE LOG
| Date | REQ | Change | By |
|------|-----|--------|----|
| 2026-02-10 | ALL | Initial from CEO feedback sessions | Claude |
