# Sentinel Architecture

## Overview
Sentinel is the oversight layer for the Rize AI Agent ecosystem, providing monitoring, security guardrails, and audit logging.

## Module Map

### Core Services (backend/services/)
- sentinel.py - Config management, maintenance windows
- guardrails.py - Request filtering, permission checks
- alert_checker.py - Threshold monitoring, alert generation
- auto_restart.py - Agent health monitoring, restart logic
- kill_switch.py - Emergency agent termination
- request_tracker.py - Request logging, rate tracking
- pii_scan_log.py - PII detection logging

### Data Storage
- agents.db (SQLite)
  - agents - Agent registry
  - heartbeats - Agent health data
  - audit_log - Action audit trail
  - request_log - Request history
  - guardrail_rules - Permission rules
  - guardrail_triggers - Rule violation log
  - restart_log - Restart history
  - sentinel_config - Sentinel settings
  - maintenance_windows - Maintenance scheduling

### API Endpoints (main.py)
- /api/sentinel/* - Sentinel dashboard APIs
- /api/agents/*/heartbeat - Agent health reporting
- /api/guardrails/* - Guardrail management

## Data Flow

1. Agent Heartbeat Flow:
   Agent -> POST /api/agents/{id}/heartbeat -> heartbeats table
   -> Sentinel checks health (every 30 min)
   -> If degraded -> alert_checker -> email CEO

2. Request Flow:
   Agent -> POST /api/agents/{id}/request -> guardrails.py check
   -> If blocked -> guardrail_triggers table -> alert
   -> If allowed -> request_log table -> process

3. Alert Flow:
   alert_checker -> creates alert -> sentinel_alerts table
   -> Email to CEO
   -> CEO acknowledges via UI -> audit_log entry

## Escalation Matrix

| Severity | Response Time | Notification | Action |
|----------|--------------|--------------|--------|
| Critical | Immediate | Email + Teams | Auto-kill agent |
| Warning | 15 min | Email | Manual review |
| Info | 24 hours | Dashboard only | Log only |

## Integration Points

### David Bishop
- Heartbeat every 5 min to port 7070
- PII gateway for email content
- Teams messaging audit

### Apex
- Heartbeat every 5 min to port 9002
- Financial data guardrails
- CEO approval for transactions >K

### Aegis
- Heartbeat every 5 min to port 9003
- Infrastructure change guardrails
- CEO approval for production changes

### Cortex
- Fleet scanning results
- Drift detection alerts
- Context API queries

## Architecture Diagram

Agents Server (.241)                 Rize-Apps (.245)
+------------------+                 +------------------+
| David Bishop     |---heartbeat---->| Homebase         |
| Apex            |---heartbeat---->|   Sentinel       |
| Aegis           |---heartbeat---->|   - oversight    |
| Cortex          |---scan data---->|   - guardrails   |
+------------------+                 |   - audit log    |
                                     +------------------+
                                            |
                                            v
                                     +------------------+
                                     | CEO Dashboard    |
                                     | - Alerts         |
                                     | - Approvals      |
                                     | - Kill Switch    |
                                     +------------------+
