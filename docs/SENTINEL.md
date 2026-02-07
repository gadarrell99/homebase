# Sentinel — AI Agent Oversight System

**Version:** 1.0.0
**Host:** rizeadmin@192.168.65.245 (integrated into Homebase)
**Status:** ACTIVE
**Database:** ~/homebase/data/agents.db

---

## Overview

Sentinel is Rize Technology Group's agent oversight system — the "immune system" of the Trinity Architecture. It monitors all AI agents (David Bishop, Apex, Aegis, Cortex), enforces guardrails, and provides the CEO with a kill switch for any agent.

Sentinel runs as part of Homebase on Rize-Apps (.245), not as a standalone service.

---

## Capabilities

### Active
- **Heartbeat Monitor:** Tracks agent health via periodic pings. Alerts on missed heartbeats.
- **Agent Registry:** Maintains database of all registered agents with status, capabilities, and config.
- **Audit Trail:** Logs all agent actions, guardrail triggers, and administrative decisions.
- **Maintenance Windows:** 03:00-04:00 UTC daily — agents have relaxed thresholds during this window.
- **Dashboard UI:** Integrated into Homebase at /settings and /agents views.

### Planned
- **Kill Switch:** SIGTERM to agent process → full incident log → CEO notification → block restart until CEO approval.
- **Auto-Restart:** If agent misses 3+ consecutive heartbeats AND process is confirmed dead AND not in maintenance window → automatic restart with probation.
- **Comms Gateway:** All agent external communications route through Sentinel for PII scanning and audit logging.
- **Teams Bot:** CEO/CTO admin interface — status, health, kill {agent}, restart {agent}, report.
- **LLM Brain:** AI-powered reasoning for anomaly detection and escalation decisions.

---

## Agent Registry

| Agent | Server | Port | Status | Type |
|-------|--------|------|--------|------|
| david-bishop | 192.168.65.241 | 9001 | healthy | ai_agent |
| apex | 192.168.65.241 | 9002 | healthy | ai_agent |
| aegis | 192.168.65.241 | 9003 | healthy | ai_agent |
| sentinel | 192.168.65.245 | — | active | oversight |
| cortex | 192.168.65.237 | 9100 | planned | ai_agent |

---

## Database Schema (agents.db)

### Tables
- **agents** — Registry of all agents (id, display_name, version, host, status, config, channels)
- **heartbeats** — Heartbeat log (agent_id, timestamp, status, response_time)
- **audit_log** — All administrative actions and guardrail events
- **incidents** — Kill switch activations and incident reports
- **compliance_violations** — Guardrail breach records
- **guardrail_rules** — Per-agent guardrail configurations
- **guardrail_triggers** — Log of triggered guardrail events
- **maintenance_windows** — Scheduled maintenance periods
- **request_log** — Agent request tracking
- **research_items** — Research findings (Phase 3)

---

## Escalation Matrix

| Severity | Response Time | Action | Notification |
|----------|--------------|--------|--------------|
| Info | None | Log only | Daily digest at 08:00 UTC |
| Warning | 30 min | Log + monitor | Email if persists 1 hour |
| Error | 5 min | Log + auto-fix attempt | Immediate email |
| Critical | Immediate | Log + kill switch | Email every 5 min until CEO acknowledges |

---

## Kill Switch Protocol

1. SIGTERM to agent process
2. Full incident logged with context (what triggered, agent state, recent actions)
3. Immediate email to CEO (artiedarrell@gmail.com + gadarrell@rize.bm)
4. Agent blocked from restart until CEO approval
5. All logs preserved for review
6. Resume requires CEO acknowledgment → Sentinel restarts with 1-hour probation (lower thresholds)

### Auto-Trigger Conditions
- 10+ malformed responses in sequence
- >50% error rate sustained for 5 minutes
- Forbidden resource access attempt
- >60s sustained response times
- 3+ user complaints per hour

---

## Guardrails Framework

### Per-Agent Permissions
| Guardrail | David | Apex | Aegis | Sentinel |
|-----------|-------|------|-------|----------|
| Read CRM/Pipeline | ✅ R/W | ❌ | ❌ | ❌ |
| Read Financial Systems | ❌ | ✅ R/O | ❌ | ❌ |
| Read Infrastructure Monitoring | ❌ | ❌ | ✅ R/O | ❌ |
| Read Agent Logs | ❌ | ❌ | ❌ | ✅ R/O |
| Start/Stop Agents | ❌ | ❌ | ❌ | ✅ |
| Send Email to Customers | ❌ | ❌ | ❌ | ❌ |
| Modify Own Guardrails | ❌ | ❌ | ❌ | ❌ |

### Sentinel-Specific
**Autonomous (no approval needed):**
- Monitor heartbeats, verify processes, check health endpoints
- Send alert emails to CEO
- Restart crashed agents (conditions met)
- Activate kill switch (trigger thresholds met)
- Generate reports and observations

**Requires CEO Approval:**
- Resume a killed agent
- Implement code changes
- Add new integrations or agents
- Modify monitoring thresholds
- Deploy updates to production

**Never Allowed (hardcoded):**
- Modify its own guardrails
- Access financial systems
- Delete production data
- Disable logging
- Override kill switch without CEO
- Communicate externally on behalf of company

---

## API Endpoints (Current + Planned)

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| /api/agents | GET | ✅ Active | List all registered agents |
| /api/agents/{id}/heartbeat | POST | ✅ Active | Accept heartbeat from agent |
| /api/agents/{id}/status | GET | ✅ Active | Get agent status |
| /api/agents/health | GET | 🔲 Planned | Aggregated health of all agents |
| /api/audit/recent | GET | 🔲 Planned | Last 50 audit trail entries |
| /api/kill-switch/{agent} | POST | 🔲 Planned | Emergency stop for agent |
| /api/maintenance/windows | GET | ✅ Active | List maintenance windows |
| /settings | GET | ✅ Active | Sentinel settings UI |

---

## Authorized Users
- Gilbert Darrell (CEO) — gadarrell@rize.bm — Full access
- Mary Ocoy (CTO) — mocoy@rize.bm — Full access
- No other users have Sentinel admin access

---

## Files

| File | Location | Purpose |
|------|----------|---------|
| sentinel.py | ~/homebase/backend/services/sentinel.py | Core service |
| agents.db | ~/homebase/data/agents.db | Agent database |
| SENTINEL.md | ~/homebase/docs/SENTINEL.md | This document |

---

## Phase 2 Modules (Added 2026-02-07)

### Kill Switch Module
**Location:** ~/homebase/backend/services/kill_switch.py

**Functions:**
- `kill_agent(agent_id, reason, triggered_by)` — Emergency stop an agent
- `resume_agent(agent_id, approved_by)` — Resume killed agent (CEO approval required)
- `get_kill_status(agent_id)` — Get current kill status
- `check_auto_triggers(agent_id)` — Check if auto-kill thresholds are met

**Safety Rules (HARDCODED):**
1. Sentinel can NEVER kill itself
2. David Bishop requires CEO pre-approval (LIVE production)
3. All kills logged with full context

**Auto-Trigger Thresholds:**
- 10+ malformed responses in sequence
- >50% error rate sustained for 5 minutes
- Forbidden resource access attempt
- >60s sustained response times
- 3+ user complaints per hour

### Auto-Restart Module
**Location:** ~/homebase/backend/services/auto_restart.py

**Functions:**
- `check_and_restart(agent_id)` — Check conditions and restart if needed
- `is_maintenance_window()` — Check if in maintenance window
- `get_restart_count(agent_id, hours)` — Get recent restart count
- `verify_process_alive(agent_id)` — SSH check if process is running

**Restart Conditions (ALL must be true):**
1. Agent missed 3+ consecutive heartbeats (15+ minutes)
2. Process confirmed dead via SSH check
3. NOT in maintenance window (03:00-04:00 UTC)
4. Agent NOT in 'killed' state
5. Agent NOT restarted more than 3 times in last hour

### Comms Gateway Module
**Location:** ~/homebase/backend/services/comms_gateway.py

**Functions:**
- `scan_and_send_email(from_agent, to_address, subject, body)` — Scan and send email
- `scan_text(agent_id, text)` — Scan any text for PII
- `get_pii_report(agent_id, days)` — Get PII scan statistics

**PII Patterns Detected:**
- SSN (XXX-XX-XXXX) — REDACTED
- Credit cards (16-digit) — REDACTED
- Phone numbers (US/Bermuda +1/441) — REDACTED
- National ID numbers — REDACTED
- Email addresses — FLAGGED (not redacted)

### Database Tables

**incidents** — Kill switch events
- id, agent_id, incident_type, reason, triggered_by, created_at
- resolved_at, resolved_by, status, context

**restart_log** — Auto-restart attempts
- id, agent_id, attempted_at, success, method, notes

**pii_scan_log** — PII scanning log
- id, agent_id, scanned_at, pii_found, patterns, action_taken, destination
