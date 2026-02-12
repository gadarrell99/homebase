# Sentinel Runbook

## Emergency Procedures

### Agent Crashes and Doesn't Auto-Restart
1. Check Sentinel dashboard for agent status
2. SSH to Agents server: ssh agents@192.168.65.241
3. Check service status: systemctl status {agent_name} --user
4. Check logs: journalctl --user -u {agent_name} -n 50
5. Restart manually: systemctl restart {agent_name} --user
6. If fails, check disk space and memory on server
7. Notify CEO if agent stays down >5 minutes

### PII Detected in Agent Communication
1. Sentinel auto-logs PII detection events
2. Check audit log: /api/sentinel/audit-log?action_type=pii_scan
3. Review the flagged content in pii_scan_log table
4. Determine if legitimate (customer data) or leak
5. If leak: kill agent immediately, investigate source
6. Document incident in audit log

### Agent Enters Restart Loop (3+ restarts in 10 min)
1. Sentinel detects pattern and raises critical alert
2. Check restart_log table for patterns
3. Review logs for root cause (memory, API failures, etc.)
4. Temporary fix: increase restart delay
5. Permanent fix: resolve underlying issue
6. Consider kill switch if causing cascading issues

### Unauthorized Write Operation Attempted
1. Guardrail triggers and blocks operation
2. Check guardrail_triggers table for details
3. Review agent config for permission levels
4. If legitimate need: update guardrail_rules
5. If attack: kill agent, investigate, report

### CEO Approval Gate Triggered
1. Agent requests action requiring CEO approval
2. Email sent to artiedarrell@gmail.com
3. Review action details in Sentinel dashboard
4. Approve: POST /api/sentinel/alerts/{id}/acknowledge
5. Deny: No action needed, request expires in 24h

## Monitoring Checklist

### Daily
- [ ] Check Sentinel overview for alerts
- [ ] Verify all agents show healthy heartbeats
- [ ] Review guardrail triggers (if any)

### Weekly
- [ ] Audit log review for anomalies
- [ ] Resource trends (CPU, memory, disk)
- [ ] Restart frequency analysis

### Monthly
- [ ] Full audit log export
- [ ] Guardrail rule review
- [ ] Agent permission audit

## Contacts
- CEO: artiedarrell@gmail.com
- Tech Lead: icharif@rize.bm
- Finance: mocoy@rize.bm
