'use client';
import { useEffect, useState } from 'react';

interface Vuln { id: string; severity: string; description: string; }
interface Report {
  date: string; severity: string; total_checks: number;
  passed: number; failed: number; warnings: number;
  vulnerabilities: Vuln[]; updates_available: string[];
  new_features: string[]; submitted_at: string; full_report: string;
}
interface Summary {
  last_scan: string; last_severity: string; total_scans: number;
  last_vuln_count: number; last_update_count: number;
  trend: { date: string; severity: string; vulns: number; failed: number }[];
}

const sColor: Record<string,string> = { critical:'bg-red-600', high:'bg-orange-500', medium:'bg-yellow-500', low:'bg-green-500', clear:'bg-green-600' };
const sEmoji: Record<string,string> = { critical:'🔴', high:'🟠', medium:'🟡', low:'🟢', clear:'✅' };

export default function RedTeamPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [summary, setSummary] = useState<Summary|null>(null);
  const [sel, setSel] = useState<Report|null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/redteam?limit=30').then(r=>r.json())
      .then(d => { setReports(d.reports||[]); setSummary(d.summary||null); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <h1 className="text-2xl font-bold mb-1">🛡️ David Bishop — Red Team Dashboard</h1>
      <p className="text-gray-400 mb-6 text-sm">Nightly vulnerability scans, update checks, feature monitoring</p>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          {[
            ['Last Scan', summary.last_scan ? new Date(summary.last_scan).toLocaleDateString() : 'Never'],
            ['Status', (sEmoji[summary.last_severity]||'⚪') + ' ' + (summary.last_severity||'N/A').toUpperCase()],
            ['Vulns', String(summary.last_vuln_count ?? 0)],
            ['Updates', String(summary.last_update_count ?? 0)],
            ['Total Scans', String(summary.total_scans ?? 0)]
          ].map(([label, val], i) => (
            <div key={i} className="bg-gray-900 rounded-lg p-3 border border-gray-800">
              <div className="text-xs text-gray-400">{label}</div>
              <div className="text-lg font-mono">{val}</div>
            </div>
          ))}
        </div>
      )}

      {summary?.trend && summary.trend.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800 mb-6">
          <h2 className="text-xs text-gray-400 mb-2">7-Day Trend</h2>
          <div className="flex gap-2 items-end h-16">
            {summary.trend.map((t,i) => (
              <div key={i} className="flex flex-col items-center flex-1">
                <div className={'w-full rounded-t ' + (sColor[t.severity]||'bg-gray-600')}
                     style={{height: Math.max(8,(t.failed+t.vulns)*8) + 'px'}}/>
                <div className="text-xs text-gray-500 mt-1">{t.date.slice(5)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-gray-900 rounded-lg border border-gray-800">
        <div className="p-3 border-b border-gray-800"><h2 className="font-semibold text-sm">Scan History</h2></div>
        {reports.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No scans yet. First scan at 4 AM.</div>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-400 border-b border-gray-800">
              <th className="p-2">Date</th><th className="p-2">Status</th><th className="p-2">Pass</th>
              <th className="p-2">Fail</th><th className="p-2">Vulns</th><th className="p-2">Updates</th>
            </tr></thead>
            <tbody>{reports.map((r,i) => (
              <tr key={i} onClick={()=>setSel(sel?.date===r.date?null:r)}
                  className="border-b border-gray-800/50 hover:bg-gray-800/50 cursor-pointer">
                <td className="p-2 font-mono">{r.date}</td>
                <td className="p-2">{sEmoji[r.severity]} {r.severity}</td>
                <td className="p-2 font-mono text-green-400">{r.passed}</td>
                <td className="p-2 font-mono text-red-400">{r.failed}</td>
                <td className="p-2 font-mono">{r.vulnerabilities?.length||0}</td>
                <td className="p-2 font-mono">{r.updates_available?.length||0}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>

      {sel && (
        <div className="mt-4 bg-gray-900 rounded-lg border border-gray-800 p-4">
          <div className="flex justify-between mb-3">
            <h2 className="font-semibold text-sm">Detail — {sel.date}</h2>
            <button onClick={()=>setSel(null)} className="text-gray-400 hover:text-white">✕</button>
          </div>
          {sel.vulnerabilities?.length>0 && <div className="mb-3">
            <h3 className="text-xs text-red-400 font-semibold mb-1">Vulnerabilities</h3>
            {sel.vulnerabilities.map((v,i) => (
              <div key={i} className="bg-gray-800 rounded p-2 mb-1 text-xs">
                <span className={'px-1.5 py-0.5 rounded text-xs mr-2 ' + 
                  (v.severity==='critical'?'bg-red-600':v.severity==='high'?'bg-orange-500':'bg-yellow-600')}>
                  {v.severity}</span>{v.description}
              </div>))}
          </div>}
          {sel.updates_available?.length>0 && <div className="mb-3">
            <h3 className="text-xs text-blue-400 font-semibold mb-1">Updates</h3>
            {sel.updates_available.map((u,i) => <div key={i} className="bg-gray-800 rounded p-2 mb-1 text-xs">📦 {u}</div>)}
          </div>}
          {sel.new_features?.length>0 && <div className="mb-3">
            <h3 className="text-xs text-purple-400 font-semibold mb-1">New Features</h3>
            {sel.new_features.map((f,i) => <div key={i} className="bg-gray-800 rounded p-2 mb-1 text-xs">✨ {f}</div>)}
          </div>}
          {sel.full_report && <pre className="bg-gray-800 rounded p-3 text-xs overflow-x-auto whitespace-pre-wrap max-h-80 mt-2">{sel.full_report}</pre>}
        </div>
      )}
    </div>
  );
}
