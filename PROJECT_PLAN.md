# Homebase — Project Plan
**Version:** v1.3.0
**Status:** ✅ Production
**Updated:** 2026-02-07

## Vision
Central command dashboard for Rize Technology Group infrastructure.
Monitors 5 active servers, 15 projects, and 8 AI agents with real-time health,
security scanning, credential management, and alerting.

## Architecture
- **Backend:** Python FastAPI on Rize-Apps (.245:8000)
- **Frontend:** Static HTML/CSS/JS (no React SPA)
- **Database:** SQLite (agents.db, uptime.db)
- **Data:** infrastructure.json (single source of truth)
- **Process:** PM2 managed
- **URL:** https://homebase.rize.bm

## Navigation (9 items)
| Item | Route | Page |
|------|-------|------|
| Dashboard | / | index.html — Server health overview |
| Fleet | /fleet | fleet.html — Servers + projects combined |
| Agents | /agents | agents.html — AI agent status + guardrails |
| Sentinel | /sentinel | sentinel.html — Security oversight + alerts |
| Research | /research | research.html — Research Scout findings |
| Infra Sheet | /infra | infra.html — Full infrastructure reference |
| Settings | /settings | settings.html — Configuration |
| Backups | /backups | backups.html — Backup status |

## Additional Pages (linked from nav pages)
| Route | Page | Linked From |
|-------|------|-------------|
| /fleet/{id} | project-detail.html | Fleet |
| /servers/{id} | server-detail.html | Fleet |
| /agent/apex | agent-apex.html | Agents |
| /agent/aegis | agent-aegis.html | Agents |
| /agent/david-bishop | agent-david-bishop.html | Agents |
| /static/mindmap.html | mindmap.html | Agents |

## Key Components
- **Sentinel:** Agent oversight, guardrail enforcement, security scanning
- **Research Scout:** Filters actionable tools/tutorials from noise
- **Fleet Scanner:** 5-minute cron updating live metrics
- **Agent Heartbeat:** 5-minute interval health checks from all agents

## Roadmap
### v1.3.0 (Current)
- [x] Nav reorganization: 22 pages → 8 core, 9 nav items
- [x] Fleet page (merged Servers + Projects)
- [x] Infra Sheet (merged Infrastructure + Credentials + Cheat Sheet)
- [x] Agent details with capabilities and guardrails
- [x] Two-column agent layout
- [x] Pre-caching on all pages

### v1.4.0 (Planned)
- [ ] Project detail pages show README/TODO/docs
- [ ] Sentinel as critical security dashboard
- [ ] Agent document viewer
- [ ] Mind map with servers
- [ ] Live metrics on fleet cards
