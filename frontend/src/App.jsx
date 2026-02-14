import { useState, useEffect } from "react";
import { initCache, getCached, getCacheAge, subscribe, refreshKey } from "./services/dataCache";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

function StatusBadge({ status }) {
  const colors = { online: "bg-green-500", offline: "bg-red-500", skip: "bg-gray-500", healthy: "bg-green-500", good: "bg-blue-500", warning: "bg-yellow-500", busy: "bg-orange-500", critical: "bg-red-500", error: "bg-red-500" };
  return <span className={`${colors[status] || "bg-gray-500"} px-2 py-1 rounded text-xs font-bold uppercase`}>{status}</span>;
}

function PriorityBadge({ priority }) {
  const colors = { P0: "bg-red-600", P1: "bg-orange-500", P2: "bg-yellow-500", P3: "bg-blue-400" };
  return <span className={`${colors[priority] || "bg-gray-500"} px-2 py-0.5 rounded text-xs font-bold`}>{priority}</span>;
}

function ProgressBar({ used, total, label }) {
  if (!total) return <span className="text-gray-500 text-sm">-</span>;
  const percent = Math.round((used / total) * 100);
  const color = percent > 80 ? "bg-red-500" : percent > 60 ? "bg-yellow-500" : "bg-green-500";
  return <div className="w-full"><div className="flex justify-between text-xs text-gray-400 mb-1"><span>{label}</span><span>{used}/{total} ({percent}%)</span></div><div className="w-full bg-gray-700 rounded-full h-2"><div className={`${color} h-2 rounded-full`} style={{ width: `${percent}%` }}></div></div></div>;
}

function NavLink({ to, children }) {
  const location = useLocation();
  const isActive = location.pathname === to;
  return <Link to={to} className={`px-4 py-2 rounded-lg transition-colors ${isActive ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white hover:bg-slate-700"}`}>{children}</Link>;
}

function Layout({ children }) {
  return <div className="min-h-screen bg-slate-900 text-white"><nav className="bg-slate-800 border-b border-slate-700"><div className="max-w-7xl mx-auto px-6 py-4"><div className="flex items-center justify-between"><Link to="/" className="text-xl font-bold">Homebase</Link><div className="flex gap-2"><NavLink to="/">Servers</NavLink><NavLink to="/projects">Projects</NavLink><NavLink to="/metrics">Metrics</NavLink><NavLink to="/security">Security</NavLink><NavLink to="/discovery">Discovery</NavLink><NavLink to="/credentials">Credentials</NavLink><NavLink to="/settings">Settings</NavLink><NavLink to="/fleet-topology">🗺️ Fleet</NavLink><NavLink to="/sentinel">🛡️ Sentinel</NavLink><NavLink to="/tasks">Tasks</NavLink><NavLink to="/agent-security">🔒 Security</NavLink></div></div></div></nav><main className="max-w-7xl mx-auto p-6">{children}</main></div>;
}

function ServerCard({ server }) {
  return <div className="bg-slate-800 rounded-lg p-5 shadow-lg border border-slate-700 hover:border-slate-600 transition-colors"><div className="flex justify-between items-start mb-4"><div><h3 className="text-xl font-bold text-white">{server.name}</h3><p className="text-gray-400 text-sm">{server.ip}</p></div><StatusBadge status={server.status} /></div>{server.status === "online" && <div className="space-y-3 mb-4"><div className="text-sm text-gray-300"><span className="text-gray-500">Uptime:</span> {server.uptime || "-"}</div><ProgressBar used={server.memory_used} total={server.memory_total} label="Memory (MB)" /><ProgressBar used={server.disk_used} total={server.disk_total} label="Disk (GB)" />{server.cpu_percent !== null && <div className="text-sm text-gray-300"><span className="text-gray-500">CPU:</span> {server.cpu_percent.toFixed(1)}%</div>}</div>}{server.status === "skip" && <p className="text-gray-500 text-sm mb-4">Windows host - SSH not available</p>}{server.status === "offline" && <p className="text-red-400 text-sm mb-4">Unable to connect</p>}<div className="flex gap-2 mt-auto">{server.web_url && <a href={`https://${server.web_url}`} target="_blank" rel="noopener noreferrer" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-center py-2 px-3 rounded text-sm font-medium transition-colors">Web</a>}{server.ssh_url && <a href={`ssh://${server.ssh_url}`} className="flex-1 bg-slate-600 hover:bg-slate-500 text-white text-center py-2 px-3 rounded text-sm font-medium transition-colors">SSH</a>}</div></div>;
}

function ServersPage() {
  const [servers, setServers] = useState(() => getCached('servers')?.servers || []);
  const [loading, setLoading] = useState(() => !getCached('servers'));
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [cacheAge, setCacheAge] = useState(0);
  const [error, setError] = useState(null);

  const fetchServers = async (force = false) => {
    try {
      if (force) setRefreshing(true);
      const url = force ? "/api/servers?force=true" : "/api/servers";
      const res = await fetch(url);
      const data = await res.json();
      setServers(data.servers);
      setLastUpdate(new Date());
      setCacheAge(data.cache_age || 0);
      setError(null);
      if (!force) fetch("/api/metrics/record", { method: "POST" }).catch(() => {});
    } catch (err) {
      setError("Failed to fetch server data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchServers();
    const interval = setInterval(() => fetchServers(false), 30000);
    return () => clearInterval(interval);
  }, []);

  const onlineCount = servers.filter(s => s.status === "online").length;
  const totalCount = servers.filter(s => s.status !== "skip").length;

  return <div><div className="flex justify-between items-center mb-6"><div><h1 className="text-2xl font-bold">Servers</h1><p className="text-gray-400">Infrastructure monitoring</p></div><div className="flex items-center gap-4"><button onClick={() => fetchServers(true)} disabled={refreshing} className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 px-4 py-2 rounded text-sm">{refreshing ? "Refreshing..." : "Force Refresh"}</button><div className="text-right"><div className="text-2xl font-bold text-green-400">{onlineCount}/{totalCount}</div><div className="text-gray-400 text-sm">servers online</div>{lastUpdate && <div className="text-gray-500 text-xs mt-1">Updated: {lastUpdate.toLocaleTimeString()}{cacheAge > 0 && <span className="ml-1">(cached {cacheAge}s ago)</span>}</div>}</div></div></div>{loading ? <div className="text-center py-20"><div className="animate-spin text-4xl mb-4">*</div><p className="text-gray-400">Loading server data...</p></div> : error ? <div className="text-center py-20"><p className="text-red-400">{error}</p><button onClick={() => fetchServers(true)} className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Retry</button></div> : <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">{servers.map(server => <ServerCard key={server.name} server={server} />)}</div>}<p className="text-center text-gray-500 text-sm mt-8">Auto-refreshes every 30 seconds | Click Force Refresh for live data</p></div>;
}

function MetricsPage() {
  const [metricsData, setMetricsData] = useState({});
  const [summary, setSummary] = useState({});
  const [selectedServer, setSelectedServer] = useState(null);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(() => !getCached('servers'));
  const [error, setError] = useState(null);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const [historyRes, summaryRes] = await Promise.all([
        fetch("/api/metrics/history?hours=" + hours + "&interval=30"),
        fetch("/api/metrics/summary?hours=" + hours)
      ]);
      const historyData = await historyRes.json();
      const summaryData = await summaryRes.json();
      setMetricsData(historyData.servers || {});
      setSummary(summaryData.summary || {});
      setError(null);
      if (!selectedServer && Object.keys(historyData.servers || {}).length > 0) {
        setSelectedServer(Object.keys(historyData.servers)[0]);
      }
    } catch (err) {
      setError("Failed to fetch metrics data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMetrics(); }, [hours]);

  const servers = Object.keys(metricsData);
  const currentData = selectedServer ? metricsData[selectedServer] || [] : [];
  const currentSummary = selectedServer ? summary[selectedServer] : null;

  return <div><div className="flex justify-between items-center mb-6"><div><h1 className="text-2xl font-bold">Metrics History</h1><p className="text-gray-400">Historical CPU, Memory, and Disk usage</p></div><div className="flex gap-4 items-center"><select value={hours} onChange={(e) => setHours(parseInt(e.target.value))} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm"><option value={6}>Last 6 hours</option><option value={24}>Last 24 hours</option><option value={48}>Last 48 hours</option><option value={168}>Last 7 days</option></select><button onClick={fetchMetrics} disabled={loading} className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 px-4 py-2 rounded text-sm">{loading ? "Loading..." : "Refresh"}</button></div></div><div className="flex gap-2 mb-6 flex-wrap">{servers.map(server => <button key={server} onClick={() => setSelectedServer(server)} className={"px-4 py-2 rounded text-sm transition-colors " + (selectedServer === server ? "bg-blue-600 text-white" : "bg-slate-700 text-gray-300 hover:bg-slate-600")}>{server}</button>)}</div>{loading && servers.length === 0 ? <div className="text-center py-20"><div className="animate-spin text-4xl mb-4">*</div><p className="text-gray-400">Loading metrics...</p></div> : error ? <div className="text-center py-20"><p className="text-red-400">{error}</p><button onClick={fetchMetrics} className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Retry</button></div> : servers.length === 0 ? <div className="text-center py-20 bg-slate-800 rounded-lg border border-slate-700"><p className="text-gray-400 mb-4">No metrics data available yet</p><p className="text-gray-500 text-sm">Metrics are recorded every 30 seconds on the Servers page</p></div> : selectedServer && <>{currentSummary && <div className="grid grid-cols-3 gap-4 mb-6"><div className="bg-slate-800 rounded-lg p-4 border border-slate-700"><h3 className="text-sm text-gray-400 mb-2">CPU</h3><div className="text-2xl font-bold text-blue-400">{currentSummary.avg_cpu ? currentSummary.avg_cpu.toFixed(1) : "-"}%</div><div className="text-xs text-gray-500">Max: {currentSummary.max_cpu ? currentSummary.max_cpu.toFixed(1) : "-"}%</div></div><div className="bg-slate-800 rounded-lg p-4 border border-slate-700"><h3 className="text-sm text-gray-400 mb-2">Memory</h3><div className="text-2xl font-bold text-green-400">{currentSummary.avg_memory ? currentSummary.avg_memory.toFixed(1) : "-"}%</div><div className="text-xs text-gray-500">Max: {currentSummary.max_memory ? currentSummary.max_memory.toFixed(1) : "-"}%</div></div><div className="bg-slate-800 rounded-lg p-4 border border-slate-700"><h3 className="text-sm text-gray-400 mb-2">Disk</h3><div className="text-2xl font-bold text-yellow-400">{currentSummary.avg_disk ? currentSummary.avg_disk.toFixed(1) : "-"}%</div><div className="text-xs text-gray-500">Max: {currentSummary.max_disk ? currentSummary.max_disk.toFixed(1) : "-"}%</div></div></div>}{currentData.length > 0 ? <div className="bg-slate-800 rounded-lg p-6 border border-slate-700"><h3 className="text-lg font-bold mb-4">{selectedServer} - Usage Over Time</h3><ResponsiveContainer width="100%" height={400}><LineChart data={currentData}><CartesianGrid strokeDasharray="3 3" stroke="#374151" /><XAxis dataKey="time_label" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} /><YAxis stroke="#9CA3AF" domain={[0, 100]} tick={{ fill: '#9CA3AF', fontSize: 12 }} tickFormatter={(v) => v + "%"} /><Tooltip contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #374151' }} labelStyle={{ color: '#9CA3AF' }} /><Legend /><Line type="monotone" dataKey="cpu_percent" name="CPU" stroke="#3B82F6" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="memory_percent" name="Memory" stroke="#10B981" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="disk_percent" name="Disk" stroke="#F59E0B" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div> : <div className="text-center py-10 bg-slate-800 rounded-lg border border-slate-700"><p className="text-gray-400">No data points for {selectedServer} in selected time range</p></div>}</>}<p className="text-center text-gray-500 text-sm mt-6">Data points: {currentData.length} | Interval: ~30 minutes</p></div>;
}

function SecurityPage() {
  const [securityData, setSecurityData] = useState(() => getCached("security")?.servers || []);
  const [loading, setLoading] = useState(() => !getCached('servers'));
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const fetchSecurity = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/security/scan");
      const data = await res.json();
      setSecurityData(data.servers || []);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError("Failed to fetch security data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSecurity(); }, []);

  const criticalCount = securityData.filter(s => s.status === "critical").length;
  const warningCount = securityData.filter(s => s.status === "warning").length;

  return <div><div className="flex justify-between items-center mb-6"><div><h1 className="text-2xl font-bold">Security</h1><p className="text-gray-400">OS updates and authentication monitoring</p></div><div className="flex gap-4 items-center">{criticalCount > 0 && <div className="bg-red-900 border border-red-700 px-3 py-1 rounded"><span className="text-red-400 font-bold">{criticalCount}</span><span className="text-red-300 text-sm ml-1">critical</span></div>}{warningCount > 0 && <div className="bg-yellow-900 border border-yellow-700 px-3 py-1 rounded"><span className="text-yellow-400 font-bold">{warningCount}</span><span className="text-yellow-300 text-sm ml-1">warnings</span></div>}<button onClick={fetchSecurity} disabled={loading} className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 px-4 py-2 rounded text-sm">{loading ? "Scanning..." : "Refresh"}</button></div></div>{loading && securityData.length === 0 ? <div className="text-center py-20"><div className="animate-spin text-4xl mb-4">*</div><p className="text-gray-400">Running security scan...</p></div> : error ? <div className="text-center py-20"><p className="text-red-400">{error}</p><button onClick={fetchSecurity} className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Retry</button></div> : <><div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden mb-6"><table className="w-full"><thead className="bg-slate-700"><tr><th className="text-left px-4 py-3 text-sm font-medium text-gray-300">Server</th><th className="text-left px-4 py-3 text-sm font-medium text-gray-300">Status</th><th className="text-left px-4 py-3 text-sm font-medium text-gray-300">Updates</th><th className="text-left px-4 py-3 text-sm font-medium text-gray-300">Critical</th><th className="text-left px-4 py-3 text-sm font-medium text-gray-300">Failed Auth</th></tr></thead><tbody className="divide-y divide-slate-700">{securityData.map(server => <tr key={server.name}><td className="px-4 py-3"><div className="font-medium text-white">{server.name}</div><div className="text-xs text-gray-500">{server.server_ip}</div></td><td className="px-4 py-3"><StatusBadge status={server.status} /></td><td className="px-4 py-3 text-gray-300">{server.updates && server.updates.total !== undefined ? server.updates.total : "-"}</td><td className="px-4 py-3">{server.updates && server.updates.critical > 0 ? <span className="text-red-400 font-bold">{server.updates.critical}</span> : <span className="text-gray-500">0</span>}</td><td className="px-4 py-3">{server.auth && server.auth.failed_count > 10 ? <span className="text-yellow-400 font-bold">{server.auth.failed_count}</span> : <span className="text-gray-500">{server.auth ? server.auth.failed_count : "-"}</span>}</td></tr>)}</tbody></table></div>{lastUpdate && <p className="text-center text-gray-500 text-sm">Last scanned: {lastUpdate.toLocaleTimeString()}</p>}</>}</div>;
}

function ProjectCard({ project, onClick }) {
  const docIcons = { README: "R", TODO: "T", CHANGELOG: "C", PROJECT_PLAN: "P", CLAUDE: "AI" };
  const docDescriptions = {
    README: "README.md - Project overview and quickstart",
    TODO: "TODO.md - Open tasks and roadmap items",
    CHANGELOG: "CHANGELOG.md - Version history and changes",
    PROJECT_PLAN: "PROJECT_PLAN.md - Detailed project roadmap",
    CLAUDE: "CLAUDE.md - AI development instructions"
  };
  return (
    <div className="bg-slate-800 rounded-lg p-5 shadow-lg border border-slate-700 hover:border-blue-500 transition-colors cursor-pointer" onClick={onClick}>
      <div className="flex justify-between items-start mb-3">
        <div><h3 className="text-lg font-bold text-white">{project.project}</h3><p className="text-gray-500 text-sm">{project.server_ip}</p></div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge status={project.status} />
          {project.version && <span className="bg-slate-700 text-gray-300 px-2 py-0.5 rounded text-xs">v{project.version}</span>}
        </div>
      </div>
      <div className="flex gap-1 mb-3 flex-wrap">
        {project.docs && project.docs.map(doc => (<span key={doc} className="bg-slate-700 text-gray-300 px-2 py-0.5 rounded text-xs cursor-help" title={docDescriptions[doc] || doc}>{docIcons[doc] || doc}</span>))}
      </div>
      <div className="flex justify-between items-center text-sm">
        <div><span className="text-gray-400">Open:</span><span className={`ml-1 font-bold ${project.todo_open > 10 ? "text-red-400" : project.todo_open > 5 ? "text-yellow-400" : "text-green-400"}`}>{project.todo_open}</span></div>
        <div><span className="text-gray-400">Done:</span><span className="ml-1 text-gray-300">{project.todo_completed}</span></div>
      </div>
      {project.last_synced && <p className="text-gray-600 text-xs mt-2">Synced: {new Date(project.last_synced).toLocaleString()}</p>}
    </div>
  );
}

function ProjectsPage() {
  const [projects, setProjects] = useState(() => getCached("projects")?.projects || []);
  const [health, setHealth] = useState({});
  const [loading, setLoading] = useState(() => !getCached('servers'));
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectDetail, setProjectDetail] = useState(null);

  const fetchProjects = async () => {
    try { const res = await fetch("/api/projects"); const data = await res.json(); setProjects(data.projects || []); setHealth(data.health || {}); setError(null); } catch (err) { setError("Failed to fetch projects"); } finally { setLoading(false); }
  };
  const syncProjects = async () => {
    try { setSyncing(true); await fetch("/api/projects/sync", { method: "POST" }); await fetchProjects(); } catch (err) { setError("Sync failed"); } finally { setSyncing(false); }
  };
  const fetchProjectDetail = async (projectName) => {
    try { const res = await fetch("/api/projects/" + projectName); const data = await res.json(); setProjectDetail(data); setSelectedProject(projectName); } catch (err) { console.error("Failed to fetch project detail", err); }
  };

  useEffect(() => { fetchProjects(); }, []);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div><h1 className="text-2xl font-bold">Projects</h1><p className="text-gray-400">Documentation and TODO tracking</p></div>
        <div className="flex gap-4 items-center">
          {health.total_open_todos > 0 && (<div className="flex gap-2">
            {health.p0_count > 0 && <span className="bg-red-900 border border-red-700 px-2 py-1 rounded text-xs"><span className="text-red-400 font-bold">{health.p0_count}</span> P0</span>}
            {health.p1_count > 0 && <span className="bg-orange-900 border border-orange-700 px-2 py-1 rounded text-xs"><span className="text-orange-400 font-bold">{health.p1_count}</span> P1</span>}
          </div>)}
          <button onClick={syncProjects} disabled={syncing} className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 px-4 py-2 rounded text-sm">{syncing ? "Syncing..." : "Sync All"}</button>
        </div>
      </div>
      {selectedProject && projectDetail && (
        <div className="fixed inset-0 bg-black bg-opacity-70 z-50 flex items-center justify-center p-4" onClick={() => setSelectedProject(null)}>
          <div className="bg-slate-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-auto p-6 border border-slate-600" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4"><h2 className="text-xl font-bold">{selectedProject}</h2><button onClick={() => setSelectedProject(null)} className="text-gray-400 hover:text-white text-xl">X</button></div>
            {projectDetail.todos && projectDetail.todos.filter(t => t.status === 'open').length > 0 && (
              <div className="mb-6"><h3 className="text-lg font-semibold mb-3 text-blue-400">Open TODOs</h3>
                <div className="space-y-2">{projectDetail.todos.filter(t => t.status === 'open').map((todo, idx) => (<div key={idx} className="flex items-start gap-2 p-2 bg-slate-900 rounded">{todo.priority && <PriorityBadge priority={todo.priority} />}<span className="text-gray-300 text-sm">{todo.description}</span></div>))}</div>
              </div>
            )}
            <div className="space-y-2">{projectDetail.docs && Object.keys(projectDetail.docs).map(docType => (<details key={docType} className="bg-slate-900 rounded p-3"><summary className="cursor-pointer font-semibold text-gray-300">{docType}.md</summary><pre className="mt-2 text-xs text-gray-400 overflow-x-auto whitespace-pre-wrap max-h-60 overflow-y-auto">{projectDetail.docs[docType].content}</pre></details>))}</div>
          </div>
        </div>
      )}
      {loading ? (<div className="text-center py-20"><div className="animate-spin text-4xl mb-4">*</div><p className="text-gray-400">Loading projects...</p></div>
      ) : error ? (<div className="text-center py-20"><p className="text-red-400">{error}</p><button onClick={fetchProjects} className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Retry</button></div>
      ) : projects.length === 0 ? (<div className="text-center py-20 bg-slate-800 rounded-lg border border-slate-700"><p className="text-gray-400 mb-4">No projects synced yet</p><button onClick={syncProjects} disabled={syncing} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">{syncing ? "Syncing..." : "Sync Now"}</button></div>
      ) : (<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">{projects.map(project => (<ProjectCard key={project.project} project={project} onClick={() => fetchProjectDetail(project.project)} />))}</div>)}
      {health.last_sync && (<p className="text-center text-gray-500 text-sm mt-6">Last sync: {new Date(health.last_sync).toLocaleString()} | {health.total_open_todos} open TODOs across {health.total_projects} projects</p>)}
      <div className="mt-4 text-center text-xs text-gray-600">
        <span className="mr-3">Doc Legend:</span>
        <span className="bg-slate-700 px-1.5 py-0.5 rounded mr-1">C</span>=CHANGELOG
        <span className="bg-slate-700 px-1.5 py-0.5 rounded mx-1 ml-3">R</span>=README
        <span className="bg-slate-700 px-1.5 py-0.5 rounded mx-1 ml-3">T</span>=TODO
        <span className="bg-slate-700 px-1.5 py-0.5 rounded mx-1 ml-3">P</span>=PROJECT_PLAN
        <span className="bg-slate-700 px-1.5 py-0.5 rounded mx-1 ml-3">AI</span>=CLAUDE
      </div>
    </div>
  );
}

function DiscoveryPage() {
  const [projects, setProjects] = useState(() => getCached("projects")?.projects || []);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/discovery/projects");
      const data = await res.json();
      setProjects(data.projects || []);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError("Failed to discover projects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch("/api/discovery/registered").then(res => res.json()).then(data => setProjects(data.projects || [])).catch(() => {});
  }, []);

  return <div><div className="flex justify-between items-center mb-6"><div><h1 className="text-2xl font-bold">Discovery</h1><p className="text-gray-400">Auto-discovered projects</p></div><div className="flex gap-4 items-center"><span className="text-gray-400">{projects.length} projects</span><button onClick={fetchProjects} disabled={loading} className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 px-4 py-2 rounded text-sm">{loading ? "Scanning..." : "Scan All"}</button></div></div>{loading && projects.length === 0 ? <div className="text-center py-20"><div className="animate-spin text-4xl mb-4">*</div><p className="text-gray-400">Discovering projects...</p></div> : error ? <div className="text-center py-20"><p className="text-red-400">{error}</p><button onClick={fetchProjects} className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Retry</button></div> : projects.length === 0 ? <div className="text-center py-20 bg-slate-800 rounded-lg border border-slate-700"><p className="text-gray-400 mb-4">No projects discovered yet</p><button onClick={fetchProjects} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Start Discovery</button></div> : <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{projects.map((project, idx) => <div key={project.server + project.path + idx} className="bg-slate-800 rounded-lg p-5 border border-slate-700 hover:border-slate-600"><div className="flex justify-between items-start mb-3"><div><h3 className="text-lg font-bold text-white">{project.name}</h3><p className="text-gray-500 text-sm">{project.server_name || project.server}</p></div>{project.version && <span className="bg-slate-700 text-gray-300 px-2 py-1 rounded text-xs">v{project.version}</span>}</div>{project.description && <p className="text-gray-400 text-sm mb-3">{project.description}</p>}<div className="text-xs text-gray-500"><code className="bg-slate-900 px-1 rounded">{project.path}</code></div></div>)}</div>}{lastUpdate && <p className="text-center text-gray-500 text-sm mt-6">Last scan: {lastUpdate.toLocaleTimeString()}</p>}</div>;
}

function CredentialsPage() {
  const [credentials, setCredentials] = useState([]);
  const [projects, setProjects] = useState(() => getCached("projects")?.projects || []);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(() => !getCached('servers'));
  const [error, setError] = useState(null);
  const [authError, setAuthError] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [revealedCreds, setRevealedCreds] = useState({});
  const [selectedProject, setSelectedProject] = useState('all');
  const [newCred, setNewCred] = useState({ name: '', type: 'api_key', value: '', project: 'Other', description: '' });

  const fetchCredentials = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('session_token');
      if (!token) {
        setAuthError(true);
        setError('Please login and enable 2FA to access credentials');
        setLoading(false);
        return;
      }
      const res = await fetch('/api/credentials', { headers: { 'Authorization': 'Bearer ' + token } });
      if (res.status === 401 || res.status === 403) {
        setAuthError(true);
        setError(res.status === 403 ? '2FA must be enabled to access credentials' : 'Please login to access credentials');
        setLoading(false);
        return;
      }
      const data = await res.json();
      setCredentials(data.credentials || []);
      setProjects(data.projects || []);
      setAuthError(false);
      setError(null);
    } catch (err) {
      setError('Failed to fetch credentials');
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    try {
      const token = localStorage.getItem('session_token');
      const res = await fetch('/api/credentials/logs?limit=50', { headers: { 'Authorization': 'Bearer ' + token } });
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (err) {
      console.error('Failed to fetch logs');
    }
  };

  useEffect(() => { fetchCredentials(); }, []);

  const revealCredential = async (name) => {
    try {
      const token = localStorage.getItem('session_token');
      const res = await fetch('/api/credentials/' + encodeURIComponent(name), { headers: { 'Authorization': 'Bearer ' + token } });
      const data = await res.json();
      setRevealedCreds(prev => ({ ...prev, [name]: data.value }));
      // Auto-hide after 10 seconds
      setTimeout(() => setRevealedCreds(prev => { const updated = { ...prev }; delete updated[name]; return updated; }), 10000);
    } catch (err) {
      alert('Failed to retrieve credential');
    }
  };

  const copyToClipboard = async (name) => {
    const value = revealedCreds[name];
    if (value) {
      await navigator.clipboard.writeText(value);
      alert('Copied to clipboard');
    } else {
      // Reveal first then copy
      try {
        const token = localStorage.getItem('session_token');
        const res = await fetch('/api/credentials/' + encodeURIComponent(name), { headers: { 'Authorization': 'Bearer ' + token } });
        const data = await res.json();
        await navigator.clipboard.writeText(data.value);
        alert('Copied to clipboard');
      } catch (err) {
        alert('Failed to copy credential');
      }
    }
  };

  const addCredential = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('session_token');
      const res = await fetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify(newCred)
      });
      if (!res.ok) throw new Error('Failed to add credential');
      setShowAddForm(false);
      setNewCred({ name: '', type: 'api_key', value: '', project: 'Other', description: '' });
      fetchCredentials();
    } catch (err) {
      alert('Failed to add credential');
    }
  };

  const deleteCredential = async (name) => {
    if (!confirm('Are you sure you want to delete "' + name + '"?')) return;
    try {
      const token = localStorage.getItem('session_token');
      await fetch('/api/credentials/' + encodeURIComponent(name), { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + token } });
      fetchCredentials();
    } catch (err) {
      alert('Failed to delete credential');
    }
  };

  const filteredCreds = selectedProject === 'all' ? credentials : credentials.filter(c => c.project === selectedProject);
  const groupedCreds = filteredCreds.reduce((acc, cred) => {
    const project = cred.project || 'Other';
    if (!acc[project]) acc[project] = [];
    acc[project].push(cred);
    return acc;
  }, {});

  const typeIcons = { ssh_key: '🔑', api_key: '🔐', password: '••••', token: '🎫' };

  if (authError) {
    return <div className="text-center py-20"><div className="text-6xl mb-4">🔒</div><h2 className="text-2xl font-bold mb-4">Authentication Required</h2><p className="text-gray-400 mb-6">{error}</p><a href="/" className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded text-white">Go to Login</a></div>;
  }

  return <div><div className="flex justify-between items-center mb-6"><div><h1 className="text-2xl font-bold">Credentials</h1><p className="text-gray-400">Secure credential storage (2FA required)</p></div><div className="flex gap-2"><button onClick={() => { fetchLogs(); setShowLogs(!showLogs); }} className="bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded text-sm">{showLogs ? 'Hide Logs' : 'View Audit Log'}</button><button onClick={() => setShowAddForm(true)} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-sm">+ Add Credential</button></div></div>

{showAddForm && <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"><div className="bg-slate-800 rounded-lg p-6 w-full max-w-md border border-slate-700"><h3 className="text-lg font-bold mb-4">Add Credential</h3><form onSubmit={addCredential}><div className="space-y-4"><div><label className="block text-sm text-gray-400 mb-1">Name</label><input type="text" value={newCred.name} onChange={e => setNewCred({...newCred, name: e.target.value})} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2" required /></div><div><label className="block text-sm text-gray-400 mb-1">Type</label><select value={newCred.type} onChange={e => setNewCred({...newCred, type: e.target.value})} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2"><option value="api_key">API Key</option><option value="ssh_key">SSH Key</option><option value="password">Password</option><option value="token">Token</option></select></div><div><label className="block text-sm text-gray-400 mb-1">Project</label><select value={newCred.project} onChange={e => setNewCred({...newCred, project: e.target.value})} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2">{projects.map(p => <option key={p} value={p}>{p}</option>)}</select></div><div><label className="block text-sm text-gray-400 mb-1">Value</label><textarea value={newCred.value} onChange={e => setNewCred({...newCred, value: e.target.value})} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 h-24 font-mono text-sm" required /></div><div><label className="block text-sm text-gray-400 mb-1">Description (optional)</label><input type="text" value={newCred.description} onChange={e => setNewCred({...newCred, description: e.target.value})} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2" /></div></div><div className="flex gap-2 mt-6"><button type="button" onClick={() => setShowAddForm(false)} className="flex-1 bg-slate-700 hover:bg-slate-600 py-2 rounded">Cancel</button><button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 py-2 rounded">Save</button></div></form></div></div>}

<div className="flex gap-2 mb-6 flex-wrap"><button onClick={() => setSelectedProject('all')} className={"px-3 py-1 rounded text-sm " + (selectedProject === 'all' ? "bg-blue-600" : "bg-slate-700 hover:bg-slate-600")}>All ({credentials.length})</button>{projects.map(p => { const count = credentials.filter(c => c.project === p).length; return count > 0 ? <button key={p} onClick={() => setSelectedProject(p)} className={"px-3 py-1 rounded text-sm " + (selectedProject === p ? "bg-blue-600" : "bg-slate-700 hover:bg-slate-600")}>{p} ({count})</button> : null; })}</div>

{loading ? <div className="text-center py-20"><div className="animate-spin text-4xl mb-4">*</div><p className="text-gray-400">Loading credentials...</p></div> : error ? <div className="text-center py-20"><p className="text-red-400">{error}</p></div> : filteredCreds.length === 0 ? <div className="text-center py-20 bg-slate-800 rounded-lg border border-slate-700"><p className="text-gray-400 mb-4">No credentials stored yet</p><button onClick={() => setShowAddForm(true)} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Add First Credential</button></div> : 
<div className="space-y-6">{Object.entries(groupedCreds).map(([project, creds]) => <div key={project} className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden"><div className="bg-slate-700 px-4 py-2 font-medium">{project}</div><div className="divide-y divide-slate-700">{creds.map(cred => <div key={cred.id} className="p-4 hover:bg-slate-700/50"><div className="flex justify-between items-start"><div><div className="flex items-center gap-2"><span className="text-lg">{typeIcons[cred.type]}</span><span className="font-medium text-white">{cred.name}</span><span className="text-xs bg-slate-600 px-2 py-0.5 rounded">{cred.type}</span></div>{cred.description && <p className="text-sm text-gray-400 mt-1">{cred.description}</p>}<div className="text-xs text-gray-500 mt-2">{cred.last_used_at ? 'Last used: ' + new Date(cred.last_used_at).toLocaleString() : 'Never used'}</div></div><div className="flex gap-2">{revealedCreds[cred.name] ? <div className="flex gap-2 items-center"><code className="bg-slate-900 px-3 py-1 rounded text-sm font-mono max-w-xs overflow-hidden text-ellipsis">{revealedCreds[cred.name]}</code><button onClick={() => copyToClipboard(cred.name)} className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm">Copy</button></div> : <><button onClick={() => revealCredential(cred.name)} className="bg-slate-600 hover:bg-slate-500 px-3 py-1 rounded text-sm">Reveal (10s)</button><button onClick={() => copyToClipboard(cred.name)} className="bg-slate-600 hover:bg-slate-500 px-3 py-1 rounded text-sm">Copy</button></>}<button onClick={() => deleteCredential(cred.name)} className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm">Delete</button></div></div></div>)}</div></div>)}</div>}

{showLogs && <div className="mt-8 bg-slate-800 rounded-lg border border-slate-700 overflow-hidden"><div className="bg-slate-700 px-4 py-2 font-medium flex justify-between"><span>Audit Log</span><button onClick={() => setShowLogs(false)} className="text-gray-400 hover:text-white">×</button></div><div className="max-h-96 overflow-y-auto"><table className="w-full"><thead className="bg-slate-700/50 sticky top-0"><tr><th className="text-left px-4 py-2 text-sm">Time</th><th className="text-left px-4 py-2 text-sm">Credential</th><th className="text-left px-4 py-2 text-sm">Action</th><th className="text-left px-4 py-2 text-sm">User</th><th className="text-left px-4 py-2 text-sm">IP</th></tr></thead><tbody className="divide-y divide-slate-700">{logs.map(log => <tr key={log.id}><td className="px-4 py-2 text-sm text-gray-400">{new Date(log.created_at).toLocaleString()}</td><td className="px-4 py-2 text-sm">{log.credential_name}</td><td className="px-4 py-2 text-sm"><span className={"px-2 py-0.5 rounded text-xs " + (log.action === 'retrieve' ? 'bg-yellow-600' : log.action === 'delete' ? 'bg-red-600' : 'bg-blue-600')}>{log.action}</span></td><td className="px-4 py-2 text-sm">{log.user || '-'}</td><td className="px-4 py-2 text-sm text-gray-500">{log.ip_address || '-'}</td></tr>)}</tbody></table></div></div>}</div>;
}


function SettingsPage() {
  const [settings, setSettings] = useState({
    cpu_threshold: 90,
    memory_threshold: 90,
    disk_threshold: 90,
    cooldown_minutes: 15,
    alert_recipients: '',
    alerts_enabled: true
  });
  const [loading, setLoading] = useState(() => !getCached('servers'));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const fetchSettings = async () => {
    try {
      const res = await fetch("/api/settings");
      const data = await res.json();
      setSettings(data.settings || {});
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to load settings' });
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      setSaving(true);
      const res = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        setMessage({ type: 'success', text: 'Settings saved successfully' });
        setTimeout(() => setMessage(null), 3000);
      } else {
        throw new Error('Failed to save');
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => { fetchSettings(); }, []);

  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div><h1 className="text-2xl font-bold">Settings</h1><p className="text-gray-400">Configure alert thresholds and notifications</p></div>
        <button onClick={saveSettings} disabled={saving} className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 px-6 py-2 rounded font-medium">{saving ? "Saving..." : "Save Settings"}</button>
      </div>

      {message && (
        <div className={`mb-6 p-4 rounded ${message.type === 'success' ? 'bg-green-900 border border-green-700 text-green-300' : 'bg-red-900 border border-red-700 text-red-300'}`}>
          {message.text}
        </div>
      )}

      {loading ? (
        <div className="text-center py-20"><div className="animate-spin text-4xl mb-4">*</div><p className="text-gray-400">Loading settings...</p></div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-bold mb-4">Alert Thresholds</h2>
            <p className="text-gray-400 text-sm mb-6">Alerts are triggered when resource usage exceeds these percentages</p>

            <div className="space-y-6">
              <div>
                <div className="flex justify-between mb-2"><label className="text-gray-300">CPU Threshold</label><span className="text-blue-400 font-bold">{settings.cpu_threshold}%</span></div>
                <input type="range" min="50" max="100" step="5" value={settings.cpu_threshold} onChange={e => updateSetting('cpu_threshold', parseInt(e.target.value))} className="w-full accent-blue-500" />
              </div>

              <div>
                <div className="flex justify-between mb-2"><label className="text-gray-300">Memory Threshold</label><span className="text-green-400 font-bold">{settings.memory_threshold}%</span></div>
                <input type="range" min="50" max="100" step="5" value={settings.memory_threshold} onChange={e => updateSetting('memory_threshold', parseInt(e.target.value))} className="w-full accent-green-500" />
              </div>

              <div>
                <div className="flex justify-between mb-2"><label className="text-gray-300">Disk Threshold</label><span className="text-yellow-400 font-bold">{settings.disk_threshold}%</span></div>
                <input type="range" min="50" max="100" step="5" value={settings.disk_threshold} onChange={e => updateSetting('disk_threshold', parseInt(e.target.value))} className="w-full accent-yellow-500" />
              </div>

              <div>
                <div className="flex justify-between mb-2"><label className="text-gray-300">Alert Cooldown</label><span className="text-gray-300">{settings.cooldown_minutes} minutes</span></div>
                <input type="range" min="5" max="60" step="5" value={settings.cooldown_minutes} onChange={e => updateSetting('cooldown_minutes', parseInt(e.target.value))} className="w-full" />
              </div>
            </div>
          </div>

          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h2 className="text-lg font-bold mb-4">Notification Settings</h2>
            <p className="text-gray-400 text-sm mb-6">Configure who receives alert notifications</p>

            <div className="space-y-6">
              <div>
                <label className="block text-gray-300 mb-2">Alert Recipients</label>
                <input type="text" value={settings.alert_recipients} onChange={e => updateSetting('alert_recipients', e.target.value)} placeholder="email1@example.com, email2@example.com" className="w-full bg-slate-900 border border-slate-600 rounded px-4 py-2 text-white focus:border-blue-500 focus:outline-none" />
                <p className="text-gray-500 text-xs mt-1">Separate multiple emails with commas</p>
              </div>

              <div className="flex items-center justify-between p-4 bg-slate-900 rounded">
                <div>
                  <label className="text-gray-300 font-medium">Enable Alerts</label>
                  <p className="text-gray-500 text-sm">Toggle all email notifications</p>
                </div>
                <button onClick={() => updateSetting('alerts_enabled', !settings.alerts_enabled)} className={`w-14 h-7 rounded-full relative transition-colors ${settings.alerts_enabled ? 'bg-blue-600' : 'bg-slate-600'}`}>
                  <span className={`absolute top-1 w-5 h-5 bg-white rounded-full transition-transform ${settings.alerts_enabled ? 'left-8' : 'left-1'}`}></span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <p className="text-center text-gray-500 text-sm mt-8">Changes take effect immediately after saving</p>
    </div>
  );
}

function App() {


// ═══ AGENT SECURITY LANDING PAGE ═══
function AgentSecurityPage() {
  const [summary, setSummary] = React.useState(null);
  const [trend, setTrend] = React.useState([]);
  const [gateway, setGateway] = React.useState(null);
  const [rotationStatus, setRotationStatus] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    Promise.all([
      fetch("/api/redteam").then(r => r.json()),
      fetch("/api/redteam/trend").then(r => r.json()),
      fetch("/api/redteam/gateway/david").then(r => r.json()).catch(() => null)
    ]).then(([redteamData, trendData, gatewayData]) => {
      setSummary(redteamData.summary || null);
      setTrend(trendData.trend || []);
      setGateway(gatewayData);
      setLoading(false);
    }).catch(() => setLoading(false));
    
    // Try to load credential rotation status (requires 2FA)
    fetch("/api/credentials/rotation-status")
      .then(r => r.ok ? r.json() : null)
      .then(d => setRotationStatus(d))
      .catch(() => {});
  }, []);

  const sev = summary?.last_severity || "unknown";
  const emoji = {critical:"🔴",high:"🟠",medium:"🟡",low:"🟢",clear:"✅"};
  const label = {critical:"CRITICAL",high:"HIGH RISK",medium:"MEDIUM",low:"LOW RISK",clear:"ALL CLEAR"};
  const border = {critical:"border-red-500",high:"border-orange-500",medium:"border-yellow-500",low:"border-green-500",clear:"border-green-600"};
  const lastScan = summary?.last_scan ? new Date(summary.last_scan).toLocaleString() : "Never";

  const trendColors = {clear:"#22c55e",low:"#84cc16",medium:"#eab308",high:"#f97316",critical:"#ef4444"};

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agent Security</h1>
        <p className="text-gray-400 text-sm mt-1">Security monitoring, vulnerability scanning, and compliance for AI agents</p>
      </div>

      <div className={"rounded-lg p-4 border-2 " + (border[sev] || "border-slate-700") + " bg-slate-800"}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-400">Overall Security Status</div>
            <div className="text-2xl font-bold mt-1">{emoji[sev] || "⚪"} {label[sev] || "UNKNOWN"}</div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-400">Last Scan</div>
            <div className="font-mono text-sm">{lastScan}</div>
          </div>
        </div>
      </div>

      {/* 7-Day Trend Chart */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <h2 className="text-lg font-semibold mb-3 text-gray-300">7-Day Security Trend</h2>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend} margin={{top:5,right:20,left:0,bottom:5}}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="day" stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} domain={[0,4]} ticks={[0,1,2,3,4]} 
                tickFormatter={(v) => ["Clear","Low","Med","High","Crit"][v] || ""} />
              <Tooltip 
                contentStyle={{backgroundColor:"#1e293b",border:"1px solid #475569",borderRadius:"8px"}}
                labelStyle={{color:"#f1f5f9"}}
                formatter={(value, name, props) => {
                  const sev = props.payload?.severity || "unknown";
                  return [sev.toUpperCase(), "Status"];
                }}
              />
              <Line type="monotone" dataKey="severity_score" stroke="#3b82f6" strokeWidth={2} 
                dot={{fill:"#3b82f6",r:4}} activeDot={{r:6}} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-4 mt-2 text-xs">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-500"></span> Clear</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-lime-500"></span> Low</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-500"></span> Medium</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-orange-500"></span> High</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500"></span> Critical</span>
        </div>
      </div>

      {/* David Gateway Uptime Indicator */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <h2 className="text-lg font-semibold mb-3 text-gray-300">David Gateway Status</h2>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={"w-4 h-4 rounded-full " + (gateway?.status === "online" ? "bg-green-500 animate-pulse" : gateway?.status === "degraded" ? "bg-yellow-500" : "bg-red-500")}></div>
            <div>
              <div className="font-semibold">{gateway?.status === "online" ? "Online" : gateway?.status === "degraded" ? "Degraded" : gateway?.status === "offline" ? "Offline" : "Unknown"}</div>
              <div className="text-xs text-gray-400">{gateway?.gateway_url || "192.168.65.241"}</div>
            </div>
          </div>
          <div className="text-right">
            {gateway?.uptime && <div className="text-sm text-gray-400">Uptime: {gateway.uptime.replace("up ", "")}</div>}
            {gateway?.services?.pm2_processes !== undefined && (
              <div className="text-xs text-gray-500">PM2: {gateway.services.online || 0}/{gateway.services.pm2_processes} processes</div>
            )}
            {gateway?.last_check && <div className="text-xs text-gray-500">Checked: {new Date(gateway.last_check).toLocaleTimeString()}</div>}
          </div>
        </div>
        {gateway?.error && <div className="mt-2 text-xs text-red-400">Error: {gateway.error}</div>}
      </div>

      {/* Credential Rotation Status */}
      {rotationStatus && (
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <h2 className="text-lg font-semibold mb-3 text-gray-300">Credential Rotation Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <div className="bg-slate-700 rounded p-3">
              <div className="text-xs text-gray-400">Total</div>
              <div className="text-xl font-mono">{rotationStatus.summary?.total || 0}</div>
            </div>
            <div className="bg-slate-700 rounded p-3">
              <div className="text-xs text-green-400">Healthy</div>
              <div className="text-xl font-mono text-green-400">{rotationStatus.summary?.healthy || 0}</div>
            </div>
            <div className="bg-slate-700 rounded p-3">
              <div className="text-xs text-yellow-400">Warning</div>
              <div className="text-xl font-mono text-yellow-400">{rotationStatus.summary?.warning || 0}</div>
            </div>
            <div className="bg-slate-700 rounded p-3">
              <div className="text-xs text-red-400">Critical</div>
              <div className="text-xl font-mono text-red-400">{rotationStatus.summary?.critical || 0}</div>
            </div>
          </div>
          {rotationStatus.recommendations?.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-2">Recommendations:</div>
              {rotationStatus.recommendations.slice(0, 3).map((rec, i) => (
                <div key={i} className={"text-xs p-2 rounded mb-1 " + (rec.priority === "high" ? "bg-red-900/30 text-red-300" : "bg-yellow-900/30 text-yellow-300")}>
                  {rec.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold mb-3 text-gray-300">Monitored Agents</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link to="/agent-security/redteam" className="bg-slate-800 rounded-lg p-5 border border-slate-700 hover:border-slate-500 transition-colors block no-underline text-white">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-lg">David Bishop</h3>
                <p className="text-gray-400 text-sm mt-1">OpenClaw AI - Sales & Marketing</p>
              </div>
              <span className={"px-2 py-1 rounded text-xs font-semibold " + (sev==="clear"?"bg-green-600":sev==="low"?"bg-green-500":sev==="medium"?"bg-yellow-600":sev==="high"?"bg-orange-500":sev==="critical"?"bg-red-600":"bg-slate-600")}>
                {(sev || "N/A").toUpperCase()}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3 mt-4">
              <div><div className="text-xs text-gray-500">Scans</div><div className="font-mono">{summary?.total_scans ?? 0}</div></div>
              <div><div className="text-xs text-gray-500">Vulns</div><div className="font-mono text-red-400">{summary?.last_vuln_count ?? 0}</div></div>
              <div><div className="text-xs text-gray-500">Updates</div><div className="font-mono text-blue-400">{summary?.last_update_count ?? 0}</div></div>
            </div>
            <div className="mt-3 text-xs text-gray-500">Red team: daily 4 AM - Click for dashboard</div>
          </Link>
          <div className="bg-slate-800/50 rounded-lg p-5 border border-slate-700 border-dashed">
            <h3 className="font-semibold text-lg text-gray-500">+ Future Agents</h3>
            <p className="text-gray-600 text-sm mt-1">Additional AI agents will appear here</p>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3 text-gray-300">Security Tools</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Link to="/agent-security/redteam" className="bg-slate-800 rounded-lg p-4 border border-slate-700 hover:border-slate-500 transition-colors no-underline text-white">
            <div className="text-sm font-semibold">Red Team Scans</div>
            <div className="text-xs text-gray-400 mt-1">Vuln probes, config drift, auth testing</div>
          </Link>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700 border-dashed">
            <div className="text-sm font-semibold text-gray-500">Audit Logs</div>
            <div className="text-xs text-gray-600 mt-1">Coming soon</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700 border-dashed">
            <div className="text-sm font-semibold text-gray-500">Compliance</div>
            <div className="text-xs text-gray-600 mt-1">Coming soon</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Red Team Dashboard Component
function RedTeamPage() {
  const [reports, setReports] = React.useState([]);
  const [summary, setSummary] = React.useState(null);
  const [trend, setTrend] = React.useState([]);
  const [selected, setSelected] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    Promise.all([
      fetch('/api/redteam?limit=30').then(r => r.json()),
      fetch('/api/redteam/trend').then(r => r.json())
    ]).then(([redteamData, trendData]) => {
      setReports(redteamData.reports || []);
      setSummary(redteamData.summary || null);
      setTrend(trendData.trend || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const sEmoji = { critical: '🔴', high: '🟠', medium: '🟡', low: '🟢', clear: '✅' };
  const sColor = { critical: 'bg-red-600', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-green-500', clear: 'bg-green-600' };

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">David Bishop - Red Team Dashboard</h1>
          <p className="text-gray-400 text-sm">Nightly vulnerability scans, update checks, feature monitoring</p>
        </div>
        <Link to="/agent-security" className="text-blue-400 hover:text-blue-300 text-sm">Back to Agent Security</Link>
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            ['Last Scan', summary.last_scan ? new Date(summary.last_scan).toLocaleDateString() : 'Never'],
            ['Status', (sEmoji[summary.last_severity] || '⚪') + ' ' + (summary.last_severity || 'N/A').toUpperCase()],
            ['Vulns', String(summary.last_vuln_count ?? 0)],
            ['Updates', String(summary.last_update_count ?? 0)],
            ['Total Scans', String(summary.total_scans ?? 0)]
          ].map(([label, val], i) => (
            <div key={i} className="bg-slate-800 rounded-lg p-3 border border-slate-700">
              <div className="text-xs text-gray-400">{label}</div>
              <div className="text-lg font-mono">{val}</div>
            </div>
          ))}
        </div>
      )}

      {/* 7-Day Trend Chart */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <h2 className="font-semibold mb-3">7-Day Vulnerability Trend</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend} margin={{top:5,right:30,left:0,bottom:5}}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="day" stroke="#9ca3af" fontSize={12} />
              <YAxis yAxisId="left" stroke="#9ca3af" fontSize={12} />
              <YAxis yAxisId="right" orientation="right" stroke="#9ca3af" fontSize={12} domain={[0,4]} 
                ticks={[0,1,2,3,4]} tickFormatter={(v) => ["Clr","Low","Med","Hi","Crit"][v] || ""} />
              <Tooltip 
                contentStyle={{backgroundColor:"#1e293b",border:"1px solid #475569",borderRadius:"8px"}}
                labelStyle={{color:"#f1f5f9"}}
              />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="vuln_count" name="Vulnerabilities" stroke="#ef4444" strokeWidth={2} dot={{r:4}} connectNulls={false} />
              <Line yAxisId="left" type="monotone" dataKey="update_count" name="Updates" stroke="#3b82f6" strokeWidth={2} dot={{r:4}} connectNulls={false} />
              <Line yAxisId="right" type="monotone" dataKey="severity_score" name="Severity" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={{r:3}} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <div className="p-3 border-b border-slate-700"><h2 className="font-semibold text-sm">Scan History</h2></div>
        {reports.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No scans yet. First scan runs at 4 AM.</div>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-400 border-b border-slate-700">
              <th className="p-2">Date</th><th className="p-2">Status</th><th className="p-2">Pass</th>
              <th className="p-2">Fail</th><th className="p-2">Vulns</th><th className="p-2">Updates</th>
            </tr></thead>
            <tbody>{reports.slice().reverse().map((r, i) => (
              <tr key={i} onClick={() => setSelected(selected?.date === r.date ? null : r)}
                  className="border-b border-slate-700/50 hover:bg-slate-700/50 cursor-pointer">
                <td className="p-2 font-mono">{r.date}</td>
                <td className="p-2">{sEmoji[r.severity]} {r.severity}</td>
                <td className="p-2 font-mono text-green-400">{r.passed}</td>
                <td className="p-2 font-mono text-red-400">{r.failed}</td>
                <td className="p-2 font-mono">{r.vulnerabilities?.length || 0}</td>
                <td className="p-2 font-mono">{r.updates_available?.length || 0}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>

      {selected && (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <div className="flex justify-between mb-3">
            <h2 className="font-semibold">Detail - {selected.date}</h2>
            <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-white">X</button>
          </div>
          {selected.vulnerabilities?.length > 0 && (
            <div className="mb-3">
              <h3 className="text-xs text-red-400 font-semibold mb-1">Vulnerabilities</h3>
              {selected.vulnerabilities.map((v, i) => (
                <div key={i} className="bg-slate-700 rounded p-2 mb-1 text-xs">
                  <span className={(v.severity === 'critical' ? 'bg-red-600' : v.severity === 'high' ? 'bg-orange-500' : 'bg-yellow-600') + " px-1.5 py-0.5 rounded text-xs mr-2"}>
                    {v.severity}</span>{v.description}
                </div>
              ))}
            </div>
          )}
          {selected.updates_available?.length > 0 && (
            <div className="mb-3">
              <h3 className="text-xs text-blue-400 font-semibold mb-1">Updates Available</h3>
              {selected.updates_available.map((u, i) => <div key={i} className="bg-slate-700 rounded p-2 mb-1 text-xs">{u}</div>)}
            </div>
          )}
          {selected.full_report && <pre className="bg-slate-700 rounded p-3 text-xs overflow-x-auto whitespace-pre-wrap max-h-80">{selected.full_report}</pre>}
        </div>
      )}
    </div>
  );
}

function FleetTopologyPage() {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetch('/api/infrastructure/servers')
      .then(r => r.json())
      .then(data => { setServers(data.servers || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const positions = {
    talos: { x: 300, y: 200 },
    agents: { x: 150, y: 80 },
    'rize-apps': { x: 450, y: 80 },
    demos: { x: 150, y: 320 },
    vector: { x: 450, y: 320 }
  };

  const getColor = (status) => {
    if (status === 'online' || status === 'ok') return '#22c55e';
    if (status === 'warning') return '#eab308';
    return '#ef4444';
  };

  const serverMap = {};
  servers.forEach(s => { serverMap[s.id] = s; });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Fleet Topology</h1>
      {loading ? (
        <div className="text-gray-400">Loading...</div>
      ) : (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <svg viewBox="0 0 600 400" className="w-full max-w-4xl mx-auto">
            {/* Connection lines from Talos to all */}
            {Object.keys(positions).filter(k => k !== 'talos').map(k => (
              <line key={k} x1={positions.talos.x} y1={positions.talos.y} 
                x2={positions[k].x} y2={positions[k].y}
                stroke="#475569" strokeWidth="2" strokeDasharray="5,5" />
            ))}
            
            {/* Server nodes */}
            {Object.entries(positions).map(([id, pos]) => {
              const server = serverMap[id] || { hostname: id, ip: '?', status: 'unknown' };
              const status = server.live?.status || server.status || 'unknown';
              return (
                <g key={id} transform={`translate(${pos.x - 60}, ${pos.y - 30})`}>
                  <rect width="120" height="60" rx="8" fill="#1e293b" stroke="#475569" strokeWidth="2" />
                  <circle cx="110" cy="10" r="6" fill={getColor(status)} />
                  <text x="60" y="22" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">
                    {server.hostname || id}
                  </text>
                  <text x="60" y="38" textAnchor="middle" fill="#94a3b8" fontSize="10">
                    {server.ip || ''}
                  </text>
                  <text x="60" y="52" textAnchor="middle" fill="#64748b" fontSize="9">
                    {server.role?.substring(0, 18) || ''}
                  </text>
                </g>
              );
            })}
          </svg>
          
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {servers.map(s => (
              <div key={s.id} className="bg-slate-700/50 rounded p-3 border border-slate-600">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold">{s.hostname}</span>
                  <StatusBadge status={s.live?.status || s.status} />
                </div>
                <div className="text-sm text-gray-400">{s.ip}</div>
                <div className="text-xs text-gray-500 mt-1">{s.description?.substring(0, 50)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


function SentinelPage() {
  // Use cache for instant loading - getCached returns pre-fetched data
  const cachedData = getCached("sentinelMaintenance");
  const [queue, setQueue] = useState(() => cachedData?.queue || []);
  const [history, setHistory] = useState(() => cachedData?.history || []);
  const [loading, setLoading] = useState(() => !cachedData);
  const [newItem, setNewItem] = useState({ service: '', action: 'restart', priority: 'P2', scheduled: '' });

  const fetchData = () => {
    refreshKey("sentinelMaintenance").then(data => {
      if (data) {
        setQueue(data.queue || []);
        setHistory(data.history || []);
      }
      setLoading(false);
    });
  };

  useEffect(() => {
    if (!cachedData) fetchData();
    else setLoading(false);
  }, []);

  const addItem = () => {
    if (!newItem.service) return;
    fetch('/api/sentinel/maintenance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newItem)
    }).then(() => { fetchData(); setNewItem({ service: '', action: 'restart', priority: 'P2', scheduled: '' }); });
  };

  const executeItem = (id) => {
    fetch(`/api/sentinel/maintenance/${id}/execute`, { method: 'POST' })
      .then(() => fetchData());
  };

  const cancelItem = (id) => {
    fetch(`/api/sentinel/maintenance/${id}`, { method: 'DELETE' })
      .then(() => fetchData());
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Sentinel - Maintenance Queue</h1>
      
      {/* Add New Item Form */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 mb-6">
        <h2 className="font-semibold mb-3">Schedule Maintenance</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <input type="text" placeholder="Service name" value={newItem.service}
            onChange={e => setNewItem({...newItem, service: e.target.value})}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white" />
          <select value={newItem.action} onChange={e => setNewItem({...newItem, action: e.target.value})}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white">
            <option value="restart">Restart</option>
            <option value="update">Update</option>
            <option value="backup">Backup</option>
            <option value="scan">Security Scan</option>
          </select>
          <select value={newItem.priority} onChange={e => setNewItem({...newItem, priority: e.target.value})}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white">
            <option value="P0">P0 - Critical</option>
            <option value="P1">P1 - High</option>
            <option value="P2">P2 - Medium</option>
            <option value="P3">P3 - Low</option>
          </select>
          <input type="datetime-local" value={newItem.scheduled}
            onChange={e => setNewItem({...newItem, scheduled: e.target.value})}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-white" />
          <button onClick={addItem} className="bg-blue-600 hover:bg-blue-700 rounded px-4 py-2 font-medium">
            Add to Queue
          </button>
        </div>
      </div>

      {/* Queue */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 mb-6">
        <h2 className="font-semibold mb-3">Pending Queue ({queue.length})</h2>
        {loading ? <div className="text-gray-400">Loading...</div> : queue.length === 0 ? (
          <div className="text-gray-500">No pending maintenance items</div>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-400 border-b border-slate-700">
              <th className="pb-2">Service</th><th className="pb-2">Action</th>
              <th className="pb-2">Priority</th><th className="pb-2">Scheduled</th><th className="pb-2">Actions</th>
            </tr></thead>
            <tbody>{queue.map(item => (
              <tr key={item.id} className="border-b border-slate-700/50">
                <td className="py-2">{item.service}</td>
                <td className="py-2">{item.action}</td>
                <td className="py-2"><PriorityBadge priority={item.priority} /></td>
                <td className="py-2 text-gray-400">{item.scheduled || 'ASAP'}</td>
                <td className="py-2 space-x-2">
                  <button onClick={() => executeItem(item.id)} className="bg-green-600 hover:bg-green-700 px-2 py-1 rounded text-xs">Execute</button>
                  <button onClick={() => cancelItem(item.id)} className="bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-xs">Cancel</button>
                </td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>

      {/* History */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <h2 className="font-semibold mb-3">History ({history.length})</h2>
        {history.length === 0 ? <div className="text-gray-500">No history</div> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-400 border-b border-slate-700">
              <th className="pb-2">Service</th><th className="pb-2">Action</th>
              <th className="pb-2">Status</th><th className="pb-2">Completed</th>
            </tr></thead>
            <tbody>{history.slice(0, 20).map(item => (
              <tr key={item.id} className="border-b border-slate-700/50">
                <td className="py-2">{item.service}</td>
                <td className="py-2">{item.action}</td>
                <td className="py-2"><StatusBadge status={item.status} /></td>
                <td className="py-2 text-gray-400">{item.completed}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}


    // Initialize global data cache on app mount
  useEffect(() => { initCache(); }, []);
  return (<BrowserRouter><Layout><Routes><Route path="/" element={<ServersPage />} /><Route path="/projects" element={<ProjectsPage />} /><Route path="/metrics" element={<MetricsPage />} /><Route path="/security" element={<SecurityPage />} /><Route path="/discovery" element={<DiscoveryPage />} /><Route path="/credentials" element={<CredentialsPage />} />
          <Route path="/settings" element={<SettingsPage />} /><Route path="/agent-security" element={<AgentSecurityPage />} /><Route path="/agent-security/redteam" element={<RedTeamPage />} /><Route path="/fleet-topology" element={<FleetTopologyPage />} /><Route path="/sentinel" element={<SentinelPage />} /><Route path="/tasks" element={<TasksPage />} /></Routes></Layout></BrowserRouter>);
}


function TasksPage() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [repoFilter, setRepoFilter] = useState("");
  const [sortBy, setSortBy] = useState("priority");
  const [repos, setRepos] = useState([]);
  const [total, setTotal] = useState(0);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ sort: sortBy });
      if (repoFilter) params.set("repo", repoFilter);
      const res = await fetch("/api/tasks?" + params.toString());
      const data = await res.json();
      setTasks(data.tasks || []);
      setTotal(data.total || 0);
      setRepos(data.available_repos || []);
    } catch (e) {
      console.error("Failed to fetch tasks:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTasks(); }, [repoFilter, sortBy]);

  const priorityColors = { critical: "bg-red-600", high: "bg-orange-500", medium: "bg-yellow-500", normal: "bg-blue-400", low: "bg-gray-500" };
  const repoShort = (r) => r ? r.split("/").pop() : "";

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Tasks ({total})</h1>
        <div className="flex gap-3 items-center">
          <select value={repoFilter} onChange={e => setRepoFilter(e.target.value)} className="bg-slate-700 text-white px-3 py-2 rounded text-sm border border-slate-600">
            <option value="">All Repos</option>
            {repos.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="bg-slate-700 text-white px-3 py-2 rounded text-sm border border-slate-600">
            <option value="priority">Sort: Priority</option>
            <option value="updated">Sort: Updated</option>
            <option value="repo">Sort: Repo</option>
          </select>
          <button onClick={fetchTasks} className="bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded text-sm font-medium">Refresh</button>
        </div>
      </div>

      {loading ? <div className="text-gray-400 text-center py-8">Loading tasks...</div> : (
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-gray-400 border-b border-slate-700 bg-slate-800/50">
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Repo</th>
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Labels</th>
              <th className="px-4 py-3">Assignee</th>
              <th className="px-4 py-3">Updated</th>
            </tr></thead>
            <tbody>{tasks.map((t, i) => (
              <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                <td className="px-4 py-2"><span className={`${priorityColors[t.priority] || "bg-gray-500"} px-2 py-0.5 rounded text-xs font-bold uppercase`}>{t.priority}</span></td>
                <td className="px-4 py-2 text-gray-300">{repoShort(t.repo)}</td>
                <td className="px-4 py-2 text-gray-400">#{t.number}</td>
                <td className="px-4 py-2">{t.url ? <a href={t.url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 hover:underline">{t.title}</a> : t.title}</td>
                <td className="px-4 py-2">{(t.labels || []).map((l, j) => <span key={j} className="bg-slate-600 px-1.5 py-0.5 rounded text-xs mr-1">{l}</span>)}</td>
                <td className="px-4 py-2 text-gray-400">{t.assignee || "-"}</td>
                <td className="px-4 py-2 text-gray-500 text-xs">{t.updated ? new Date(t.updated).toLocaleDateString() : "-"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}


export default App;