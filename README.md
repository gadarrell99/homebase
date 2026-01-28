# Homebase - Central Command

Infrastructure & Project Dashboard for Rize Technologies.

**Live URL:** https://homebase.rize.bm

## Overview

Homebase is the **Central Command** for Rize Technologies infrastructure. It provides real-time server monitoring, project discovery across all servers, security monitoring, centralized credential management, and log aggregation.

## Features

### Server Monitoring
- Real-time status indicators (online/offline)
- System metrics collection via SSH
- CPU usage percentage
- Memory usage (used/total)
- Disk usage (used/total)
- Uptime tracking
- Hyper-V VM status (Windows support)

### Project Auto-Discovery (v0.2.0)
- Automatic scanning of all servers for projects
- Detection via package.json, requirements.txt, docker-compose, .git
- Version tracking from VERSION files or package.json
- Git remote URL extraction
- README description parsing

### Security Monitoring (v0.2.0)
- OS update checking (apt list --upgradable)
- Critical security update alerts
- Failed SSH authentication monitoring
- Fail2ban integration
- Per-server security status dashboard

### Key Management (v0.2.0)
- Encrypted credential storage (Fernet encryption)
- Support for SSH keys, API keys, passwords, tokens
- Credential rotation with audit logging
- Access logging for all credential operations
- Server-specific credential association

### Log Aggregation (v0.2.0)
- Remote log fetching via SSH
- Support for journalctl and PM2 logs
- Error pattern detection (errors, exceptions, crashes)
- Log snapshot storage
- Recent error querying

### User Interface
- Clean, dark-themed dashboard
- Multi-page navigation (Servers, Security, Discovery)
- Server status cards with color-coded indicators
- Security overview table with alerts
- Project discovery grid with metadata
- One-click Web UI and SSH access
- Auto-refresh every 30 seconds
- Responsive design

## Server Matrix

| Server | IP Address | Admin User | Web URL | SSH URL | Purpose |
|--------|------------|------------|---------|---------|---------|
| Cobalt | 192.168.65.243 | cobaltadmin | homebase.rize.bm | cobalt-ssh.rize.bm | Homebase Dashboard |
| Relay | 192.168.65.248 | relayadmin | relay.rize.bm | relay-ssh.rize.bm | AI Orchestration |
| BPS AI | 192.168.65.246 | bpsaiadmin | bpsai.rize.bm | bpsai-ssh.rize.bm | Police Case Mgmt |
| Context Hub | 192.168.65.247 | contextadmin | context.rize.bm | context-ssh.rize.bm | IT Support Platform |
| Dockyard | 192.168.65.252 | dockyardadmin | dockyard-admin.rize.bm | dockyard-ssh.rize.bm | WiFi Captive Portal |
| Vector | 192.168.65.249 | betadmin | app.bet.bm | vector-ssh.bet.bm | BET Transport |
| Claude Code | 192.168.65.245 | claudedevadmin | - | claude-dev-ssh.rize.bm | AI Worker Host |
| Hyper-V | 192.168.65.253 | Administrator | - | hyperv-ssh.rize.bm | VM Host (Windows) |

## Tech Stack

### Backend
- **Framework:** FastAPI
- **SSH Client:** asyncssh (async SSH connections)
- **Database:** SQLite (migrating to PostgreSQL)
- **Encryption:** cryptography (Fernet)
- **ASGI Server:** Uvicorn
- **Python:** 3.12+

### Frontend
- **Framework:** React 18
- **Routing:** React Router v7
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **Language:** JavaScript/JSX

### Infrastructure
- **Process Manager:** PM2
- **Tunnel:** Cloudflare Tunnel
- **Platform:** Ubuntu 22.04 LTS

## API Endpoints

### Health & Servers
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with version and timestamp |
| `/api/servers` | GET | All servers with current metrics |

### Discovery
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/discovery/scan` | GET | Check server reachability |
| `/api/discovery/projects` | GET | Discover all projects |
| `/api/discovery/projects/{ip}` | GET | Discover projects on specific server |
| `/api/discovery/registered` | GET | Get registered projects |

### Security
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/security/scan` | GET | Full security scan all servers |
| `/api/security/updates/{ip}` | GET | Check OS updates on server |
| `/api/security/auth-logs/{ip}` | GET | Get auth logs for server |
| `/api/security/service/{ip}/{service}` | GET | Check service status |

### Credentials
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/credentials` | GET | List all credentials (no values) |
| `/api/credentials` | POST | Store new credential |
| `/api/credentials/{name}` | GET | Retrieve credential value |
| `/api/credentials/{id}/rotate` | PUT | Rotate credential |
| `/api/credentials/{name}` | DELETE | Delete credential |
| `/api/credentials/logs` | GET | Get access logs |

### Logs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/logs/{ip}/{service}` | GET | Fetch service logs |
| `/api/logs/{ip}/{service}/analyze` | GET | Analyze logs for errors |
| `/api/logs/errors/recent` | GET | Get recent errors |

## Project Structure

```
homebase/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── homebase.db          # SQLite database
│   ├── requirements.txt     # Python dependencies
│   ├── services/
│   │   ├── database.py      # Database schema & queries
│   │   ├── discovery.py     # Project auto-discovery
│   │   ├── security.py      # Security monitoring
│   │   ├── keyManager.py    # Credential encryption
│   │   └── logCollector.py  # Log aggregation
│   └── venv/                # Virtual environment
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app with routing
│   │   └── ...
│   ├── dist/                # Production build
│   └── package.json
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── DEPLOYMENT.md
├── ecosystem.config.cjs
├── README.md
├── CHANGELOG.md
├── TODO.md
└── PROJECT_PLAN.md
```

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- PM2 (`npm install -g pm2`)
- SSH key access to monitored servers

### Installation

```bash
# Clone repository
git clone git@github.com:artieRizmo/homebase.git
cd homebase

# Setup backend
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup frontend
cd ../frontend
npm install
npm run build

# Start with PM2
cd ..
pm2 start ecosystem.config.cjs
```

## PM2 Commands

```bash
pm2 status           # View status
pm2 logs             # View logs
pm2 restart all      # Restart services
pm2 save             # Save process list
```

## Security Notes

- Encryption keys stored in `.homebase_key` (chmod 600)
- Credentials encrypted at rest using Fernet
- All credential access is logged
- SSH connections use key-based auth only

## Roadmap

See [TODO.md](TODO.md) for planned features.

## License

MIT License - Rize Technologies
