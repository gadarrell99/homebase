# Homebase

Infrastructure & Project Dashboard for Rize Technologies.

**Live URL:** https://homebase.rize.bm

## Overview

Homebase is a real-time server monitoring dashboard that provides visibility into the Rize Technologies infrastructure. It displays server status, system metrics, and quick-access links for all servers in the fleet.

## Features

### Server Monitoring
- Real-time status indicators (online/offline)
- System metrics collection via SSH
- CPU usage percentage
- Memory usage (used/total)
- Disk usage (used/total)
- Uptime tracking

### User Interface
- Clean, dark-themed dashboard
- Server status cards with color-coded indicators
- One-click Web UI access
- One-click SSH access (via browser)
- Auto-refresh every 30 seconds
- Responsive design

### Infrastructure
- FastAPI backend with async SSH
- React 18 frontend with Vite
- PM2 process management
- Cloudflare Tunnel for secure access

## Server Matrix

| Server | IP Address | Admin User | Web URL | SSH URL |
|--------|------------|------------|---------|---------|
| Cobalt | 192.168.65.243 | cobaltadmin | homebase.rize.bm | cobalt-ssh.rize.bm |
| Relay | 192.168.65.248 | relayadmin | relay.rize.bm | relay-ssh.rize.bm |
| BPS AI | 192.168.65.246 | bpsaiadmin | bpsai.rize.bm | bpsai-ssh.rize.bm |
| Context Hub | 192.168.65.247 | contextadmin | context.rize.bm | context-ssh.rize.bm |
| Dockyard | 192.168.65.252 | dockyardadmin | dockyard-admin.rize.bm | dockyard-ssh.rize.bm |
| Vector | 192.168.65.249 | betadmin | app.bet.bm | vector-ssh.bet.bm |
| Claude Code | 192.168.65.245 | claudedevadmin | - | claude-dev-ssh.rize.bm |
| Hyper-V | 192.168.65.253 | Administrator | - | - |

## Tech Stack

### Backend
- **Framework:** FastAPI
- **SSH Client:** asyncssh (async SSH connections)
- **ASGI Server:** Uvicorn
- **Python:** 3.12+

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **Language:** JavaScript/JSX

### Infrastructure
- **Process Manager:** PM2
- **Tunnel:** Cloudflare Tunnel
- **Platform:** Ubuntu 22.04 LTS

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with timestamp |
| `/api/servers` | GET | All servers with current metrics |
| `/*` | GET | SPA fallback (serves React app) |

### Example Response

```json
{
  "servers": [
    {
      "name": "Cobalt",
      "ip": "192.168.65.243",
      "web_url": "homebase.rize.bm",
      "ssh_url": "cobalt-ssh.rize.bm",
      "status": "online",
      "uptime": "5 days, 3 hours",
      "memory_used": 2048,
      "memory_total": 8192,
      "disk_used": 25,
      "disk_total": 100,
      "cpu_percent": 12.5
    }
  ],
  "timestamp": 1706400000.0
}
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

### Development Mode

```bash
# Backend (with auto-reload)
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (with HMR)
cd frontend
npm run dev
```

## Project Structure

```
homebase/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── venv/                # Virtual environment
├── frontend/
│   ├── src/                 # React source code
│   ├── dist/                # Production build
│   ├── package.json         # Node dependencies
│   ├── vite.config.js       # Vite configuration
│   └── tailwind.config.js   # Tailwind configuration
├── docs/
│   ├── API.md               # API documentation
│   ├── ARCHITECTURE.md      # System architecture
│   └── DEPLOYMENT.md        # Deployment guide
├── ecosystem.config.cjs     # PM2 configuration
├── README.md                # This file
├── CHANGELOG.md             # Version history
└── TODO.md                  # Planned features
```

## PM2 Commands

```bash
# View status
pm2 status

# View logs
pm2 logs

# Restart services
pm2 restart all

# Stop services
pm2 stop all
```

## Documentation

- [API Reference](docs/API.md) - Detailed API documentation
- [Architecture](docs/ARCHITECTURE.md) - System design and diagrams
- [Deployment](docs/DEPLOYMENT.md) - Full deployment guide

## Adding a New Server

1. Edit `backend/main.py`
2. Add entry to `SERVERS` list:
   ```python
   {"name": "ServerName", "ip": "192.168.65.XXX", "user": "admin", "web_url": "domain.rize.bm", "ssh_url": "ssh.rize.bm"},
   ```
3. Ensure SSH key access is configured
4. Restart: `pm2 restart homebase-api`

## Troubleshooting

### Server Shows Offline
- Verify SSH key access: `ssh user@ip`
- Check network connectivity
- Review PM2 logs: `pm2 logs homebase-api`

### High CPU on Dashboard
- Check if asyncssh connections are timing out
- Verify SSH timeout setting (default: 5s)

### Frontend Not Loading
- Verify build exists: `ls frontend/dist`
- Rebuild: `cd frontend && npm run build`
- Check PM2 status: `pm2 status`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test locally
5. Submit a pull request

## License

MIT License - Rize Technologies

## Support

For issues or questions, contact the Rize Technologies infrastructure team.
