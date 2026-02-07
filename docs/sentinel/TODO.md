# Sentinel — TODO

## Critical Priority
- [ ] Real-time heartbeat timeline display (show last heartbeat per agent with visual indicator)
- [ ] Alert history page with search and date filtering
- [ ] Guardrail violation detection and logging (flag when agent tries to exceed boundaries)
- [ ] Kill switch UI button with two-step confirmation dialog
- [ ] Heartbeat latency tracking (how long between expected and actual heartbeat)

## High Priority
- [ ] Agent action approval queue (agents request permission for write operations, CEO approves)
- [ ] Anomaly detection baseline (learn normal behavior patterns, flag deviations)
- [ ] Security scan integration (connect to actual vulnerability scanners)
- [ ] Pipeline monitor dashboard (show Cortex audit: last run, result, next scheduled)
- [ ] Agent error rate tracking with trend visualization
- [ ] Escalation rules: warning (10 min) → critical (25 min) → CEO alert (automatic)

## Medium Priority
- [ ] Custom email alert templates (configurable per severity level)
- [ ] Agent performance metrics dashboard (response time, task completion rate)
- [ ] Audit trail search with date range and agent filters
- [ ] Agent comparison view (side-by-side status cards)
- [ ] Resource usage trends (CPU/memory charts over time per agent)

## Low Priority
- [ ] Historical heartbeat gap analysis (trend charts)
- [ ] PRTG integration for infrastructure-level correlation
- [ ] Mobile push notifications for critical alerts
- [ ] Automated agent restart on degradation (with CEO pre-approval)
- [ ] Compliance reporting export (PDF) for client audits

## Completed
- [x] Basic heartbeat monitoring (2026-02-06)
- [x] Sentinel overview API — /api/sentinel/overview (2026-02-06)
- [x] Per-agent status API — /api/sentinel/agents (2026-02-06)
- [x] Guardrails definition API — /api/sentinel/guardrails (2026-02-06)
- [x] Server resources API — /api/sentinel/resources (2026-02-07)
- [x] Pipeline monitor integration (2026-02-07)
- [x] Cron job status tracking (2026-02-07)
- [x] Sentinel page with tabs (Overview, Agents, Alerts, Guardrails) (2026-02-07)
