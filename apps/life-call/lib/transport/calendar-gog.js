// lib/transport/calendar-gog.js — LOCAL calendar transport (#74 slice4). BYOK: drives the user's own
// `gog` CLI (gog 0.17.0) against their own Google account/keychain — no Composio. Same adapter interface
// as calendar-composio.js, so the SAME life-logic runs locally with LIFE_TRANSPORT=gog. `run` is
// injectable (execFileSync by default) for unit tests. uid is ignored — gog acts on the configured account.
"use strict";

const { execFileSync } = require("node:child_process");

function isoZ(ms) {
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function makeGogCalendar({ bin, account, keyring, calId = "primary", run } = {}) {
  const gogBin = bin || process.env.GOG_BIN || "gog";
  const acct = account || process.env.GOG_ACCOUNT || "";
  const keyringPwd = keyring != null ? keyring : (process.env.GOG_KEYRING_PASSWORD || "");
  // every gog call appends --account; gog flags are order-independent (verified gog 0.17.0).
  const exec = run || ((args, timeout = 60000) =>
    execFileSync(gogBin, [...args, "--account", acct], {
      env: { ...process.env, GOG_KEYRING_PASSWORD: keyringPwd, GOG_ACCOUNT: acct },
      encoding: "utf8", timeout,
    }));

  return {
    kind: "gog",
    ready: () => !!acct,
    // Raw Google-Calendar-shaped items for [timeMin, timeMax]. gog --from/--to accept RFC3339 directly.
    async listEventsRaw(_uid, { timeMin, timeMax, maxResults } = {}) {
      if (!acct) return [];
      const args = ["calendar", "events", "list", "-j", "--all-pages", "--max", String(maxResults || 250)];
      if (timeMin) args.push("--from", timeMin);
      if (timeMax) args.push("--to", timeMax);
      try {
        const d = JSON.parse(exec(args));
        return Array.isArray(d) ? d : (d.events || d.items || []);
      } catch { return []; }
    },
    // Accepts the same arg shape travel.js builds (Composio dialect) and translates to gog flags.
    async createEvent(_uid, args = {}) {
      if (!acct) return { successful: false };
      const startMs = Date.parse(/Z$/.test(args.start_datetime || "") ? args.start_datetime : `${args.start_datetime}Z`);
      if (!Number.isFinite(startMs)) return { successful: false };
      const durMs = ((args.event_duration_hour || 0) * 60 + (args.event_duration_minutes || 0)) * 60000;
      const a = ["calendar", "create", args.calendar_id || calId, "-j",
        "--summary", args.summary || "予定",
        "--from", isoZ(startMs), "--to", isoZ(startMs + durMs)];
      if (args.location) a.push("--location", args.location);
      if (args.description) a.push("--description", args.description);
      try { exec(a, 30000); return { successful: true }; } catch { return { successful: false }; }
    },
    // Accepts {calendar_id, event_id, location, ...} (Composio dialect) → gog calendar update.
    async patchEvent(_uid, args = {}) {
      if (!acct || !args.event_id) return { successful: false };
      const a = ["calendar", "update", args.calendar_id || calId, args.event_id, "-j"];
      if (args.location != null) a.push("--location", args.location);
      if (args.summary != null) a.push("--summary", args.summary);
      try { exec(a, 30000); return { successful: true }; } catch { return { successful: false }; }
    },
  };
}

module.exports = { makeGogCalendar };
