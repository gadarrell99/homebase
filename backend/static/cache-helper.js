/**
 * Homebase Cache-First Pattern Utility
 * Shows pre-cached data immediately, refreshes in background.
 * Usage: initCacheFirst('key', 'containerId', loadFn, intervalMs)
 */
function initCacheFirst(key, containerId, loadFn, intervalMs) {
    var TTL = 300000; // 5 minutes
    var el = containerId ? document.getElementById(containerId) : null;

    // Restore cached HTML immediately
    try {
        var raw = sessionStorage.getItem(key);
        if (raw) {
            var obj = JSON.parse(raw);
            if (Date.now() - obj.ts < TTL && el) {
                el.innerHTML = obj.html;
            }
        }
    } catch(e) {}

    // Save cache after successful load
    function saveCache() {
        try {
            var target = containerId ? document.getElementById(containerId) : null;
            if (target && target.innerHTML && target.innerHTML.indexOf('Loading') === -1) {
                sessionStorage.setItem(key, JSON.stringify({ html: target.innerHTML, ts: Date.now() }));
            }
        } catch(e) {}
    }

    // Load fresh data in background
    try {
        var p = loadFn();
        if (p && typeof p.then === 'function') {
            p.then(saveCache).catch(function(){});
        }
    } catch(e) {}

    // Periodic refresh
    if (intervalMs > 0) {
        setInterval(function() {
            try {
                var p = loadFn();
                if (p && typeof p.then === 'function') {
                    p.then(saveCache).catch(function(){});
                }
            } catch(e) {}
        }, intervalMs);
    }
}
