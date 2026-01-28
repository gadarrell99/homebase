# Homebase API

Base URL: `https://homebase.rize.bm`

## Endpoints

### GET /api/servers

Returns all monitored servers with current status and metrics.

**Response:**
```json
{
  "servers": [
    {
      "name": "Relay",
      "ip": "192.168.65.248",
      "status": "online",
      "uptime": "2 weeks, 5 days",
      "memory_used": 810,
      "memory_total": 3844,
      "disk_used": 11,
      "disk_total": 28,
      "cpu_percent": 2.2,
      "web_url": "relay.rize.bm",
      "ssh_url": "relay-ssh.rize.bm"
    }
  ],
  "timestamp": 1769559422.34
}
```

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": 1769559422.34
}
```
