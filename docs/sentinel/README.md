# Sentinel — AI Agent Oversight System

## Purpose
Sentinel is Homebase's critical security subsystem responsible for monitoring all AI agents in the Rize fleet, enforcing guardrails, managing kill switches, and serving as the single alerting gateway to the CEO.

Every AI agent is a potential threat vector. David Bishop handles email and customer communications, Apex will access financial data, Aegis monitors infrastructure. If any agent goes rogue, exceeds its boundaries, or fails silently, Sentinel is the safety net.

## Architecture
- **Part of:** Homebase (not a standalone service)
- **Location:** Rize-Apps (.245:8000)
- **Backend:** ~/homebase/backend/services/sentinel.py
- **Frontend:** ~/homebase/backend/static/sentinel.html
- **Database:** agents.db (SQLite — heartbeats, status history)
- **Report data:** data/sentinel-report.json

## API Endpoints (7)
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/sentinel/overview | GET | Health summary: healthy/degraded/offline counts, alert counts |
| /api/sentinel/agents | GET | Per-agent detail: heartbeat time, uptime, memory, CPU, errors |
| /api/sentinel/alerts | GET | Active alerts with severity and timestamps |
| /api/sentinel/guardrails | GET | Guardrail definitions per agent |
| /api/sentinel/requests | GET | Agent action request log |
| /api/sentinel/crons | GET | Scheduled job status |
| /api/sentinel/resources | GET | Server resource usage (CPU, memory, disk) |

## Monitoring Hierarchy
```
CEO (final authority)
  └── Sentinel (automated oversight)
       ├── David Bishop (.241) — LIVE — security/email/Teams
       ├── Apex (.241) — MOCK — finance/revenue leakage
       ├── Aegis (.241) — MOCK — infrastructure monitoring
       └── Cortex (.237) — ACTIVE — fleet orchestration
            ├── The Architect — CLI build/audit persona
            └── The Inquisitor — CLI verification persona
```

## Heartbeat Protocol
1. Every agent sends POST to /api/agents/{id}/heartbeat every 5 minutes
2. Sentinel checks heartbeat freshness on each overview request
3. Miss 2 heartbeats (10 min) → status changes to "degraded"
4. Miss 5 heartbeats (25 min) → status changes to "offline", CEO alert sent

## Kill Switch Protocol
1. Sentinel detects anomaly OR receives manual trigger from CEO
2. Kill command sent to target agent — requires confirmation
3. Agent stops all operations immediately
4. CEO notified via email (artiedarrell@gmail.com + gadarrell@rize.bm)
5. Agent remains stopped until manually restarted by CEO
6. All events logged immutably in audit trail

## Security Principles
- Sentinel CANNOT modify its own guardrails
- Sentinel CANNOT deploy new agent code
- Sentinel CANNOT access agent credentials or secrets
- Kill switch requires explicit confirmation (no auto-kill)
- All actions logged immutably — no deletion capability
- CEO is the only authority for guardrail changes
