# Changelog

## [0.2.0] - 2026-01-28

### Added
- **Project Auto-Discovery**
  - New `/api/discovery/*` endpoints
  - Scans all servers for projects automatically
  - Detects projects via package.json, requirements.txt, docker-compose, .git
  - Extracts version from VERSION files or package.json
  - Parses README for project descriptions
  - Tracks git remote URLs

- **Security Monitoring**
  - New `/api/security/*` endpoints
  - OS update checking via apt
  - Critical security update identification
  - Failed SSH attempt monitoring
  - Fail2ban status integration
  - Per-server security status

- **Credential Management**
  - New `/api/credentials/*` endpoints
  - Fernet encryption for all stored secrets
  - Support for SSH keys, API keys, passwords, tokens
  - Credential rotation with audit trail
  - Full access logging

- **Log Aggregation**
  - New `/api/logs/*` endpoints
  - Remote log fetching via SSH
  - Journalctl and PM2 log support
  - Automatic error pattern detection
  - Log snapshot storage

- **Frontend Enhancements**
  - Added React Router for multi-page navigation
  - New Security page with server security table
  - New Discovery page with project cards
  - Navigation bar with active state
  - Status badges for security alerts

- **Backend Services**
  - `services/database.py` - SQLite schema and queries
  - `services/discovery.py` - Project auto-discovery
  - `services/security.py` - Security monitoring
  - `services/keyManager.py` - Encrypted credential storage
  - `services/logCollector.py` - Log aggregation

### Changed
- Updated main.py to v0.2.0 with new endpoints
- Added cryptography and pydantic to requirements.txt
- Restructured backend with services directory

### Database
- Added `servers` table
- Added `projects` table
- Added `credentials` table with encrypted values
- Added `credential_access_logs` table
- Added `security_scans` table
- Added `log_snapshots` table

---

## [0.1.0] - 2026-01-28

### Added
- Initial release
- Server status dashboard for 8 servers
- Real-time metrics: CPU, memory, disk, uptime
- Hyper-V Windows server support with VM status
- Web and SSH quick-access buttons
- Auto-refresh every 30 seconds
- Dark theme UI
- FastAPI backend with asyncssh
- React frontend with Tailwind CSS
- PM2 process management
- Cloudflare tunnel integration

## v0.2.2 - January 29, 2026
- Configured SMTP for email alerts (smtp.office365.com)
- Tested email delivery successfully
