"use strict";

// spec §5.2.1 — the phone is OPT-IN. Measured, it reached a human 3 times against 17 voicemails, and
// Telegram is what actually pushes someone out the door, so a user who has expressed no preference
// gets no call. Only `call_enabled` flipped: notifications and the daily automation are how the
// product now reaches everyone (§5.3), and they keep their opt-OUT semantics.
//
// A default alone cannot enforce this — a preference row that exists for some OTHER setting returns
// call_enabled as SQL NULL, which spreads straight over this object. Consumers must test `=== true`,
// never `!== false`. See scheduler.js wakeTick / wakeCallOnce.
const DEFAULTS = Object.freeze({ call_enabled: false, notifications_enabled: true, daily_automation_enabled: true });

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
