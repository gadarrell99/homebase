import { useState, useEffect } from "react";

const API_URL = "/api/servers";

function StatusBadge({ status }) {
  const colors = {
    online: "bg-green-500",
    offline: "bg-red-500",
    skip: "bg-gray-500",
  };
  return (
    <span className={`${colors[status] || "bg-gray-500"} px-2 py-1 rounded text-xs font-bold uppercase`}>
      {status}
    </span>
  );
}

function ProgressBar({ used, total, label }) {
  if (!total) return <span className="text-gray-500 text-sm">-</span>;
  const percent = Math.round((used / total) * 100);
  const color = percent > 80 ? "bg-red-500" : percent > 60 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>{label}</span>
        <span>{used}/{total} ({percent}%)</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${percent}%` }}></div>
      </div>
    </div>
  );
}

function ServerCard({ server }) {
  return (
    <div className="bg-slate-800 rounded-lg p-5 shadow-lg border border-slate-700 hover:border-slate-600 transition-colors">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-white">{server.name}</h3>
          <p className="text-gray-400 text-sm">{server.ip}</p>
        </div>
        <StatusBadge status={server.status} />
      </div>
      
      {server.status === "online" && (
        <div className="space-y-3 mb-4">
          <div className="text-sm text-gray-300">
            <span className="text-gray-500">Uptime:</span> {server.uptime || "-"}
          </div>
          <ProgressBar used={server.memory_used} total={server.memory_total} label="Memory (MB)" />
          <ProgressBar used={server.disk_used} total={server.disk_total} label="Disk (GB)" />
          {server.cpu_percent !== null && (
            <div className="text-sm text-gray-300">
              <span className="text-gray-500">CPU:</span> {server.cpu_percent.toFixed(1)}%
            </div>
          )}
        </div>
      )}
      
      {server.status === "skip" && (
        <p className="text-gray-500 text-sm mb-4">Windows host - SSH not available</p>
      )}
      
      {server.status === "offline" && (
        <p className="text-red-400 text-sm mb-4">Unable to connect</p>
      )}
      
      <div className="flex gap-2 mt-auto">
        {server.web_url && (
          <a
            href={`https://${server.web_url}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-center py-2 px-3 rounded text-sm font-medium transition-colors"
          >
            Web
          </a>
        )}
        {server.ssh_url && (
          <a
            href={`ssh://${server.ssh_url}`}
            className="flex-1 bg-slate-600 hover:bg-slate-500 text-white text-center py-2 px-3 rounded text-sm font-medium transition-colors"
          >
            SSH
          </a>
        )}
      </div>
    </div>
  );
}

function App() {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const fetchServers = async () => {
    try {
      const res = await fetch(API_URL);
      const data = await res.json();
      setServers(data.servers);
      setLastUpdate(new Date());
      setError(null);
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

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      <header className="max-w-7xl mx-auto mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Homebase</h1>
            <p className="text-gray-400">Infrastructure Dashboard</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-green-400">{onlineCount}/{totalCount}</div>
            <div className="text-gray-400 text-sm">servers online</div>
            {lastUpdate && (
              <div className="text-gray-500 text-xs mt-1">
                Updated: {lastUpdate.toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto">
        {loading ? (
          <div className="text-center py-20">
            <div className="animate-spin text-4xl mb-4">*</div>
            <p className="text-gray-400">Loading server data...</p>
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-400">{error}</p>
            <button 
              onClick={fetchServers}
              className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {servers.map((server) => (
              <ServerCard key={server.name} server={server} />
            ))}
          </div>
        )}
      </main>

      <footer className="max-w-7xl mx-auto mt-8 text-center text-gray-500 text-sm">
        Auto-refreshes every 30 seconds
      </footer>
    </div>
  );
}

export default App;
