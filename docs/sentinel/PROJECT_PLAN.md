# Sentinel — Project Plan & Roadmap

## Current: Phase 1 — Basic Monitoring (v1.0)
Status: ✅ Deployed
- Agent heartbeat tracking (5-minute intervals)
- Health status classification (healthy/degraded/offline)
- 7 API endpoints for monitoring data
- Sentinel HTML page with tabbed interface
- Pipeline monitor for Cortex audit freshness
- Cron job status tracking

## Next: Phase 2 — Active Oversight (v2.0)
Target: v1.5 of Homebase
- Real-time heartbeat timeline with visual indicators
- Guardrail violation detection and logging
- Kill switch UI with confirmation flow
- Alert history with search/filter capabilities
- Agent action approval queue (request → review → approve/deny)
- Escalation timeline (warning → critical → CEO alert)

## Future: Phase 3 — Intelligent Monitoring (v3.0)
Target: v2.0 of Homebase
- Behavioral baseline learning (normal patterns per agent)
- Anomaly detection (flag deviations from baseline)
- Predictive alerts (detect degradation before failure)
- Cross-agent correlation (detect cascading failures)
- PRTG integration for infrastructure-level context
- Security scan automation

## Vision: Phase 4 — Autonomous Oversight (v4.0)
- Self-healing: auto-restart degraded agents (with pre-approval rules)
- Compliance reporting for client-facing audits (PDF export)
- Real-time operational dashboard for all agent activities
- Mobile app for CEO alerts and quick approvals
- Multi-tenant support for managed client environments
