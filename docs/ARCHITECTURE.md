# Homebase Architecture

## System Overview

Homebase is an infrastructure monitoring dashboard that provides real-time visibility into Rize Technologies server fleet. It uses SSH-based metrics collection and a modern React frontend.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
│                                                                              │
│                         ┌──────────────────┐                                 │
│                         │   Cloudflare     │                                 │
│                         │   Tunnel         │                                 │
│                         │   (homebase.     │                                 │
│                         │    rize.bm)      │                                 │
│                         └────────┬─────────┘                                 │
└──────────────────────────────────┼───────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RIZE-APPS SERVER (192.168.65.245)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                           PM2 Process Manager                        │    │
│  │  ┌─────────────────┐    ┌────────────────────────────────────────┐  │    │
│  │  │   homebase-api  │    │           homebase-frontend            │  │    │
│  │  │   (FastAPI)     │    │           (Vite/React)                 │  │    │
│  │  │   Port 8000     │    │           Static via API               │  │    │
│  │  └────────┬────────┘    └────────────────────────────────────────┘  │    │
│  └───────────┼──────────────────────────────────────────────────────────┘    │
│              │                                                               │
│              │ asyncssh                                                      │
│              ▼                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              │ SSH (port 22)
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MONITORED SERVERS                                  │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Rize-Apps   │  │             │  │   BPS AI    │  │ Context Hub │        │
│  │ .245        │  │ ----        │  │ .246        │  │ .247        │        │
│  │ (self)      │  │             │  │             │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Dockyard   │  │   Vector    │  │ Claude Code │  │  Hyper-V    │        │
│  │ .252        │  │ .249        │  │ .245        │  │ .253        │        │
│  │             │  │             │  │             │  │ (Windows)   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Backend (FastAPI)

**Location:** `backend/main.py`

The backend is a single-file FastAPI application responsible for:

1. **SSH-Based Metrics Collection**
   - Uses `asyncssh` for non-blocking SSH connections
   - Parallel collection from all servers
   - 5-second connection timeout per server

2. **Metrics Collected**
   - Uptime (`uptime -p`)
   - Memory usage (`free -m`)
   - Disk usage (`df -BG /`)
   - CPU percentage (`top -bn1`)

3. **API Endpoints**
   | Endpoint | Method | Description |
   |----------|--------|-------------|
   | `/api/health` | GET | Health check with timestamp |
   | `/api/servers` | GET | All servers with current metrics |
   | `/*` | GET | SPA fallback (serves frontend) |

4. **Static File Serving**
   - Serves built React app from `frontend/dist`
   - SPA routing handled via catch-all route

### Frontend (React + Vite)

**Location:** `frontend/src/`

Built with:
- React 18 with hooks
- Vite for build tooling
- Tailwind CSS for styling

**Features:**
- Server status cards with color-coded indicators
- Real-time metrics display (CPU, Memory, Disk)
- Auto-refresh every 30 seconds
- Quick-access links for Web UI and SSH
- Dark theme design

### Process Management (PM2)

**Configuration:** `ecosystem.config.cjs`

PM2 manages:
- `homebase-api`: Uvicorn server on port 8000
- `homebase-frontend`: Build artifacts served by API

### Network Architecture

**External Access:**
- Cloudflare Tunnel terminates at Rize-Apps:8000
- Domain: `homebase.rize.bm`

**Internal Communication:**
- SSH key-based authentication between servers
- Private network (192.168.65.0/24)

## Data Flow

```
User Request → Cloudflare → Rize-Apps:8000 → FastAPI
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │ /api/servers  │
                                    └───────┬───────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
                    ▼                       ▼                       ▼
            ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
            │ SSH Server 1 │        │ SSH Server 2 │        │ SSH Server N │
            │ (async)      │        │ (async)      │        │ (async)      │
            └──────────────┘        └──────────────┘        └──────────────┘
                    │                       │                       │
                    └───────────────────────┼───────────────────────┘
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │  Aggregate    │
                                    │  Results      │
                                    └───────┬───────┘
                                            │
                                            ▼
                                    JSON Response → Frontend → UI Update
```

## Security Considerations

1. **SSH Keys**: Pre-distributed SSH keys for server access
2. **CORS**: Currently allows all origins (internal use)
3. **No Auth**: Dashboard is public (relies on Cloudflare Access if needed)
4. **Known Hosts**: Disabled for flexibility (`known_hosts=None`)

## Scalability

- **Horizontal**: Add servers to `SERVERS` list in `main.py`
- **Caching**: Consider Redis for metrics caching
- **Rate Limiting**: Add if exposed publicly

## Directory Structure

```
homebase/
├── backend/
│   ├── main.py          # FastAPI application
│   ├── requirements.txt # Python dependencies
│   └── venv/            # Virtual environment
├── frontend/
│   ├── src/             # React source
│   ├── dist/            # Built static files
│   ├── package.json     # Node dependencies
│   └── vite.config.js   # Vite configuration
├── docs/
│   ├── API.md           # API documentation
│   ├── ARCHITECTURE.md  # This file
│   └── DEPLOYMENT.md    # Deployment guide
├── ecosystem.config.cjs # PM2 configuration
├── README.md            # Project overview
├── CHANGELOG.md         # Version history
└── TODO.md              # Planned features
```
