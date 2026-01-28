# Homebase Project Plan

## Vision

Homebase evolves from a simple infrastructure dashboard into the **Central Command** for all Rize Technologies infrastructure. It will absorb monitoring (previously in Relay's Pulse), manage credentials centrally, auto-discover new projects, and eventually trigger automated fixes via Claude Code or Relay.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     HOMEBASE - Central Command              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Servers    │  │   Security   │  │  Discovery   │      │
│  │  Dashboard   │  │  Monitoring  │  │    Engine    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Key      │  │     Log      │  │   Alerting   │      │
│  │  Management  │  │  Aggregation │  │   (Future)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ SSH / API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure                           │
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ Cobalt  │ │  Relay  │ │ BPS AI  │ │ Context │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │Dockyard │ │ Vector  │ │ Claude  │ │ Hyper-V │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Roadmap

### v0.1.0 - Core Dashboard ✅ (Complete)
- Real-time server monitoring
- System metrics (CPU, memory, disk, uptime)
- React/Tailwind frontend
- PM2 + Cloudflare deployment

### v0.2.0 - Central Command Foundation ✅ (Current)
- Project auto-discovery
- Security monitoring
- Encrypted credential management
- Log aggregation
- Multi-page frontend

### v0.3.0 - Enhanced Monitoring (Next)
- Historical metrics in database
- Time-series charts (24h, 7d)
- Email/Slack alerts
- Uptime tracking

### v0.4.0 - Automation
- GitHub integration
- One-click deployments
- Scheduled security scans
- Integration with Claude Code

### v0.5.0 - Advanced
- Role-based access control
- Mobile-responsive design
- Credential management UI
- Log search/filter

### v1.0.0 - Production Ready
- PostgreSQL migration
- Full test coverage
- Documentation complete
- Security audit passed

## Integration Points

### Relay
- Pulse monitoring absorbed into Homebase
- Can trigger Relay for complex orchestration tasks
- Shares server matrix

### Claude Code
- Can trigger automated fixes
- Receives alerts for issues
- Manages deployment workflows

### GitHub
- Track commits per project
- Trigger deployments on merge
- Show PR/issue counts

## Database Schema

```sql
-- Servers
CREATE TABLE servers (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    ip TEXT,
    username TEXT,
    os TEXT,
    web_url TEXT,
    ssh_url TEXT
);

-- Discovered Projects
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT,
    server_id INTEGER,
    path TEXT,
    version TEXT,
    description TEXT,
    has_git BOOLEAN,
    git_remote TEXT
);

-- Encrypted Credentials
CREATE TABLE credentials (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    type TEXT, -- ssh_key, api_key, password, token
    encrypted_value TEXT,
    server_id INTEGER,
    last_rotated_at TIMESTAMP
);

-- Access Logs
CREATE TABLE credential_access_logs (
    id INTEGER PRIMARY KEY,
    credential_id INTEGER,
    action TEXT,
    user TEXT,
    created_at TIMESTAMP
);

-- Security Scans
CREATE TABLE security_scans (
    id INTEGER PRIMARY KEY,
    server_id INTEGER,
    status TEXT,
    total_updates INTEGER,
    critical_updates INTEGER,
    failed_auth_count INTEGER,
    scanned_at TIMESTAMP
);

-- Log Snapshots
CREATE TABLE log_snapshots (
    id INTEGER PRIMARY KEY,
    server_id INTEGER,
    service TEXT,
    log_content TEXT,
    error_count INTEGER,
    captured_at TIMESTAMP
);
```

## Security Considerations

1. **Credential Encryption**: All secrets encrypted with Fernet
2. **Key Storage**: Encryption keys stored with chmod 600
3. **Access Logging**: All credential access logged
4. **SSH Only**: No password auth, keys only
5. **Network**: Internal network only + Cloudflare tunnel

## Success Metrics

- All 7+ servers monitored in real-time
- < 30s latency for metric updates
- 100% uptime for Homebase itself
- Zero credential leaks
- < 1 minute to discover new projects
