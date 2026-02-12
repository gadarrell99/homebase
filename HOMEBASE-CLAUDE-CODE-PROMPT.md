# HOMEBASE WORK SESSION — REQUIREMENTS-DRIVEN

Read ~/CLAUDE.md first. Hospital-grade QA.

## MANDATORY WORKFLOW

1. READ ~/homebase/HOMEBASE-REQUIREMENTS.md — this is your task list
2. Work through OPEN items in P0 → P1 order
3. For EACH item you complete:
   a. Run the matching Playwright test
   b. If test PASSES → update HOMEBASE-REQUIREMENTS.md status to DONE with evidence
   c. If test FAILS → fix the issue and re-test
   d. Do NOT mark DONE without a passing test
4. After all work: run full test suite and report results
5. Email summary to artiedarrell@gmail.com

## SETUP (run once if not already done)

```bash
ssh rizeadmin@192.168.65.245 << 'EOF'
cd ~/homebase
if [ ! -d node_modules/@playwright ]; then
  npm init -y 2>/dev/null
  npm install @playwright/test
  npx playwright install chromium
  npx playwright install-deps chromium
fi
EOF
```

## COPY TEST FILE TO SERVER

```bash
scp ~/uploads/homebase-tests.spec.js rizeadmin@192.168.65.245:~/homebase/
```

## AFTER EACH FIX

```bash
ssh rizeadmin@192.168.65.245 << 'EOF'
cd ~/homebase
USE_LOCAL=1 HB_URL=http://localhost:8000 npx playwright test homebase-tests.spec.js -g "REQ-HXXX" --reporter=list
EOF
```

## AFTER ALL FIXES

```bash
ssh rizeadmin@192.168.65.245 << 'EOF'
cd ~/homebase
USE_LOCAL=1 HB_URL=http://localhost:8000 npx playwright test homebase-tests.spec.js --reporter=list 2>&1 | tee ~/homebase/TEST-RESULTS.txt
echo "=== SUMMARY ==="
grep -c "passed" ~/homebase/TEST-RESULTS.txt
grep -c "failed" ~/homebase/TEST-RESULTS.txt
EOF
```

## CRITICAL NAV BAR FIX (REQ-H001, H002, H003)

The nav bar is the #1 priority. It must be IDENTICAL HTML across all 16 pages:
index, servers, projects, agents, metrics, sentinel, security, settings,
research, backups, credentials, server-detail, project-detail, agent-detail

Strategy: Extract nav into a single shared component/include, then reference from all pages.
Do NOT copy-paste nav HTML 16 times — use a template or JS include.

## COMPLETION CRITERIA

- Zero OPEN P0 items in HOMEBASE-REQUIREMENTS.md
- Playwright suite passes all P0 tests
- REQUIREMENTS.md updated with evidence for every DONE item

## RULES
- Do NOT skip requirements
- Do NOT mark DONE without test evidence
- Do NOT work on P1 until ALL P0 items are DONE
- Update HOMEBASE-REQUIREMENTS.md after EVERY fix
- Talos (.237) is never rebooted during active sessions
