# 🏠 RIZE INFRASTRUCTURE CHEAT SHEET
**Updated:** February 6, 2026 18:00 UTC
**Status:** 🟢 ALL SYSTEMS OPERATIONAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 FLEET OVERVIEW
| Metric | Count |
|--------|-------|
| Active Production VMs | 5 |
| Decommissioned VMs | 6 |
| Hyper-V Host | 1 |
| Total Endpoints Managed | 109 |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🖥️ ACTIVE SERVERS (5 + Hyper-V)

| Server | IP | User | RAM | Role | Services |
|--------|-----|------|-----|------|----------|
| Talos | .237 | talosadmin | 8GB | C2 Command | Claude Code, SSH gateway, Ollama |
| Agents | .241 | agents | 8GB | AI Agents | David Bishop, Treasurer, Watchman |
| Rize-Apps | .245 | rizeadmin | 16GB | Production | Homebase, Sentinel, Property Rize, Nexus, Dockyard WiFi, Relay, OpenHands, PostgreSQL |
| Demos | .246 | demos | 8GB | Demos | Best Shipping, BPS AI, Premier EMR, Helios |
| Vector | .249 | betadmin | 3GB | CRITICAL | BET Air Ambulance |
| Hyper-V | .253 | Administrator | Host | VM Host | Windows Server |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔗 SSH QUICK REFERENCE (from Talos)
```bash
ssh agents@192.168.65.241      # AI Agents (David, Treasurer, Watchman)
ssh rizeadmin@192.168.65.245   # Rize-Apps (Homebase, Property Rize, Nexus, etc)
ssh demos@192.168.65.246       # Demos (Best Shipping, BPS AI, EMR, Helios)
ssh betadmin@192.168.65.249    # Vector (BET Air Ambulance - CRITICAL)
```
Fallback Password: M00nshot2025!@#

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🌐 SERVICES & PORTS

### Rize-Apps (.245)
| Service | Port | Process | Status |
|---------|------|---------|--------|
| Homebase | 8000 | systemd/uvicorn | ✅ Production |
| Sentinel | 8000 | (part of Homebase) | ✅ Production |
| Property Rize | 8501 | Streamlit | ✅ Production |
| Nexus Frontend | 3002 | Nginx | ✅ Production |
| Nexus Backend | 3003 | Node | ✅ Production |
| Dockyard WiFi | 8080 | Docker | 🚧 Building |
| Dockyard Admin | 8081 | Docker | 🚧 Building |
| Relay | 8888 | systemd/uvicorn | ✅ Production |
| OpenHands | 3000 | Docker | ✅ Running |
| PostgreSQL | 5432 | system | ✅ Running |

### Demos (.246)
| Service | Port | Process | Status |
|---------|------|---------|--------|
| BPS AI | 3000 | PM2/Node | ✅ Demo |
| Best Shipping Frontend | 3001 | PM2/Node | ✅ Demo |
| Best Shipping API | 8001 | PM2/Python | ✅ Demo |
| Premier EMR Frontend | 3004 | Docker | ✅ Running |
| Premier EMR API | 5004 | Docker | ✅ Running |
| Helios | 3005 | Docker | 🚧 Building |

### Agents (.241)
| Service | Port | Process | Status |
|---------|------|---------|--------|
| OpenClaw Gateway | 7070 | user/david | ✅ Production |
| David Bishop | 18789 | OpenClaw | ✅ Production |
| Teams Webhook | 3978 | OpenClaw | ✅ Production |
| Treasurer | 9002 | systemd | 📋 Mock |
| Watchman | 9003 | systemd | 📋 Mock |
| Ollama | 11434 | systemd | ✅ Running |

### Vector (.249) ⚠️ CRITICAL
| Service | Port | Process | Status |
|---------|------|---------|--------|
| BET Dispatch | 8000 | PM2 | ✅ Production |
| BET Frontend | 5173 | Vite | ✅ Running |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🤖 AI AGENTS

| Agent | Mode | Server | Port | Channels |
|-------|------|--------|------|----------|
| David Bishop | Live | .241 | 18789 | Teams, Telegram, Email |
| Treasurer | Mock (read-only) | .241 | 9002 | Internal |
| Watchman | Mock (silent) | .241 | 9003 | Internal |
| Sentinel | Active (oversight) | .245 | 8000 | Dashboard |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🌍 WEB DOMAINS & TUNNELS

### Rize-Apps (.245) - Tunnel: 5d69d616-005b-455d-8ab0-18d7533b9487
| Domain | Port | Status |
|--------|------|--------|
| homebase.rize.bm | 8000 | ✅ |
| property.rize.bm | 8501 | ✅ |
| nexus.rize.bm | 3002 | ✅ |
| relay.rize.bm | 8888 | ✅ |
| dockyardwifi.rize.bm | 8080 | ✅ |
| dockyard-admin.rize.bm | 8081 | ✅ |
| openhands.rize.bm | 3000 | ✅ |
| rize-apps-ssh.rize.bm | 22 | ✅ |

### Demos (.246) - Tunnel: ae68edab-703a-43ff-a9b3-a6c32ba75054
| Domain | Port | Status |
|--------|------|--------|
| bestshipping.rize.bm | 3001 | ✅ |
| bestshipping-api.rize.bm | 8001 | ✅ |
| bpsai.rize.bm | 3000 | ✅ |
| emr.rize.bm | 3004 | ✅ |
| emr-api.rize.bm | 5004 | ✅ |
| helios.rize.bm | 3005 | ✅ |

### Other Servers
| Domain | Server | Tunnel UUID |
|--------|--------|-------------|
| davidbot.rize.bm | .241 | 23740853-4b98-416f-a2ac-871895f60bde |
| talos-ssh.rize.bm | .237 | 84bd4915-1cf4-42ec-9c9b-e384995a4197 |
| vector.rize.bm | .249 | 99789829-9d9a-4fa6-b784-48037490bdbe |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔐 DEMO CREDENTIALS

### Best Shipping
- Demo: cornell@bestshipping.bm / demo2026
- Admin: admin@bestshipping.bm / admin2026

### BPS AI
- Demo: rizeadmin@bps.bm / BPSDemo2026!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🗑️ DECOMMISSIONED SERVERS (Still Powered On)

| IP | Old Name | Old User | Migrated To |
|----|----------|----------|-------------|
| .239 | Premier-EMR | emradmin | .246 |
| .240 | Helios | heliosdev | .246 |
| .243 | Cobalt | cobaltadmin | .245 |
| .247 | Nexus | nexusadmin | .245 |
| .248 | Relay | relayadmin | .245 |
| .252 | Dockyard | dockyardadmin | .245 |

**Action Required:** Shutdown via Hyper-V console

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ⚠️ PENDING WORK

1. Shutdown 6 decommissioned servers via Hyper-V
2. SSH hardening (disable password auth fleet-wide)
3. Monitor .246 disk usage (currently 86%)
4. Dockyard WiFi launch (Feb 28 target)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
