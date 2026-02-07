# Homebase - Deployment

## Server

- **Host:** 192.168.65.245 (Rize-Apps)
- **User:** rizeadmin
- **Path:** ~/homebase
- **Service:** PM2 (homebase)
- **Port:** 8000
- **URL:** https://homebase.rize.bm

## Prerequisites

```bash
# Python 3.10+
python3 --version

# Node.js 18+ (for PM2 and frontend)
node --version

# PM2 globally installed
npm install -g pm2
```

## Backend Setup

```bash
cd ~/homebase/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from services.database import init_database, seed_servers; init_database(); seed_servers()"
```

## Frontend Setup

```bash
cd ~/homebase/frontend

# Install dependencies
npm install

# Build for production
npm run build

# Output in dist/ served by FastAPI static files
```

## PM2 Configuration

`ecosystem.config.cjs`:
```javascript
module.exports = {
  apps: [
    {
      name: "homebase",
      cwd: "/home/rizeadmin/homebase/backend",
      script: "/home/rizeadmin/homebase/backend/venv/bin/uvicorn",
      args: "main:app --host 0.0.0.0 --port 8000",
      interpreter: "none"
    }
  ]
}
```

## Start Service

```bash
cd ~/homebase
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup  # Follow instructions to enable on boot
```

## Verification

```bash
# Check PM2 status
pm2 status homebase

# Test health endpoint
curl http://localhost:8000/health

# Test frontend
curl http://localhost:8000/ | head -20

# View logs
pm2 logs homebase
```

## Environment Variables

Create `backend/.env`:
```bash
# Database
DATABASE_PATH=./homebase.db

# Auth
JWT_SECRET=your-jwt-secret
SESSION_EXPIRE_HOURS=24

# SMTP for email notifications
SMTP_HOST=localhost
SMTP_PORT=2525
SMTP_FROM=homebase@rize.bm

# Feature flags
ENABLE_2FA=true
ENABLE_REDTEAM=false
```

## Cloudflare Tunnel

Homebase is exposed via Cloudflare tunnel on Talos:
```
homebase.rize.bm -> 192.168.65.245:8000
```

## Common Operations

### Restart
```bash
pm2 restart homebase
```

### View Logs
```bash
pm2 logs homebase --lines 100
```

### Update
```bash
cd ~/homebase
git pull

# Rebuild frontend if changed
cd frontend && npm run build

# Restart
pm2 restart homebase
```

### Rollback
```bash
cd ~/homebase
git checkout HEAD~1
cd frontend && npm run build
pm2 restart homebase
```

## Database

SQLite database at `backend/homebase.db`:
- servers table
- users table
- sessions table
- agent_heartbeats table

### Backup
```bash
cp ~/homebase/backend/homebase.db ~/backups/homebase-$(date +%Y%m%d).db
```

## Monitoring

Homebase monitors:
- 5 active servers (Talos, Agents, Rize-Apps, Demos, Vector)
- 4 AI agents (David Bishop, Apex, Aegis, Sentinel)
- SSH connectivity
- Service health

## Troubleshooting

### Port already in use
```bash
lsof -i :8000
kill -9 <PID>
pm2 restart homebase
```

### Database locked
```bash
pm2 stop homebase
cp backend/homebase.db backend/homebase.db.bak
pm2 start homebase
```

### Frontend not updating
```bash
cd ~/homebase/frontend
rm -rf dist node_modules
npm install
npm run build
pm2 restart homebase
```
