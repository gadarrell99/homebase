# Homebase Changelog

## v1.4.0 (2026-02-09)
- **PROJECT DOCS VIEWER**: View project README/TODO/CHANGELOG from Homebase
- NEW: GET /api/projects/{id}/docs endpoint for direct docs access
- NEW: SSH-based doc fetching for remote projects (demos, vector, agents servers)
- Fixed project_path in infrastructure.json for best-shipping and bet-air-ambulance
- Project detail page now shows docs with tabs (README, TODO, Changelog, Project Plan, Claude.md)

## v1.3.0 (2026-02-07)
- **NAV OVERHAUL**: Reorganized navigation: 22 pages -> 8 core pages, 7 nav items
- NEW: Fleet page (merged Servers + Projects + Project Status)
- NEW: Infra Sheet (merged Infrastructure + Credentials + Cheat Sheet)
- Enhanced Sentinel with Security, Metrics, and Audit Trail tabs
- Added nav bar to all agent dashboard pages (apex, aegis, david-bishop)
- Deleted stale cheat-sheet-full.json
- Added redirects for old URLs (/servers -> /fleet, /cheat-sheet -> /infra)
- Fixed agent names in templates (Treasurer->Apex, Watchman->Aegis)
- Fixed David Bishop port in infrastructure.json (9001->7070)

## v1.2.0 (2026-02-06)
- Added Settings, Research, Sentinel, Credentials pages
- Research Scout with complaint filtering
- infrastructure.json as single source of truth
- Agent heartbeat system (5-minute intervals)
- Pipeline monitor for Cortex/Sentinel oversight
- Agent dashboard pages for Apex, Aegis, David Bishop
- Azure Teams bot integration

## v1.1.0 (2026-02-05)
- Initial deployment with Dashboard, Servers, Projects, Agents
- infra-scanner.py cron job
- Basic alert system

## v1.0.0 (2026-02-04)
- First deployment of Homebase
