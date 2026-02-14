#!/usr/bin/env python3
"""Run pipeline monitor and save report. Called by cron every 30 minutes."""
import sys, json
sys.path.insert(0, '/home/rizeadmin/homebase/backend')

from services.pipeline_monitor import PipelineMonitor

REPORT_FILE = "/home/rizeadmin/homebase/data/pipeline-report.json"

if __name__ == "__main__":
    monitor = PipelineMonitor()
    report = monitor.run_all_checks()
    
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    
    status = report["status"].upper()
    summary = report["summary"]
    print(f"[Pipeline Monitor] Status: {status} | Critical: {summary['critical']} | Warning: {summary['warning']} | OK: {summary['healthy']}")
