"""
SENTINEL PIPELINE MONITOR — Watches the Build & Audit Pipeline
Rize Technology Group — Homebase Sentinel Extension

Cortex OWNS execution. Sentinel OWNS review.
This module monitors the health of the build/audit pipeline itself.

WHAT IT WATCHES:
  - Cortex reachability (:9100)
  - Audit freshness (last report < 36 hours old)
  - Manifest freshness (fleet-manifest.json < 36 hours old)
  - Learning log activity (updated within 7 days)
  - Compile regressions (any failures in latest audit)
  - Homebase API health (/api/infrastructure responding)

INTEGRATION:
  1. Copy to ~/homebase/backend/services/ on .245
  2. Import in sentinel.py: from services.pipeline_monitor import PipelineMonitor
  3. Add to Sentinel's check cycle (runs every 30 min or on-demand)

ALERTS:
  - CRITICAL: Cortex down, audit pipeline broken
  - WARNING: Stale audit/manifest, compile failures
  - INFO: Learning log inactive
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

CORTEX_URL = "http://192.168.65.237:9100"
HOMEBASE_URL = "http://192.168.65.245:8000"

# Thresholds
AUDIT_STALE_HOURS = 36        # Alert if no audit in this many hours
MANIFEST_STALE_HOURS = 36     # Alert if manifest older than this
LEARNING_LOG_STALE_DAYS = 7   # Warn if learning log unchanged
MAX_COMPILE_FAILURES = 0      # Alert on any compile failures


class PipelineMonitor:
    """Monitors the build/audit pipeline health for Sentinel."""

    def __init__(self):
        self.findings = []

    def run_all_checks(self) -> Dict:
        """Run all pipeline health checks. Returns structured report."""
        self.findings = []
        now = datetime.now(timezone.utc)

        self._check_cortex_health()
        self._check_audit_freshness(now)
        self._check_manifest_freshness(now)
        self._check_learning_log_activity(now)
        self._check_compile_regressions()
        self._check_homebase_api()

        # Aggregate
        criticals = [f for f in self.findings if f["severity"] == "critical"]
        warnings = [f for f in self.findings if f["severity"] == "warning"]
        infos = [f for f in self.findings if f["severity"] == "info"]

        status = "healthy"
        if criticals:
            status = "critical"
        elif warnings:
            status = "degraded"

        return {
            "timestamp": now.isoformat(),
            "monitor": "pipeline",
            "status": status,
            "findings": self.findings,
            "summary": {
                "total_checks": len(self.findings),
                "critical": len(criticals),
                "warning": len(warnings),
                "info": len(infos),
                "healthy": len([f for f in self.findings if f["severity"] == "ok"]),
            },
        }

    def _add_finding(self, check: str, severity: str, message: str, detail: str = ""):
        self.findings.append({
            "check": check,
            "severity": severity,  # ok | info | warning | critical
            "message": message,
            "detail": detail,
        })

    # ═══════════════════════════════════════════════════════════
    # Individual Checks
    # ═══════════════════════════════════════════════════════════

    def _check_cortex_health(self):
        """Is Cortex reachable and responding?"""
        if not HAS_REQUESTS:
            self._add_finding("cortex_health", "warning",
                              "Cannot check Cortex — requests library not installed")
            return

        try:
            resp = requests.get(f"{CORTEX_URL}/health", timeout=5)
            if resp.status_code == 200:
                self._add_finding("cortex_health", "ok", "Cortex is healthy")
            else:
                self._add_finding("cortex_health", "warning",
                                  f"Cortex returned HTTP {resp.status_code}",
                                  resp.text[:200])
        except requests.ConnectionError:
            self._add_finding("cortex_health", "critical",
                              "Cortex is UNREACHABLE on :9100",
                              "Build/audit pipeline cannot execute. Check if Cortex service is running on Talos.")
        except requests.Timeout:
            self._add_finding("cortex_health", "critical",
                              "Cortex timed out",
                              "Service may be overloaded or hung.")
        except Exception as e:
            self._add_finding("cortex_health", "critical",
                              f"Cortex check failed: {str(e)[:100]}")

    def _check_audit_freshness(self, now: datetime):
        """Has an audit run recently?"""
        if not HAS_REQUESTS:
            return

        try:
            resp = requests.get(f"{CORTEX_URL}/api/audit/latest", timeout=5)
            if resp.status_code == 404:
                self._add_finding("audit_freshness", "warning",
                                  "No audit reports found",
                                  "Run: curl -X POST http://192.168.65.237:9100/api/audit/run")
                return
            if resp.status_code != 200:
                self._add_finding("audit_freshness", "warning",
                                  f"Could not fetch latest audit: HTTP {resp.status_code}")
                return

            data = resp.json()
            ts_str = data.get("timestamp", "")
            if not ts_str:
                self._add_finding("audit_freshness", "warning", "Audit report has no timestamp")
                return

            audit_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age_hours = (now - audit_time).total_seconds() / 3600

            if age_hours > AUDIT_STALE_HOURS:
                self._add_finding("audit_freshness", "warning",
                                  f"Last audit is {age_hours:.0f}h old (threshold: {AUDIT_STALE_HOURS}h)",
                                  f"Last run: {ts_str}. Verdict: {data.get('verdict', 'unknown')}")
            else:
                verdict = data.get("verdict", "unknown")
                self._add_finding("audit_freshness", "ok",
                                  f"Last audit {age_hours:.0f}h ago — verdict: {verdict}")

        except Exception as e:
            self._add_finding("audit_freshness", "warning",
                              f"Could not check audit freshness: {str(e)[:100]}")

    def _check_manifest_freshness(self, now: datetime):
        """Is the fleet manifest recent?"""
        if not HAS_REQUESTS:
            return

        try:
            resp = requests.get(f"{CORTEX_URL}/api/fleet/manifest", timeout=5)
            if resp.status_code != 200:
                self._add_finding("manifest_freshness", "warning",
                                  "Could not fetch fleet manifest from Cortex")
                return

            data = resp.json()
            ts_str = data.get("generated_at", "")
            source = data.get("_fleet_source", "unknown")

            if not ts_str:
                self._add_finding("manifest_freshness", "warning", "Manifest has no timestamp")
                return

            manifest_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age_hours = (now - manifest_time).total_seconds() / 3600

            if age_hours > MANIFEST_STALE_HOURS:
                self._add_finding("manifest_freshness", "warning",
                                  f"Fleet manifest is {age_hours:.0f}h old (threshold: {MANIFEST_STALE_HOURS}h)",
                                  f"Source: {source}. Run discovery to refresh.")
            else:
                self._add_finding("manifest_freshness", "ok",
                                  f"Manifest is {age_hours:.0f}h old, source: {source}")

            # Extra check: if using fallback, Homebase API may be down
            if source == "fallback":
                self._add_finding("manifest_source", "warning",
                                  "Manifest using hardcoded fallback — Homebase API may be unreachable",
                                  "Check: curl http://192.168.65.245:8000/api/infrastructure")

        except Exception as e:
            self._add_finding("manifest_freshness", "warning",
                              f"Could not check manifest: {str(e)[:100]}")

    def _check_learning_log_activity(self, now: datetime):
        """Is the learning log being updated?"""
        if not HAS_REQUESTS:
            return

        try:
            # Get manifest which includes learning log info indirectly
            # Or check audit history for recent entries
            resp = requests.get(f"{CORTEX_URL}/api/audit/history", timeout=5)
            if resp.status_code != 200:
                self._add_finding("learning_log", "info",
                                  "Could not check learning log activity")
                return

            data = resp.json()
            reports = data.get("reports", [])

            if not reports:
                self._add_finding("learning_log", "info",
                                  "No audit history — learning log may be stagnant")
                return

            # Check if any audit ran in last 7 days
            recent = False
            for r in reports:
                ts_str = r.get("timestamp", "")
                if ts_str:
                    try:
                        t = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if (now - t).days < LEARNING_LOG_STALE_DAYS:
                            recent = True
                            break
                    except Exception:
                        pass

            if not recent:
                self._add_finding("learning_log", "info",
                                  f"No audits in {LEARNING_LOG_STALE_DAYS} days — learning log may be stale",
                                  "The system improves through regular audits. Consider running one.")
            else:
                self._add_finding("learning_log", "ok",
                                  "Audit pipeline active within last 7 days")

        except Exception as e:
            self._add_finding("learning_log", "info",
                              f"Could not check learning log: {str(e)[:100]}")

    def _check_compile_regressions(self):
        """Does the latest audit show any compile failures?"""
        if not HAS_REQUESTS:
            return

        try:
            resp = requests.get(f"{CORTEX_URL}/api/audit/latest", timeout=5)
            if resp.status_code != 200:
                return  # Already flagged by freshness check

            data = resp.json()
            summary = data.get("summary", {})
            fail_count = summary.get("compile_fail", 0)
            safety_violations = summary.get("safety_violations", 0)

            if fail_count > MAX_COMPILE_FAILURES:
                self._add_finding("compile_regression", "warning",
                                  f"{fail_count} compile failure(s) in latest audit",
                                  "Check: curl http://192.168.65.237:9100/api/audit/latest")
            else:
                self._add_finding("compile_regression", "ok",
                                  "No compile failures in latest audit")

            if safety_violations > 0:
                self._add_finding("safety_violations", "critical",
                                  f"{safety_violations} safety violation(s) detected!",
                                  "MOCK_MODE or READ_ONLY_MODE may be disabled. Requires CEO review.")
            else:
                self._add_finding("safety_violations", "ok",
                                  "All safety flags verified")

        except Exception as e:
            self._add_finding("compile_regression", "info",
                              f"Could not check compile status: {str(e)[:100]}")

    def _check_homebase_api(self):
        """Is Homebase serving infrastructure truth?"""
        if not HAS_REQUESTS:
            return

        try:
            resp = requests.get(f"{HOMEBASE_URL}/api/infrastructure", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                server_count = len(data.get("servers", data.get("fleet", {})))
                self._add_finding("homebase_api", "ok",
                                  f"Homebase API serving {server_count} servers")
            else:
                self._add_finding("homebase_api", "warning",
                                  f"Homebase /api/infrastructure returned HTTP {resp.status_code}",
                                  "Cortex will fall back to hardcoded fleet. Fix Homebase API.")
        except requests.ConnectionError:
            self._add_finding("homebase_api", "critical",
                              "Homebase is UNREACHABLE on :8000",
                              "Fleet truth source is down. Cortex using fallback. All pages may be affected.")
        except Exception as e:
            self._add_finding("homebase_api", "warning",
                              f"Homebase API check failed: {str(e)[:100]}")


# ═══════════════════════════════════════════════════════════════
# Standalone execution for testing
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    monitor = PipelineMonitor()
    report = monitor.run_all_checks()

    print(f"Pipeline Status: {report['status'].upper()}")
    print(f"Checks: {report['summary']}")
    print()
    for f in report["findings"]:
        icon = {"ok": "✅", "info": "ℹ️", "warning": "⚠️", "critical": "❌"}.get(f["severity"], "?")
        print(f"  {icon} [{f['check']}] {f['message']}")
        if f.get("detail"):
            print(f"     {f['detail']}")
