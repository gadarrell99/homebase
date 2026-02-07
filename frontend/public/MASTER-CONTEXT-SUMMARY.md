# MASTER CONTEXT SUMMARY — Rize Technologies Infrastructure
**Generated:** 2026-02-05 17:00 UTC
**Source Files:** ALL-MARKDOWNS-CONCATENATED.md, ALL-TODOS-CONCATENATED.md, ALL-HOMEBASE-MDS.md
**Maintainer:** talosadmin@talos (192.168.65.237)

---

## Table of Contents
1. [Fleet Overview](#fleet-overview)
2. [Per-Project Sections](#per-project-sections)
3. [Global TODOs](#global-todos)
4. [Credentials Index](#credentials-index)
5. [Open Issues](#open-issues)

---

## Fleet Overview

| # | Server | IP | User | Project Path | Stack | Version | Status |
|---|--------|-----|------|-------------|-------|---------|--------|
| 1 | Talos | .237 | talosadmin | ~/context | Docker, Python | — | C2 Node |
| 2 | Premier-EMR | .239 | emradmin | ~/premier-emr | FastAPI+React, Docker | v0.2.1 | Chunk 01 live |
| 3 | Helios | .240 | heliosdev | ~/helios-ai | Python/FastAPI | — | cloudflared inactive |
| 4 | David | .241 | david | ~/.openclaw | Node.js | v2026.2.4 | 65 dirty files |
| 5 | .245-Rize | .245 | rizeadmin | ~/homebase | Python/FastAPI, PM2 | v1.0.0 | 315 restarts |
| 6 | Claude-Dev | .245 | claudedevadmin | ~ | Docker (OpenHands) | — | Idle |
| 7 | BPS-AI | .246 | bpsaiadmin | ~/bps-ai | Next.js 14, PM2 | v0.9.26 | Demo overdue |
| 8 | Nexus | .247 | nexusadmin | /opt/it-context-hub | Node 20, Docker | v2.0.0 | POC 90% |
| 9 | Relay | .248 | relayadmin | ~/relay | Python/FastAPI, PG | v3.3.0 | Production |
| 10 | Vector | .249 | betadmin | ~/bet | Node/Express, Docker | — | AIR AMBULANCE |
| 11 | Dockyard | .252 | dockyardadmin | ~/dockyard* | Node/Express, Docker | v1.8.0 | 502 errors |
| 12 | Hyper-V | .253 | Administrator | — | Windows/PowerShell | — | Online |

*Dockyard project path in chunk3 listed as ~/dockyard-wifi-portal but containers run from different path.

---

## Per-Project Sections

---

### 1. TALOS — C2 Command Node (.237)

**Purpose:** Central control node for fleet management. SSH access to all 10 Linux servers + Hyper-V.
**Stack:** Ubuntu 24.04, Docker v29.2.1, Python 3.x
**RAM:** 7.4G total / 5.8G available | **Disk:** 80G free

**What's here:**
- `~/context/` — 2,583 ingested files (project docs from all servers)
- `~/scripts/` — Fleet verification scripts (chunk1, chunk2, chunk3, gather_fleet_intel, ingest_intel, etc.)
- `~/infrastructure/` — Infrastructure configs
- `~/.ssh/id_ed25519` — Fleet SSH key (passwordless to all nodes)
- Docker installed but no containers running
- cloudflared installed (from .deb)

**Missing/Needed:**
- Ollama not installed (spec calls for DeepSeek/Qwen models)
- UFW inactive (firewall not enabled)
- No crontab configured
- 4 pending updates (kernel 6.8.0-100, docker-model-plugin)

---

### 2. HOMEBASE — Infrastructure Dashboard (.245)

**Purpose:** Central monitoring dashboard for all Rize servers. Real-time health, security scanning, credential vault, agent monitoring, alerting.
**Version:** v1.0.0 (git tag)
**Stack:** Python FastAPI, 11 static HTML pages (no React SPA), SQLite, PM2
**Domain:** homebase.rize.bm (Cloudflare tunnel, active)
**Port:** 8000
**RAM:** 1.6G total / 846M available | **Disk:** 82G free

**Pages (11):**
| Page | Route | Status |
|------|-------|--------|
| Dashboard | / | 200 OK |
| Servers | /servers | 200 OK |
| Projects | /projects | 200 OK |
| Agents | /agents | 200 OK |
| Metrics | /metrics | 200 OK |
| Security | /security | 200 OK |
| Audit Tracker | /audit-tracker | 200 OK |
| Backups | /backups | 200 OK |
| Credentials | /credentials | 200 OK |
| Settings | /settings | 200 OK |
| Cheat Sheet | /cheat-sheet | 200 OK |

**API Routes:** 87 registered in main.py. Key route groups:
- `/api/servers` — Server metrics via SSH
- `/api/security/scan` — Nightly security scanner results
- `/api/credentials` — Fernet-encrypted credential vault (2FA required)
- `/api/metrics/summary`, `/api/metrics/history` — Historical metrics
- `/api/agents`, `/api/agents/{id}` — AI agent monitoring
- `/api/alerts` — Alert management
- `/api/audit-fixes` — Audit fix tracking
- `/api/vault/status` — Vault health
- `/api/settings` — Settings CRUD
- `/api/discovery/scan` — Subnet discovery
- `/api/pulse/*` — Pulse monitoring subsystem
- `/api/redteam/*` — Red team reporting
- `/api/reports/david` — David Bishop agent reports
- `/api/auth/*` — TOTP 2FA authentication (10 endpoints)
- `/api/projects/*` — Project doc aggregation
- `/api/logs/*` — Log collection

**Backend Services (22 Python files, all compile clean):**
agent_monitor.py, alert_checker.py, alerts.py, auth.py, cheat_sheet.py, database.py, discovery.py, email_alerts.py, keyManager.py, logCollector.py, metrics_history.py, navbar.py, projectSyncService.py, pulse_monitor.py, redteam.py, security.py, server_enrichment.py, settings.py, totp_service.py, uptime.py

**Databases:**
- `data/agents.db` — Agent monitoring (SQLite)
- `data/uptime.db` — Uptime history (SQLite, 491K)
- `backend/homebase.db` — Auth, settings (SQLite)
- Settings stored in SQLite (alert thresholds, cooldowns)

**Data Files:**
- `data/servers.json` — Server definitions
- `data/projects.json` — Project metadata
- `data/credentials.json` — Encrypted credentials (Fernet)
- `data/.credentials.key` — Credential encryption key
- `data/.totp-secret` — TOTP secret for 2FA
- `data/security-scans.json` — Security scan results
- `data/alerts.json` — Alert history (98K)
- `data/cheat-sheet-full.json` — Cheat sheet data
- `data/backup-report.json`, `data/backup-freshness.json` — Backup status
- `data/credential-scan.json` — Credential scan results
- `data/audit-fixes.json` — Audit fix tracking
- `data/overlord-report.json` — Agent Overlord reports
- `data/discovery-queue.json` — Discovery queue

**Cron Jobs (11 active on rizeadmin):**
```
*/5 * * * *  curl /api/metrics/record                    # Metrics every 5 min
0 0 * * *    curl -X DELETE /api/metrics/cleanup?days=30 # Daily cleanup
0 6 * * *    ~/property-rize/scripts/daily_scrape.sh     # Property scraper
0 * * * *    curl -X POST /api/projects/sync             # Hourly project sync
0 */6 * * *  ~/scripts/health-check.sh                   # Health check 6h
0 3 * * *    backend/scripts/nightly-scan.sh             # Nightly security scan
*/5 * * * *  backend/scripts/uptime-monitor.sh           # Uptime monitor 5min
*/5 * * * *  python3 alert_checker.check_all             # Alert check 5min
0 4 * * 0    backend/scripts/discovery-scan.sh           # Weekly discovery
0 * * * *    backend/scripts/credential-scanner.sh       # Hourly cred scan
30 * * * *   backend/scripts/generate-cheat-sheet.sh     # Cheat sheet refresh
```

**PM2 Processes:**
- `homebase` — online, 315 restarts, 73MB
- `property-rize` — online, 1 restart, 51MB

**Architecture:**
```
Internet → Cloudflare Tunnel → .245-Rize:8000 → FastAPI
                                              │ asyncssh
                                              ▼
                                    10 monitored servers (SSH port 22)
```

**Completed Phases:** 1-9 (Core dashboard, security, credentials, metrics, projects, auth/2FA, alerts, discovery, agents)
**TODO Phases:** 6 (Slack/Discord alerts), 7 (GitHub + one-click deploy), 8 (RBAC, mobile, cost tracking)

---

### 3. DOCKYARD WiFi Portal (.252)

**Purpose:** Captive WiFi portal for Royal Naval Dockyard in Bermuda
**Version:** v1.8.0 (sprint from v1.4.6)
**Stack:** Node.js/Express, Docker (4 containers: admin, backend, postgres, redis)
**Domain:** dockyardwifi.rize.bm, dockyard-admin.rize.bm
**DEADLINE:** February 28, 2026
**BLOCKED:** Payment integration — waiting on Martin
**RAM:** 2.8G total / 2.0G available | **Disk:** 71G free

**Features (implemented):**
- WiFi captive portal splash page
- Google OAuth login (grants 1hr free WiFi)
- Facebook OAuth login
- Voucher/coupon system (free_hour, free_day, multi-use)
- Video rotation + sponsor ads
- Admin dashboard (analytics, settings, pricing controls)
- Sponsor image upload (JPG/PNG/GIF/WebP, max 5MB)
- CSV voucher export
- Mobile responsive (min 44px tap targets)

**Known Issues:**
- Admin 502s on /ads, /videos, /sponsors, /settings pages (P0 BROKEN)
- These regressions caused by v1.4.6→v1.8.0 sprint

**Changelog highlights:**
- v1.8.0: Admin panel 502 regressions
- v1.7.0: Mobile responsive improvements
- v1.4.3: Admin pricing controls
- v1.4.2: Sponsor image upload
- v1.4.0: Google + Facebook OAuth
- v1.3.2: Voucher time addition fix
- v1.2.0: Voucher/coupon system

---

### 4. BPS AI — Police Case Management (.246)

**Purpose:** AI-powered case management and reporting for Bermuda Police Services
**Version:** v0.9.26
**Stack:** Next.js 14, React, TypeScript, Tailwind CSS, PostgreSQL 16 + pgvector, Prisma, NextAuth.js, PM2
**Client:** Alexander Rollin (arollin@bps.bm)
**Domain:** bpsai.rize.bm
**Port:** 3000
**RAM:** 7.8G total / 5.9G available | **Disk:** 21G free (55% used — watch!)
**UFW:** INACTIVE

**Data:**
- 16 users, 65 cases, 136 evidence, 10 IA investigations, 31 IA documents

**Core Features:**
1. Case management (3 types: Domestic Abuse, Gang/Drug, Traffic)
2. Multi-model AI report generation (Claude, GPT-4, Gemini, Llama 3 8B, Mistral 7B via Ollama)
3. Internal Affairs module (separate auth + database, purple theme)
4. Legal & News Research (RAG) — 98 scraped Bermuda laws, 10yr news archive
5. Evidence file upload with chain of custody + immutability
6. Voice dictation for case input
7. AI Auto-Fill from notes (POST /api/ai/extract-from-notes)
8. Email notifications (SMTP Office365)
9. PDF report export (PDFKit)
10. Audit logging (hospital-grade, append-only)
11. Column customization with localStorage persistence

**Key API Endpoints:**
- `/api/health` — Health check
- `/api/cases` — CRUD + filtering
- `/api/cases/:id/pdf` — PDF export
- `/api/evidence/upload` — File upload (10MB max)
- `/api/files/evidence/[caseId]/[filename]` — File serving
- `/api/ai/extract-from-notes` — AI auto-fill
- `/api/ia/*` — Internal affairs routes

**Monitoring:** Relay/Pulse at .248 checks /api/health

---

### 5. RELAY — Autonomous Task Engine (.248)

**Purpose:** LLM-driven autonomous task execution engine with Commander/Worker/Reviewer pipeline
**Version:** v3.3.0
**Stack:** Python/FastAPI, PostgreSQL, WebSocket, SSH
**Domain:** relay.rize.bm
**Port:** 8000
**RAM:** 3.8G total / 2.9G available | **Disk:** 16G free (43% used — watch!)

**Architecture:** Commander → Worker → Reviewer pipeline
- Commander: Plans tasks, generates structured JSON
- Worker: Executes code on remote servers via SSH
- Reviewer: Validates output, approves/rejects

**Features (v3.3.0):**
- Full LLM Commander/Worker/Reviewer pipeline
- Batch TODO multi-step tasks
- Email notifications on completion/failure (SMTP aidev@rize.bm)
- Dark theme Mission Control dashboard
- Cost tracking per task
- Task templates (8 defaults + custom)
- WebSocket real-time updates
- Projects API with 8 servers seeded
- Phase 10 complete: Autonomous execution loop (context loading, structured outputs, self-fix loop, milestones)

**SSH Routes to:** .245-Rize, Relay, BPS-AI, Nexus, Dockyard, Vector, Claude-Dev (8 servers)

**Monitored Projects:**
Relay (.248), BPS AI (.246), Nexus (.247), Vector (.249), Dockyard (.252)

---

### 6. NEXUS / IT Context Hub (.247)

**Purpose:** MSP client context aggregation platform — unifies Halo PSA, Microsoft 365, and AI
**Version:** v2.0.0 (Context Hub v1.5.1)
**Stack:** Node.js 20, Express, TypeScript, PostgreSQL 15, Redis 7, Elasticsearch 8.11, React 18, Prisma
**Domain:** context.rize.bm
**Port:** 3001
**Project Path:** /opt/it-context-hub/
**Service:** systemd (context-hub.service)
**RAM:** 3.9G total / 1.1G available | **Disk:** 49G free

**109 endpoints.** Key routes:
- `/health` — Health check
- `/api/companies` — Company list
- `/api/sync/clients|users|tickets|actions|assets` — Halo PSA sync
- `/api/sync/emails|sharepoint|teams` — Microsoft Graph sync
- `/api/sync/index` — Elasticsearch reindex
- `/api/ai/query` — Multi-provider AI queries

**Data Sources:**
- Halo PSA: Clients, users, ~30k tickets, actions, assets (OAuth client credentials)
- Microsoft Graph: Emails, SharePoint (Technical + Sales sites only), Teams
- AI: OpenAI, Anthropic, Gemini (provider switching via settings)

**Security Features:**
- PII detection (SSN, credit cards, bank accounts, DOB, passport)
- Content filtering (salary, termination, HR, medical)
- SharePoint restricted to whitelisted sites
- Management DM filtering
- Email approval workflow for flagged content
- Audit logging

**Cron:** Automated sync every 4 hours

**POC Status:** ~90% complete. Missing: Cloudflare Access auth, ~10-15 companies need email matching verification

**Known Issues:**
- Actions sync slow (iterates all 30k tickets)
- SharePoint recursive sync not fully tested
- Email matching accuracy varies
- Backend uses 1.6GB memory
- Frontend not served via Node (needs nginx proxy)

---

### 7. DAVID / OpenClaw (.241)

**Purpose:** Scope-restricted AI agent with email polling and 3-tier security architecture
**Version:** v2026.2.4
**Stack:** Node.js
**Project Path:** ~/.openclaw
**Domain:** via cloudflared (active)
**RAM:** 7.8G total / 6.3G available | **Disk:** 147G free

**Last commit:** `1a9e08b v2026.2.4: Security architecture overhaul, monitoring, email inbound`

**Issues:**
- 65 dirty git files (needs commit/cleanup)
- No README.md, TODO.md, or CHANGELOG.md
- openclaw-gateway systemd service: inactive

**Integration with Homebase:**
- Heartbeat cron sends reports to Homebase `/api/reports/david`
- David Bishop agent detail page at `/agents/david-bishop`

---

### 8. PREMIER-EMR (.239)

**Purpose:** Electronic Medical Records system
**Version:** v0.2.1
**Stack:** FastAPI + React, Docker (3 containers: backend, frontend, db/healthy)
**Services:** nginx (active), cloudflared (active)
**RAM:** 3.8G total / 2.9G available | **Disk:** 33G free

**Status:** Chunk 01 deployed, 14 chunks remaining
**Remaining chunks (02-15):** RBAC, settings, clinical features, patient management, scheduling, billing, reporting, etc.

---

### 9. VECTOR — Air Ambulance (.249)

**Purpose:** AIR AMBULANCE system — DO NOT TOUCH without explicit reason
**Stack:** Node.js/Express, Docker (2 containers: vector-db/healthy, vector-redis)
**Domain:** cloudflared (active)
**RAM:** 3.3G total / 2.3G available | **Disk:** 82G free

---

### 10. HELIOS (.240)

**Purpose:** helios-ai project (details sparse)
**Stack:** Python/FastAPI
**Services:** nginx (active), cloudflared (INACTIVE — needs investigation)
**RAM:** 1.8G total / 1.2G available | **Disk:** 76G free

---

### 11. CLAUDE-DEV (.245)

**Purpose:** Claude Code host / OpenHands agent server
**Stack:** Docker (oh-agent-server, openhands containers)
**Services:** cloudflared (active)
**RAM:** 15.6G total / 13.8G available | **Disk:** 42G free
**Note:** Most powerful server by RAM. Runs autonomous coding agents.

---

### 12. PROPERTY-RIZE (on .245-Rize .245)

**Purpose:** Real estate property scraper for Bermuda listings
**Stack:** Python, PM2
**Cron:** Daily scrape at 6 AM (`~/property-rize/scripts/daily_scrape.sh`)
**Features:** Sales + rental scraping, price alerts
**Version:** ~v0.4.4

---

## Global TODOs

### P0 — Critical / Broken

| Item | Server | Notes |
|------|--------|-------|
| Dockyard admin 502s (ads/videos/sponsors/settings) | .252 | Regressions from v1.4.6→v1.8.0 sprint |
| Relay async SSH blocking | .248 | Sync SSH calls block event loop, deadlocks on self-targeting |
| Relay task timeout enforcement | .248 | No mechanism to kill stuck tasks |

### P1 — High Priority

| Item | Server | Notes |
|------|--------|-------|
| Homebase undefined errors (security, agents, alerts pages) | .245 | Frontend JS errors |
| Premier-EMR chunks 02-15 | .239 | RBAC, settings, features — 14 chunks remaining |
| Homebase credential scanner + cheat refresh crons | .245 | Verify crons are actually producing output |
| Relay milestone emails | .248 | Only sends final summary, not per-milestone |
| Relay SSH connection pooling | .248 | Reuse connections instead of new per task |
| Relay SSH key to Claude-Dev (.245) | .248 | Not yet established |
| Nexus Cloudflare Access auth | .247 | Security blocker for POC demo |
| BPS-AI mobile responsive | .246 | Audit needed |
| Install Ollama on Talos | .237 | DeepSeek/Qwen models for C2 node |

### P2 — Medium Priority

| Item | Server | Notes |
|------|--------|-------|
| David notification channel verification | .241 | Confirm heartbeats working |
| BPS AI demo (overdue) | .246 | Client: Alexander Rollin |
| Homebase Phase 6: Slack/Discord alerts | .245 | Webhook integration |
| Homebase Phase 7: GitHub integration | .245 | Recent commits, one-click deploy |
| Relay dashboard polish | .248 | Model persistence, terminal, export |
| Relay reviewer verification | .248 | File existence + syntax checks |
| Relay security (rate limiting, API keys, auth) | .248 | Currently no auth on dashboard |
| David: commit/cleanup 65 dirty files | .241 | Needs git housekeeping |
| David: add README/TODO/CHANGELOG | .241 | No project docs |
| Enable UFW on Talos (.237) and BPS-AI (.246) | .237/.246 | Firewalls inactive |
| Nexus actions sync optimization | .247 | Currently iterates all 30k tickets |
| VERSION files for Nexus, David, Helios | .247/.241/.240 | Missing |

### P3 — Future / Backlog

| Item | Server | Notes |
|------|--------|-------|
| Homebase Phase 8: RBAC, mobile, cost tracking, API key mgmt | .245 | v1.0.0 target |
| Relay Phase 11: Parallel workers (Redis queue) | .248 | Replace JSON file queue |
| Relay Phase 12: Claude Code integration | .248 | Dashboard visibility for claude -p runs |
| Relay Phase 13: SQLite → PostgreSQL migration | .248 | Scale for 10+ workers |
| Relay Phase 14: MemOS + MCP + Learning | .248 | Memory system, MCP protocol |
| BPS-AI: Government integrations | .246 | Court, TCD, Immigration, Hospital APIs |
| BPS-AI: Comprehensive test suite | .246 | No tests currently |
| Dockyard payment integration | .252 | Blocked on Martin |
| Tesla P40 GPU integration | .248? | ~Feb 2026 |
| Nexus mobile-responsive design | .247 | |
| Nexus Datto RMM, IT Glue, Slack integrations | .247 | Phase 6 |

---

## Credentials Index

**WARNING: Values redacted. This lists WHAT exists and WHERE.**

### Talos (.237)
| Credential | Location | Type |
|------------|----------|------|
| SSH Ed25519 key | ~/.ssh/id_ed25519 | SSH key |
| SSH RSA key | ~/.ssh/id_rsa | SSH key |
| authorized_keys | ~/.ssh/authorized_keys | SSH (0 entries) |

### Homebase (.245)
| Credential | Location | Type |
|------------|----------|------|
| Credential encryption key | data/.credentials.key | Fernet key |
| Encrypted credentials store | data/credentials.json | Encrypted JSON |
| TOTP 2FA secret | data/.totp-secret | TOTP secret |
| Homebase auth key | backend/.homebase_key | App key |
| SMTP config | In cron/alert_checker | smtp.office365.com:587 |
| Admin default password | Printed to console on first run | Random generated |
| Session tokens | In-memory / SQLite | JWT-style (64 bytes) |
| Device trust tokens | Cookies | 48 bytes urlsafe |
| Credential vault contents | data/credentials.json | SSH keys, API keys, passwords, tokens |

### Dockyard (.252)
| Credential | Location | Type |
|------------|----------|------|
| Google OAuth | .env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET | OAuth |
| Facebook OAuth | .env: FACEBOOK_APP_ID, FACEBOOK_APP_SECRET | OAuth |
| PostgreSQL creds | Docker env / .env | DB auth |
| Redis creds | Docker env | Cache auth |

### BPS-AI (.246)
| Credential | Location | Type |
|------------|----------|------|
| Demo user accounts | Seeded in PostgreSQL | 8 main + 4 IA accounts |
| SMTP (Office365) | .env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM | Email |
| Claude API key | .env or settings DB | AI provider |
| OpenAI API key | .env or settings DB | AI provider |
| Gemini API key | .env or settings DB | AI provider |
| NextAuth secret | .env: NEXTAUTH_SECRET | Auth |
| PostgreSQL (main + IA) | .env: DATABASE_URL | DB auth |

### Nexus / Context Hub (.247)
| Credential | Location | Type |
|------------|----------|------|
| Halo PSA OAuth | .env: HALO_BASE_URL + client credentials | API OAuth |
| Microsoft Graph | .env: MS_TENANT_ID + client credentials | API OAuth |
| OpenAI API key | settings DB: openai_api_key | AI provider |
| Anthropic API key | settings DB: anthropic_api_key | AI provider |
| Gemini API key | settings DB: gemini_api_key | AI provider |
| PostgreSQL | .env: DATABASE_URL (user: contexthub) | DB auth |
| Microsoft Client Secret | .env | OAuth |
| Freshsales API Key | .env | API key |

### Relay (.248)
| Credential | Location | Type |
|------------|----------|------|
| SMTP config | ~/relay/data/email_config.json | Email (aidev@rize.bm) |
| PostgreSQL | config | DB auth |
| SSH keys to 8 servers | ~/.ssh/ | SSH keys |

### General / Cross-Server
| Credential | Location | Type |
|------------|----------|------|
| Cloudflare tunnel creds | ~/.cloudflared/ on each server | Tunnel auth |
| Email notification target | artiedarrell@gmail.com | Hardcoded recipient |
| GitHub: gadarrell99 | Various repos | Git auth |
| GitHub: artieRizmo | homebase repo | Git auth |

---

## Open Issues

### Critical (P0)
1. **Dockyard admin 502s** (.252) — /ads, /videos, /sponsors, /settings return 502. Regressions from rapid v1.4.6→v1.8.0 sprint. Docker containers running but admin routes broken. Feb 28 deadline.
2. **Relay SSH blocking** (.248) — Synchronous SSH calls in async task runner block event loop. Causes deadlocks when tasks target Relay itself.

### High (P1)
3. **Homebase 315 PM2 restarts** (.245) — Stability issue. Process has restarted 315 times. Root cause unknown — could be memory (only 846MB available), unhandled exceptions, or import errors.
4. **Homebase undefined errors** (.245) — Security, agents, and alerts pages show "undefined" values in frontend. Likely missing/null data in API responses.
5. **Premier-EMR** (.239) — Only Chunk 01 deployed. 14 remaining chunks for RBAC, clinical features, patient management, etc.
6. **BPS-AI demo overdue** (.246) — Demo for Alexander Rollin (BPS) is past due. System is functional at v0.9.26 but UFW is off and disk at 55%.
7. **Nexus POC incomplete** (.247) — ~90% done. Missing Cloudflare Access auth (security requirement) and email matching verification for 10-15 companies.

### Medium (P2)
8. **David 65 dirty git files** (.241) — No README/TODO/CHANGELOG. openclaw-gateway service inactive.
9. **Helios cloudflared inactive** (.240) — External access broken.
10. **Talos missing Ollama** (.237) — C2 spec calls for local AI models (DeepSeek, Qwen).
11. **UFW inactive** on Talos (.237) and BPS-AI (.246) — No firewall protection.
12. **Disk pressure** — BPS-AI at 55%, Relay at 43%. Monitor closely.
13. **.245-Rize low RAM** (.245) — Only 846MB available with Homebase + Property-Rize running.

### Known Bugs (from docs)
14. **Homebase API route mismatches** — Frontend calls /api/metrics, /api/security/latest, /api/cheat-sheet, /api/uptime/latest, /api/discovery but actual routes are /api/metrics/summary, /api/security/scan, /api/discovery/scan. Missing: cheat-sheet API, uptime/latest API.
15. **Nexus actions sync slow** — Iterates all 30k Halo tickets; needs incremental sync.
16. **Nexus memory at 1.6GB** — Monitor for leaks.
17. **Relay auth failures before SSH success** — Cosmetic, low severity.
18. **BPS-AI demo accounts use demo passwords** — Listed in README (should be rotated for production).

---

## Key Domains

| Domain | Target | Service |
|--------|--------|---------|
| homebase.rize.bm | .245-Rize:8000 | Homebase dashboard |
| bpsai.rize.bm | BPS-AI:3000 | Police case management |
| relay.rize.bm | Relay:8000 | Task automation |
| context.rize.bm | Nexus:3001 | IT Context Hub |
| dockyardwifi.rize.bm | Dockyard:portal | WiFi captive portal |
| dockyard-admin.rize.bm | Dockyard:admin | Admin dashboard |
| bpsai-ssh.rize.bm | BPS-AI:22 | Browser SSH |
| context-ssh.rize.bm | Nexus:22 | Browser SSH |

All served via Cloudflare Tunnel (cloudflared service on each server).

---

## Key Contacts

| Role | Name | Email |
|------|------|-------|
| Developer / Owner | Gilbert "Artie" Darrell | artiedarrell@gmail.com, gadarrell@rize.bm |
| BPS Client | Alexander Rollin | arollin@bps.bm |
| Dockyard (payment) | Martin | (pending) |
| Biz Dev | Sarah | (Rize) |
| AI Dev email | — | aidev@rize.bm |

---

*Generated by Talos C2 verification protocol. Last updated: 2026-02-05 17:00 UTC*
