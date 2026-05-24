#!/usr/bin/env node
/**
 * Fetch RevenueCat overview (mobile MRR, active subs, churn).
 * Falls back to direct REST API if MCP unavailable (cron context).
 *
 * Auth: RC_API_KEY env var (V2 secret key sk_...).
 */

const RC_KEY = process.env.RC_API_KEY;
const fs = require('fs');
const path = require('path');
const config = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'config.json'), 'utf-8'));
const PROJECT_ID = config.rc_project_id;

(async () => {
  if (!RC_KEY) {
    // Fallback: cached snapshot from RevenueCat MCP (manually refreshed weekly)
    const fs = require('fs');
    const path = require('path');
    const snapshotPath = path.join(__dirname, '..', 'data', 'rc-snapshot.json');
    try {
      const snap = JSON.parse(fs.readFileSync(snapshotPath, 'utf-8'));
      console.log(JSON.stringify({
        mrr_usd: snap.mrr_usd,
        active_subscriptions: snap.active_subscriptions,
        active_trials: snap.active_trials,
        source: 'mcp_snapshot',
        snapshot_source: snap.snapshot_source,
        stale_after: snap.stale_after,
        fetched_at: new Date().toISOString()
      }, null, 2));
      return;
    } catch {
      console.log(JSON.stringify({
        mrr_usd: null,
        error: 'RC_API_KEY not set and no snapshot available',
        fetched_at: new Date().toISOString()
      }, null, 2));
      return;
    }
  }

  try {
    const res = await fetch(`https://api.revenuecat.com/v2/projects/${PROJECT_ID}/metrics/overview`, {
      headers: { 'Authorization': `Bearer ${RC_KEY}` }
    });
    if (!res.ok) {
      throw new Error(`RC ${res.status} ${await res.text()}`);
    }
    const data = await res.json();
    // RC v2 metrics shape: { metrics: [{ id, name, value, unit, period }] }
    const metrics = {};
    for (const m of (data.metrics || data.data || [])) {
      const k = m.id || m.name;
      metrics[k] = m.value;
    }
    console.log(JSON.stringify({
      mrr_usd: metrics.mrr || metrics.MRR || null,
      active_subscriptions: metrics.active_subscriptions || metrics.activeSubscriptions || null,
      active_trials: metrics.active_trials || metrics.activeTrials || null,
      raw: data,
      fetched_at: new Date().toISOString()
    }, null, 2));
  } catch (err) {
    console.error('fetch-rc warning:', err.message);
    console.log(JSON.stringify({
      mrr_usd: null,
      error: err.message,
      fetched_at: new Date().toISOString()
    }, null, 2));
  }
})();
