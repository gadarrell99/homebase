// Central pre-cache for all Homebase pages
// Fires on app load, refreshes every 60s
// Pages read from cache first, then background refresh

const CACHE = {};
const LISTENERS = new Set();
const REFRESH_INTERVAL = 60000; // 60 seconds

const ENDPOINTS = {
  servers: "/api/servers",
  metrics: "/api/metrics/history?hours=24&interval=30",
  metricsSummary: "/api/metrics/summary?hours=24",
  security: "/api/security/scan",
  projects: "/api/projects",
  credentials: "/api/credentials",
  settings: "/api/settings",
  logs: "/api/discovery/logs?limit=100",
  sentinelOverview: "/api/sentinel/overview",
  sentinelAlerts: "/api/sentinel/alerts",
  sentinelAudit: "/api/sentinel/audit-log",
  sentinelCrons: "/api/sentinel/crons",
  sentinelMaintenance: "/api/sentinel/maintenance",
  infrastructure: "/api/infrastructure",
  briefing: "/api/briefing/latest",
  agents: "/api/cheat-sheet/agents"
};

let initialized = false;
let refreshTimer = null;

async function fetchAll() {
  const promises = Object.entries(ENDPOINTS).map(async ([key, url]) => {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        CACHE[key] = { data, timestamp: Date.now(), loading: false, error: null };
      } else {
        CACHE[key] = { ...CACHE[key], loading: false, error: `HTTP ${res.status}` };
      }
    } catch (e) {
      console.warn(`Cache fetch failed: ${key}`, e.message);
      CACHE[key] = { ...CACHE[key], loading: false, error: e.message };
    }
  });
  await Promise.allSettled(promises);
  LISTENERS.forEach(fn => fn({ ...CACHE }));
}

export function initCache() {
  if (initialized) return;
  initialized = true;
  console.log("[DataCache] Initializing pre-cache for all pages...");
  fetchAll();
  refreshTimer = setInterval(fetchAll, REFRESH_INTERVAL);
}

export function getCached(key) {
  return CACHE[key]?.data || null;
}

export function getTimestamp(key) {
  return CACHE[key]?.timestamp || null;
}

export function getCacheAge(key) {
  const ts = CACHE[key]?.timestamp;
  return ts ? Math.round((Date.now() - ts) / 1000) : null;
}

export function subscribe(fn) {
  LISTENERS.add(fn);
  fn({ ...CACHE }); // immediate callback with current state
  return () => LISTENERS.delete(fn);
}

export function refreshKey(key) {
  const url = ENDPOINTS[key];
  if (!url) return Promise.resolve(null);
  CACHE[key] = { ...CACHE[key], loading: true };
  return fetch(url)
    .then(r => r.json())
    .then(data => {
      CACHE[key] = { data, timestamp: Date.now(), loading: false, error: null };
      LISTENERS.forEach(fn => fn({ ...CACHE }));
      return data;
    })
    .catch(e => {
      CACHE[key] = { ...CACHE[key], loading: false, error: e.message };
      LISTENERS.forEach(fn => fn({ ...CACHE }));
      return null;
    });
}

export function refreshAll() {
  return fetchAll();
}

// Export endpoints for reference
export const CACHE_KEYS = Object.keys(ENDPOINTS);
