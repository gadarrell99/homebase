# RIZE DEVELOPMENT WORKFLOW — ENFORCEMENT SPEC
# This document defines the mandatory rules for all development on Rize projects.
# Referenced by: CLAUDE.md (all projects), Sentinel (audit), Cortex (monitoring)
# Location: ~/homebase/WORKFLOW-SPEC.md on .245, synced to all servers
# Last Updated: 2026-02-10

---

## THE 6-PHASE WORKFLOW

Every piece of work flows through these phases in order. No shortcuts.

### Phase 1: Feedback Intake
```
CEO feedback → Gitea issue → Homebase dashboard updates
```
- ALL feedback becomes a Gitea issue. No exceptions.
- Every issue gets: labels (P0/P1/P2), milestone (if deadline), description
- Tags: ceo-feedback, bug, feature, security, demo-blocker, ui-ux
- Homebase /requirements reflects new issue within 5 minutes

### Phase 2: Session Start
```
Read CLAUDE.md → Fetch Gitea issues → Read REQUIREMENTS.md → Verify current state
```
- Claude Code reads CLAUDE.md FIRST
- Fetches open issues from Gitea API (source of truth)
- Reads REQUIREMENTS.md (backup reference)
- Verifies current server state via SSH before making changes
- Sentinel logs session start

### Phase 3: Development (per issue)
```
Pick P0 issue → Implement fix → Run Playwright test → Pass? → Commit + close
```
- One issue at a time
- P0 before P1, always
- Playwright test MUST pass before marking done
- Commit message MUST reference issue: "Fixes #N"
- Push to Gitea immediately after commit
- Update REQUIREMENTS.md as backup

### Phase 4: CI Verification
```
Push → Gitea Actions → Full Playwright suite → Post results → Check regressions
```
- Every push triggers full test suite (not just the changed test)
- Results posted as comments on related issues
- Regressions auto-reopen affected issues
- Cortex alerts on regression

### Phase 5: Session Close
```
Full test suite → Update docs → Final push → Email CEO → Sentinel log
```
- Run complete Playwright suite, save TEST-RESULTS.txt
- Update: README.md, TODO.md, CHANGELOG.md, REQUIREMENTS.md
- Push everything to Gitea
- Email completion report to artiedarrell@gmail.com
- Sentinel records full session audit

### Phase 6: Continuous Monitoring (24/7)
```
Homebase refreshes → Cortex watches → Sentinel audits → David reports
```
- Homebase reads Gitea API every 5 minutes
- Cortex alerts on: stale P0 (>48h), approaching deadlines, service outages
- Sentinel flags: issues closed without test evidence, commits without issue refs
- David's daily report includes project completion percentages

---

## ENFORCEMENT RULES

### MUST Rules (violation = audit flag + CEO alert)

| ID | Rule | Enforced By | Check |
|----|------|-------------|-------|
| M1 | Read CLAUDE.md before any work | CLAUDE.md | First action in session |
| M2 | Fetch Gitea open issues before coding | CLAUDE.md | API call logged in session |
| M3 | P0 issues before P1 — no exceptions | CLAUDE.md | Issue priority checked |
| M4 | Playwright test MUST pass before marking DONE | Playwright + CLAUDE.md | Test output in commit/comment |
| M5 | Commit message references issue number | Git hooks | Regex: /Fixes? #\d+/ |
| M6 | Push to Gitea after every fix | CLAUDE.md | Gitea commit log |
| M7 | Email session report to CEO | CLAUDE.md + send-email.py | Email sent |
| M8 | Never reboot Talos during active session | CLAUDE.md | Talos uptime check |
| M9 | Syntax check before service restart | CLAUDE.md | No crash-restart cycles |
| M10 | Verify current state before changes | CLAUDE.md | SSH state check in session |
| M11 | CEO approval for write operations on agents | Sentinel | Approval logged |

### SHOULD Rules (violation = warning, not block)

| ID | Rule | Enforced By | Check |
|----|------|-------------|-------|
| S1 | Update docs after every task | CLAUDE.md | Doc timestamps |
| S2 | One change per commit | Git practice | Commit size |
| S3 | Keep REQUIREMENTS.md in sync with Gitea | CLAUDE.md | Diff check |
| S4 | Use rollback plan before risky changes | CLAUDE.md | Backup before edit |

### AUTO Rules (system handles it, no human action)

| ID | Rule | Enforced By | Check |
|----|------|-------------|-------|
| A1 | CI runs full test suite on push | Gitea Actions | Workflow trigger |
| A2 | Stale P0 alert after 48 hours | Cortex | Issue age monitor |
| A3 | Homebase refreshes every 5 min | Crontab | Cache timestamp |
| A4 | Regression auto-reopens issues | Gitea Actions | Test result → issue state |
| A5 | Sentinel logs all agent actions | Sentinel | Heartbeat + audit trail |
| A6 | David daily report includes status | David Bishop | Scheduled email |

---

## SYSTEM RESPONSIBILITIES

### Gitea (Source of Truth)
- Stores all project code (5 repos)
- Tracks all issues (requirements, bugs, features)
- Runs CI via Gitea Actions
- Auto-closes issues on "Fixes #N" commits
- Provides API for Homebase, Claude Code, Cortex
- URL: gitea.rize.bm | Port: 3100 | Server: .245

### Homebase (CEO Dashboard)
- /requirements page: real-time view of all project status
- Reads from Gitea API (not SSH parsing)
- Pre-cached data, 5-minute refresh
- Links to Gitea issues for detail
- Links to Plane for sprint/roadmap view
- URL: homebase.rize.bm | Port: 8000 | Server: .245

### Claude Code (Development Engine)
- Runs on Talos (.237)
- SSHs to project servers (.245, .246) for actual work
- Reads tasks from Gitea, executes fixes, pushes results
- MUST follow Phase 2-5 workflow every session
- Agent teams mode for parallelizable work

### Playwright (Verification Layer)
- Test file per project (helios-tests.spec.js, bps-tests.spec.js, etc.)
- One test per requirement (REQ-XXX maps to test "REQ-XXX")
- Runs locally (Claude Code) and in CI (Gitea Actions)
- Results gate issue closure — no pass, no close
- Catches regressions via full suite on push

### Sentinel (Audit & Security)
- Logs every agent action
- Tracks: session starts/ends, issues worked, commits made, tests run
- Flags violations: closed without test, commits without issue ref
- Security monitoring: guardrail breaches, protocol violations
- Reports to: Homebase /sentinel page, aidev@rize.bm

### Cortex (Operations Monitor)
- Fleet maintenance: service health, heartbeats
- Issue monitoring: stale P0 alerts, deadline warnings
- Regression alerts when CI detects failures
- Feeds data to David Bishop for daily reports
- Teams notifications to #trinity-ops

### Plane (Project Management — Optional)
- Sprint planning with cycles
- Cross-project modules (Demo Readiness, Security, Infrastructure)
- Roadmap view for strategic planning
- Syncs from Gitea via webhooks
- CEO-level visibility into sprint progress
- URL: plane.rize.bm | Port: 3200 | Server: .245

### David Bishop (Sales Intelligence)
- Daily report includes project completion %
- Flags: demos approaching deadline with open P0s
- Sales pipeline tied to demo readiness

---

## PROJECT MATRIX

| Project | Repo | Server | Port | Deadline | Tunnel |
|---------|------|--------|------|----------|--------|
| Helios | rize/helios | .246 | 3005 | Feb 17 | helios.rize.bm |
| BPS AI | rize/bps-ai | .246 | 3000 | Feb 20 | bpsai.rize.bm |
| Homebase | rize/homebase | .245 | 8000 | — | homebase.rize.bm |
| BEST Shipping | rize/best-shipping | .246 | — | TBD | bestshipping.rize.bm |
| Premier EMR | rize/premier-emr | .246 | — | TBD | premieremr.rize.bm |

---

## SENTINEL AUDIT CHECKS

Sentinel runs these checks continuously and flags violations:

### Session Integrity
- [ ] CLAUDE.md read at session start (check file access timestamp)
- [ ] Gitea API called before first code change (check API logs)
- [ ] P0 issues worked before P1 (check issue priority vs order worked)
- [ ] All commits reference issue numbers (regex check on git log)

### Verification Integrity
- [ ] Every closed issue has Playwright test evidence (check comments)
- [ ] No issues closed manually without test (check close method)
- [ ] CI ran on every push (check Gitea Actions log)
- [ ] No regressions in last 24 hours (check test result trend)

### Documentation Integrity
- [ ] REQUIREMENTS.md matches Gitea issue states (diff check)
- [ ] README.md updated within last 7 days (file timestamp)
- [ ] CHANGELOG.md has entry for last session (content check)
- [ ] TEST-RESULTS.txt exists and is < 24h old (file check)

### Infrastructure Integrity
- [ ] All 5 services responding (health check endpoints)
- [ ] Cloudflare tunnels active (tunnel status check)
- [ ] Gitea accessible (API version check)
- [ ] Homebase /requirements returns data (API check)
- [ ] Crontab running requirements refresh (process check)

---

## CORTEX MONITORING RULES

```yaml
monitors:
  stale_p0:
    check: "Gitea P0 issues open > 48 hours"
    action: "Teams alert to #trinity-ops"
    frequency: "every 6 hours"

  deadline_warning:
    check: "Milestone deadline within 3 days AND open P0 issues > 0"
    action: "Teams alert + email to CEO"
    frequency: "daily"

  regression:
    check: "CI test count decreased from last run"
    action: "Teams alert + reopen affected issues"
    frequency: "on every CI run"

  service_health:
    check: "Project URL returns non-200"
    action: "Teams alert + Sentinel log"
    frequency: "every 5 minutes"

  session_compliance:
    check: "Session ended without email report"
    action: "Flag in Sentinel audit"
    frequency: "on session close"
```

---

## VERSION HISTORY

| Date | Version | Change |
|------|---------|--------|
| 2026-02-10 | 1.0 | Initial workflow spec — Tier 1+2+3 system |
| 2026-02-11 | 1.1 | Added GitHub + Gitea dual-push workflow |

---

## GIT DUAL-PUSH: GITHUB + GITEA

### Rule: Every push goes to BOTH remotes

All projects maintain two git remotes:
- `origin` → GitHub (gadarrell99 or Rize-Technologies org)
- `gitea` → Gitea (rize org on .245:3100)

### Push command (in every CLAUDE.md):
```bash
git push origin main && git push gitea main
```

Or set up a combined push (one command, both remotes):
```bash
git remote set-url --add --push origin http://oauth2:TOKEN@192.168.65.245:3100/rize/REPO.git
# Now "git push origin" pushes to BOTH GitHub and Gitea
```

### Why both:
- **GitHub**: External backup, collaboration, CI/CD
- **Gitea**: Internal issue tracking, Homebase integration, Claude Code workflow

### Sync direction:
- Claude Code pushes to both on every commit
- GitHub is the backup, Gitea is the operational source of truth
- If out of sync: Gitea wins (it has the issue linkage)

### Repository map:
| Project | GitHub Repo | Gitea Repo | Server |
|---------|-------------|------------|--------|
| Helios | Rize-Technologies/helios-ai | rize/helios | .246 |
| BPS AI | gadarrell99/bps-ai | rize/bps-ai | .246 |
| Homebase | gadarrell99/homebase | rize/homebase | .245 |
| BEST Shipping | gadarrell99/best | rize/best-shipping | .246 |
| Premier EMR | gadarrell99/premier-emr | rize/premier-emr | .246 |
| Cortex | gadarrell99/cortex | rize/cortex | .241 |
| David Bishop | gadarrell99/david-bishop | rize/david-bishop | .241 |
| Apex | gadarrell99/apex | rize/apex | .241 |
| Aegis | gadarrell99/aegis | rize/aegis | .241 |
| Sentinel | gadarrell99/sentinel | rize/sentinel | .245 |
| Talos | — | rize/talos | .237 |
| Vector | gadarrell99/bet-vector | rize/vector | .249 |
