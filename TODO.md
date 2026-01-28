# Homebase TODO

## Phase 1 - Core Dashboard (v0.1.0) ✅
- [x] Server status polling via SSH
- [x] Real-time metrics (CPU, memory, disk)
- [x] React dashboard with Tailwind
- [x] PM2 deployment
- [x] Cloudflare tunnel setup
- [x] Auto-refresh (30s)
- [x] Hyper-V Windows support

## Phase 2 - Central Command Foundation (v0.2.0) ✅
- [x] Project auto-discovery service
  - [x] Scan all servers for projects
  - [x] Detect via package.json, requirements.txt, docker-compose, .git
  - [x] Extract version from VERSION or package.json
  - [x] Parse README for descriptions
  - [x] Track git remotes
- [x] Security monitoring service
  - [x] Check OS updates (apt list --upgradable)
  - [x] Identify critical security updates
  - [x] Monitor failed SSH attempts
  - [x] Fail2ban integration
- [x] Credential management service
  - [x] Fernet encryption for secrets
  - [x] Store SSH keys, API keys, passwords, tokens
  - [x] Credential rotation
  - [x] Access logging
- [x] Log aggregation service
  - [x] Fetch logs via SSH (journalctl, pm2)
  - [x] Error pattern detection
  - [x] Store log snapshots
- [x] Frontend pages
  - [x] Security page with server table
  - [x] Discovery page with project cards
  - [x] Navigation between pages

## Phase 3 - Enhanced Monitoring
- [ ] Historical metrics storage (SQLite/PostgreSQL)
- [ ] 24h/7d charts for CPU, memory, disk
- [ ] Email alerts for critical security issues
- [ ] Slack/Discord webhook integration
- [ ] Uptime percentage tracking
- [ ] Response time monitoring

## Phase 4 - Automation & Integration
- [ ] GitHub integration (show recent commits)
- [ ] One-click deployments (pm2 restart, git pull)
- [ ] Scheduled security scans
- [ ] Auto-remediation for common issues
- [ ] Claude Code integration for automated fixes

## Phase 5 - Advanced Features
- [ ] Multi-tenancy support
- [ ] Role-based access control
- [ ] Cost tracking per server
- [ ] Mobile-responsive dashboard
- [ ] API key management UI
- [ ] Log search and filtering

## Bugs
- None currently tracked

## Ideas Backlog
- Mobile app (React Native)
- Slack bot for status queries
- Integration with Relay for AI-driven alerts
- Terraform/Ansible integration for infrastructure management
