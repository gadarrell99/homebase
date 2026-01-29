import { useState, useEffect } from "react";
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
  return <div className="min-h-screen bg-slate-900 text-white"><nav className="bg-slate-800 border-b border-slate-700"><div className="max-w-7xl mx-auto px-6 py-4"><div className="flex items-center justify-between"><Link to="/" className="text-xl font-bold">Homebase</Link><div className="flex gap-2"><NavLink to="/">Servers</NavLink><NavLink to="/projects">Projects</NavLink><NavLink to="/metrics">Metrics</NavLink><NavLink to="/security">Security</NavLink><NavLink to="/discovery">Discovery</NavLink></div></div></div></nav><main className="max-w-7xl mx-auto p-6">{children}</main></div>;
}

function ServerCard({ server }) {
  return <div className="bg-slate-800 rounded-lg p-5 shadow-lg border border-slate-700 hover:border-slate-600 transition-colors"><div className="flex justify-between items-start mb-4"><div><h3 className="text-xl font-bold text-white">{server.name}</h3><p className="text-gray-400 text-sm">{server.ip}</p></div><StatusBadge status={server.status} /></div>{server.status === "online" && <div className="space-y-3 mb-4"><div className="text-sm text-gray-300"><span className="text-gray-500">Uptime:</span> {server.uptime || "-"}</div><ProgressBar used={server.memory_used} total={server.memory_total} label="Memory (MB)" /><ProgressBar used={server.disk_used} total={server.disk_total} label="Disk (GB)" />{server.cpu_percent !== null && <div className="text-sm text-gray-300"><span className="text-gray-500">CPU:</span> {server.cpu_percent.toFixed(1)}%</div>}</div>}{server.status === "skip" && <p className="text-gray-500 text-sm mb-4">Windows host - SSH not available</p>}{server.status === "offline" && <p className="text-red-400 text-sm mb-4">Unable to connect</p>}<div className="flex gap-2 mt-auto">{server.web_url && <a href={`https://${server.web_url}`} target="_blank" rel="noopener noreferrer" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-center py-2 px-3 rounded text-sm font-medium transition-colors">Web</a>}{server.ssh_url && <a href={`ssh://${server.ssh_url}`} className="flex-1 bg-slate-600 hover:bg-slate-500 text-white text-center py-2 px-3 rounded text-sm font-medium transition-colors">SSH</a>}</div></div>;
}

function ServersPage() {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const fetchServers = async () => {
    try {
      const res = await fetch("/api/servers");
      const data = await res.json();
      setServers(data.servers);
      setLastUpdate(new Date());
      setError(null);
      fetch("/api/metrics/record", { method: "POST" }).catch(() => {});
    } catch (err) {
      setError("Failed to fetch server data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
    const interval = setInterval(fetchServers, 30000);
    return () => clearInterval(interval);
  }, []);

  const onlineCount = servers.filter(s => s.status === "online").length;
  const totalCount = servers.filter(s => s.status !== "skip").length;

  return <div><div className="flex justify-between items-center mb-6"><div><h1 className="text-2xl font-bold">Servers</h1><p className="text-gray-400">Infrastructure monitoring</p></div><div className="text-right"><div className="text-2xl font-bold text-green-400">{onlineCount}/{totalCount}</div><div className="text-gray-400 text-sm">servers online</div>{lastUpdate && <div className="text-gray-500 text-xs mt-1">Updated: {lastUpdate.toLocaleTimeString()}</div>}</div></div>{loading ? <div className="text-center py-20"><div className="animate-spin text-4xl mb-4">*</div><p className="text-gray-400">Loading server data...</p></div> : error ? <div className="text-center py-20"><p className="text-red-400">{error}</p><button onClick={fetchServers} className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Retry</button></div> : <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">{servers.map(server => <ServerCard key={server.name} server={server} />)}</div>}<p className="text-center text-gray-500 text-sm mt-8">Auto-refreshes every 30 seconds</p></div>;
}

function MetricsPage() {
  const [metricsData, setMetricsData] = useState({});
  const [summary, setSummary] = useState({});
  const [selectedServer, setSelectedServer] = useState(null);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(true);
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
  const [securityData, setSecurityData] = useState([]);
  const [loading, setLoading] = useState(true);
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
        {project.docs && project.docs.map(doc => (<span key={doc} className="bg-slate-700 text-gray-300 px-2 py-0.5 rounded text-xs" title={doc}>{docIcons[doc] || doc}</span>))}
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
  const [projects, setProjects] = useState([]);
  const [health, setHealth] = useState({});
  const [loading, setLoading] = useState(true);
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
    </div>
  );
}

function DiscoveryPage() {
  const [projects, setProjects] = useState([]);
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

function App() {
  return (<BrowserRouter><Layout><Routes><Route path="/" element={<ServersPage />} /><Route path="/projects" element={<ProjectsPage />} /><Route path="/metrics" element={<MetricsPage />} /><Route path="/security" element={<SecurityPage />} /><Route path="/discovery" element={<DiscoveryPage />} /></Routes></Layout></BrowserRouter>);
}

export default App;