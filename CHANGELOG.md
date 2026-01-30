## [0.5.0] - 2026-01-30

### Added
- TOTP-based 2FA authentication (Google Authenticator/Authy compatible)
- QR code generation for authenticator app setup
- Backup codes (10 one-time use codes)
- Encrypted TOTP secret storage (Fernet encryption)
- Login flow: Password → 2FA code → Access
- 'Remember this device for 30 days' option with device tokens
- Email notification on new device login
- Session management with JWT-style tokens
- Auth logging for security auditing
- User authentication endpoints:
  - POST /api/auth/login - Password authentication
  - POST /api/auth/verify-2fa - 2FA code verification
  - POST /api/auth/setup-2fa - Initialize 2FA
  - POST /api/auth/verify-2fa-setup - Complete 2FA setup
  - GET /api/auth/me - Get current user
  - POST /api/auth/logout - Logout
  - GET /api/auth/devices - List trusted devices
  - DELETE /api/auth/devices/{id} - Revoke device
  - GET /api/auth/logs - View auth logs
  - POST /api/auth/change-password - Change password

### Changed
- Version updated to 0.5.0

### Security
- Default admin account created on first run with random password
- Password hashing using PBKDF2-SHA256 with salt
- Secure session tokens (64 bytes urlsafe)
- Device trust tokens (48 bytes urlsafe)


# Changelog
## [0.4.5] - 2026-01-30

### Added
- **Settings Page for Alerts**
  - New /settings route with alert configuration UI
  - Slider controls for CPU, Memory, Disk thresholds (50-100%)
  - Cooldown period configuration (5-60 minutes)
  - Alert recipients email field (comma-separated)
  - Enable/disable alerts toggle
  - Settings stored in SQLite database

- **Settings API Endpoints**
  - GET /api/settings - retrieve all settings
  - PUT /api/settings - update settings
  - GET /api/settings/{key} - get single setting

- **Settings Service** (backend/services/settings.py)
  - SQLite settings table with default values
  - get_setting(), get_all_settings(), update_setting() functions

## [0.4.4] - 2026-01-30

### Added
- **Acronym Legend/Tooltips on Projects Page**
  - Doc badges now show descriptive tooltips on hover
  - Added visible legend at bottom: C=CHANGELOG, R=README, T=TODO, P=PROJECT_PLAN, AI=CLAUDE
  - Hover over any badge to see full description

## [0.4.1] - 2026-01-30

### Fixed
- **Servers Page Loading Performance**
  - Added server cache for instant page loads
  - Returns cached data immediately while refreshing in background
  - Added Force Refresh button for live data
  - Added SSH timeout wrapper (15s) to prevent hanging
  - Cache shows age indicator (e.g., cached 30s ago)

### Changed
- Updated API version to 0.4.1
- Metrics recording now also updates server cache


## [0.4.0] - 2026-01-29

### Added
- **Project Docs Aggregator Dashboard**
  - New /api/projects endpoint for all project summaries
  - New /api/projects/{name} for full project details
  - New /api/projects/{name}/todos for parsed TODO items
  - POST /api/projects/sync to trigger manual sync

- **Project Docs Sync Service** (backend/services/projectSyncService.py)
  - SSH to 7 servers to pull README, TODO, CHANGELOG, PROJECT_PLAN, CLAUDE.md
  - Automatic version extraction from CHANGELOG.md
  - TODO.md parser with P0-P3 priority detection
  - Open/completed status tracking
  - Stores full doc content in SQLite

- **Database Schema**
  - project_docs table (project, server_ip, doc_type, content, version, last_synced)
  - project_todos table (project, priority, status, description, completed_version)

- **Frontend Projects Page**
  - Cards for each project showing version, docs, TODO counts
  - Status badges: healthy/good/warning/busy based on open TODOs
  - Click to expand and view full docs
  - Priority badges (P0-P3) for TODO items
  - Sync All button to trigger manual sync

- **Cron Job**
  - Hourly sync: 0 * * * * curl -X POST /api/projects/sync

### Changed
- Added "Projects" to navigation between Servers and Metrics
- Updated version to 0.4.0

## [0.3.3] - 2026-01-29

### Added
- **Uptime Tracking** (backend/services/database.py)
  - uptime_events table to log status changes
  - record_uptime_event() - logs up/down transitions
  - get_uptime_percentage() - calculates uptime % for time period

## [0.3.2] - 2026-01-29

### Added
- **Critical Alert Service** (backend/services/alerts.py)
  - Email alerts for CPU/Memory/Disk > 90%
  - Offline server notifications
  - 15-minute cooldown to prevent spam
  - Test email sent successfully

## [0.3.1] - 2026-01-29

### Verified
- **Metrics Charts Working**
  - Recharts-based line charts for CPU, Memory, Disk
  - Time range selector: 6h, 24h, 48h, 7 days
  - Server tabs to switch between servers
  - Summary cards with avg/max values
  - Color-coded lines: blue=CPU, green=Memory, yellow=Disk

## [0.3.0] - 2026-01-29

### Added
- **Historical Metrics Storage**
  - Database table for storing server metrics over time
  - API endpoints for history and summary
  - Cron job records metrics every 5 minutes

## [0.2.0] - 2026-01-28

### Added
- Project Auto-Discovery
- Security Monitoring
- Credential Management
- Log Aggregation
- Frontend multi-page navigation

## [0.1.0] - 2026-01-28

### Added
- Initial release
- Server status dashboard
- Real-time metrics
- Hyper-V support with VM status
