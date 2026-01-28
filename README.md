# 🏠 Homebase

Infrastructure & Project Dashboard for Rize Technologies.

**URL:** https://homebase.rize.bm

## Features

- Real-time server status monitoring (7 servers)
- System metrics: CPU, memory, disk, load
- Uptime tracking
- One-click Web and SSH access
- Auto-refresh every 30 seconds
- Dark theme UI

## Server Matrix

| Server | IP | Web | SSH |
|--------|-----|-----|-----|
| Cobalt | 192.168.65.243 | homebase.rize.bm | cobalt-ssh.rize.bm |
| Relay | 192.168.65.248 | relay.rize.bm | relay-ssh.rize.bm |
| BPS AI | 192.168.65.246 | bpsai.rize.bm | bpsai-ssh.rize.bm |
| Context Hub | 192.168.65.247 | context.rize.bm | context-ssh.rize.bm |
| Dockyard | 192.168.65.252 | dockyard-admin.rize.bm | dockyard-ssh.rize.bm |
| Vector | 192.168.65.249 | app.bet.bm | vector-ssh.bet.bm |
| Claude Code | 192.168.65.245 | - | claude-dev-ssh.rize.bm |
| Hyper-V | 192.168.65.253 | - | - |

## Tech Stack

- **Backend:** FastAPI + asyncssh + uvicorn
- **Frontend:** React 18 + Vite + Tailwind CSS
- **Process Manager:** PM2
- **Tunnel:** Cloudflare

## API Endpoints

- `GET /api/servers` - All servers with status/metrics
- `GET /api/health` - Health check

## Quick Start
```bash
# SSH to Cobalt
ssh cobaltadmin@192.168.65.243

# Check services
pm2 status

# View logs
pm2 logs
```

## License

MIT - Rize Technologies
