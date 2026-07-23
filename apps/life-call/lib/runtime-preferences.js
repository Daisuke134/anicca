"use strict";

const DEFAULTS = Object.freeze({ call_enabled: true, notifications_enabled: true, daily_automation_enabled: true });

async function readRuntimePreferences(uid, opts = {}) {
  if (!uid || !opts.supaUrl || !opts.supaKey) return null;
  const response = await (opts.fetchImpl || fetch)(`${String(opts.supaUrl).replace(/\/$/, "")}/rest/v1/lm_panel_preferences?uid=eq.${encodeURIComponent(uid)}&select=call_enabled,notifications_enabled,daily_automation_enabled&limit=1`, {
    headers: { apikey: opts.supaKey, Authorization: `Bearer ${opts.supaKey}` },
  }).catch(() => null);
  if (!response || !response.ok) return null;
  const rows = await response.json().catch(() => null);
  if (!Array.isArray(rows)) return null;
  return { ...DEFAULTS, ...(rows[0] || {}) };
}

module.exports = { DEFAULTS, readRuntimePreferences };
