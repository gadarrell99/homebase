# Changelog

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
