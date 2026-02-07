# Homebase Deployment Guide

## Prerequisites

- Ubuntu 22.04+ server
- Python 3.11+
- Node.js 18+
- PM2 process manager
- SSH key access to all monitored servers
- Cloudflare Tunnel (for external access)

## Initial Server Setup

### 1. System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install Node.js (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2
sudo npm install -g pm2
```

### 2. Clone Repository

```bash
cd ~
git clone git@github.com:artieRizmo/homebase.git
cd homebase
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi, asyncssh, uvicorn; print(OK)"
```

### 4. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Build for production
npm run build

# Verify build
ls -la dist/
```

### 5. SSH Key Distribution

Ensure the cobaltadmin user has SSH access to all servers:

```bash
# Generate SSH key if needed
ssh-keygen -t ed25519 -C "homebase@cobalt"

# Copy to each server
ssh-copy-id rizeadmin@192.168.65.245
ssh-copy-id relayadmin@192.168.65.248
ssh-copy-id bpsaiadmin@192.168.65.246
ssh-copy-id contextadmin@192.168.65.247
ssh-copy-id dockyardadmin@192.168.65.252
ssh-copy-id betadmin@192.168.65.249
ssh-copy-id claudedevadmin@192.168.65.245

# Test connections
for ip in 243 248 246 247 252 249 245; do
  echo "Testing 192.168.65.$ip..."
  ssh -o ConnectTimeout=5 192.168.65.$ip "hostname"
done
```

## Starting Services

### Using PM2 (Recommended)

```bash
cd ~/homebase

# Start all services
pm2 start ecosystem.config.cjs

# Save PM2 configuration
pm2 save

# Enable startup on boot
pm2 startup
# Follow the printed command (sudo required)
```

### Manual Start (Development)

```bash
# Terminal 1: Backend
cd ~/homebase/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend (dev mode)
cd ~/homebase/frontend
npm run dev
```

## PM2 Commands Reference

```bash
# View status
pm2 status

# View logs
pm2 logs
pm2 logs homebase-api
pm2 logs homebase-api --lines 100

# Restart services
pm2 restart all
pm2 restart homebase-api

# Stop services
pm2 stop all

# Delete from PM2
pm2 delete all
```

## Cloudflare Tunnel Setup

### 1. Install cloudflared

```bash
curl -L https://pkg.cloudflare.com/cloudflared-stable-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
```

### 2. Authenticate

```bash
cloudflared tunnel login
```

### 3. Create Tunnel

```bash
cloudflared tunnel create homebase
```

### 4. Configure Tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /home/rizeadmin/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: homebase.rize.bm
    service: http://localhost:8000
  - service: http_status:404
```

### 5. Route DNS

```bash
cloudflared tunnel route dns homebase homebase.rize.bm
```

### 6. Run as Service

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

## Updating Homebase

### Standard Update

```bash
cd ~/homebase

# Pull latest changes
git pull origin main

# Update backend dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Rebuild frontend
cd ../frontend
npm install
npm run build

# Restart services
pm2 restart all
```

### Quick Backend-Only Update

```bash
cd ~/homebase
git pull origin main
pm2 restart homebase-api
```

### Quick Frontend-Only Update

```bash
cd ~/homebase/frontend
git pull origin main
npm run build
# No restart needed - static files are served directly
```

## Monitoring & Troubleshooting

### Check Service Status

```bash
# PM2 status
pm2 status

# Check if port is listening
ss -tlnp | grep 8000

# Test API endpoint
curl http://localhost:8000/api/health
```

### View Logs

```bash
# PM2 logs
pm2 logs --lines 50

# System logs
journalctl -u cloudflared -f
```

### Common Issues

#### 1. SSH Connection Timeouts

**Symptom:** Servers show as offline

**Solution:**
```bash
# Test SSH manually
ssh -v rizeadmin@192.168.65.245

# Check SSH key permissions
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

#### 2. Port Already in Use

**Symptom:** `Address already in use`

**Solution:**
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
pm2 delete homebase-api
sudo kill -9 <PID>
```

#### 3. Frontend Build Fails

**Symptom:** `npm run build` errors

**Solution:**
```bash
# Clean and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### 4. Python Import Errors

**Symptom:** `ModuleNotFoundError`

**Solution:**
```bash
# Ensure venv is activated
source ~/homebase/backend/venv/bin/activate
pip install -r requirements.txt
```

## Backup & Recovery

### Backup Configuration

```bash
# Backup PM2 config
pm2 save

# Backup Cloudflare credentials
cp -r ~/.cloudflared ~/cloudflared-backup
```

### Full Backup

```bash
tar -czvf homebase-backup-$(date +%Y%m%d).tar.gz \
  ~/homebase \
  ~/.cloudflared \
  --exclude=*/node_modules/* \
  --exclude=*/venv/* \
  --exclude=*/.git/*
```

### Recovery

```bash
# Restore from backup
tar -xzvf homebase-backup-YYYYMMDD.tar.gz -C ~

# Rebuild dependencies
cd ~/homebase/backend && source venv/bin/activate && pip install -r requirements.txt
cd ~/homebase/frontend && npm install && npm run build

# Start services
pm2 start ecosystem.config.cjs
```

## Adding New Servers

1. Edit `backend/main.py`
2. Add server to `SERVERS` list:
   ```python
   {"name": "NewServer", "ip": "192.168.65.XXX", "user": "admin", "web_url": "new.rize.bm", "ssh_url": "new-ssh.rize.bm"},
   ```
3. Ensure SSH key access:
   ```bash
   ssh-copy-id admin@192.168.65.XXX
   ```
4. Restart API:
   ```bash
   pm2 restart homebase-api
   ```

## Environment Variables

Currently no environment variables required. Future enhancements may include:

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | API listening port | 8000 |
| `SSH_TIMEOUT` | SSH connection timeout | 5 |
| `REFRESH_INTERVAL` | Frontend refresh rate (ms) | 30000 |
