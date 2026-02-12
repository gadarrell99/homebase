# Sentinel API Reference

## Overview
Sentinel provides agent oversight, security monitoring, and audit logging for the Rize AI Agent fleet.

## Base URL
http://192.168.65.245:8000/api/sentinel

## Endpoints

### GET /api/sentinel/overview
Get overview statistics for the Sentinel dashboard.
Returns: agents_healthy, agents_degraded, requests_24h, alerts counts

### GET /api/sentinel/agents
Get detailed status for all registered agents.
Returns: agent list with id, name, status, last_heartbeat, uptime_seconds, channels

### GET /api/sentinel/alerts
Get security alerts and warnings.
Query params: limit (int), severity (str)

### GET /api/sentinel/audit-log
Get audit log entries for agent actions.
Query params: limit (int), agent_id (str), action_type (str)

### GET /api/sentinel/crons
Get cron job status across the fleet.

### GET /api/sentinel/resources
Get resource usage (CPU, memory, disk) for all servers.

### POST /api/sentinel/restart/{agent_name}
Trigger an agent restart via SSH.
Request body: {"confirm": true}

### POST /api/sentinel/alerts/{alert_id}/acknowledge
Acknowledge a security alert.
Request body: {"acknowledged_by": "user", "notes": "optional"}

## Authentication
Currently no authentication required (internal network only).

## Error Responses
All endpoints return JSON errors: {"error": "Description"}
