# Homebase TODO

**Current Version:** 0.4.1

---

## Phase 1 - Core Dashboard (v0.1.0) - COMPLETE
- [x] Server status polling via SSH
- [x] Real-time metrics (CPU, memory, disk)
- [x] React dashboard with Tailwind
- [x] PM2 deployment
- [x] Cloudflare tunnel setup
- [x] Auto-refresh (30s)
- [x] Hyper-V Windows support

## Phase 2 - Central Command Foundation (v0.2.0) - COMPLETE
- [x] Project auto-discovery service
- [x] Security monitoring service
- [x] Credential management service (Fernet encryption)
- [x] Log aggregation service
- [x] Frontend pages (Security, Discovery, Navigation)

## Phase 3 - Historical Metrics (v0.3.0) - COMPLETE
- [x] Metrics history database table
- [x] Historical metrics API endpoints
- [x] Metrics recording via cron (every 5 min)
- [x] 30-day data retention with daily cleanup

## Phase 3.1 - Metrics Charts (v0.3.1) - COMPLETE
- [x] Recharts line chart for CPU/Memory/Disk
- [x] Time range selector (6h/24h/48h/7d)
- [x] Server selector tabs
- [x] Summary cards with avg/max values

## Phase 4 - Project Docs Aggregator (v0.4.0) - COMPLETE
- [x] SSH sync to pull project documentation
- [x] Parse TODO.md with P0-P3 priorities
- [x] Extract version from CHANGELOG.md
- [x] Projects dashboard page
- [x] Email alerts configured and tested
- [x] Added Relay 2.0 to server monitoring

---

## Phase 5 - Enhanced Alerts (v0.5.0) - NEXT
- [ ] Slack/Discord webhook integration
- [ ] Uptime percentage tracking
- [ ] Response time monitoring
- [ ] Alert thresholds configuration

## Phase 6 - Automation & Integration (v0.6.0)
- [ ] GitHub integration (show recent commits)
- [ ] One-click deployments (pm2 restart, git pull)
- [ ] Scheduled security scans
- [ ] Auto-remediation for common issues
- [ ] Claude Code integration for automated fixes

## Phase 7 - Advanced Features (v1.0.0)
- [ ] Multi-tenancy support
- [ ] Role-based access control
- [ ] Cost tracking per server
- [ ] Mobile-responsive dashboard
- [ ] API key management UI
- [ ] Log search and filtering

---

## Bugs
- None currently tracked

## Ideas Backlog
- Mobile app (React Native)
- Slack bot for status queries
- Integration with Relay for AI-driven alerts
- Terraform/Ansible integration for infrastructure management

---

*Last Updated: 2026-01-29*
