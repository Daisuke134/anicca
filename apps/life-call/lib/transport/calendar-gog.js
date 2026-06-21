// lib/transport/calendar-gog.js — LOCAL calendar transport (#74 slice4). BYOK: drives the user's own
// `gog` CLI (gog 0.17.0) against their own Google account/keychain — no Composio. Same adapter interface
// as calendar-composio.js, so the SAME life-logic runs locally with LIFE_TRANSPORT=gog. `run` is
// injectable (execFileSync by default) for unit tests. uid is ignored — gog acts on the configured account.
"use strict";

const { execFileSync } = require("node:child_process");

function isoZ(ms) {
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

// argv-injection guard: a value starting with "-" could be parsed by gog as a FLAG, not data.
// Positionals (calendarId, eventId) never legitimately start with "-" → reject. Option values are
// passed as a single glued `--flag=value` token (see opt()) so a leading "-" can never smuggle a flag.
const isFlaglike = (s) => /^-/.test(String(s == null ? "" : s));
const opt = (flag, value) => `${flag}=${value}`;

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
      const args = ["calendar", "events", "list", "-j", "--all-pages", opt("--max", String(maxResults || 250))];
      if (timeMin) args.push(opt("--from", timeMin)); // ISO (RFC3339) — never flag-like
      if (timeMax) args.push(opt("--to", timeMax));
      try {
        const d = JSON.parse(exec(args));
        return Array.isArray(d) ? d : (d.events || d.items || []);
      } catch { return []; }
    },
    // Accepts the same arg shape travel.js builds (Composio dialect) and translates to gog flags.
    async createEvent(_uid, args = {}) {
      if (!acct) return { successful: false };
      const cal2 = args.calendar_id || calId;
      if (isFlaglike(cal2)) return { successful: false }; // positional can't start with "-"
      const startMs = Date.parse(/Z$/.test(args.start_datetime || "") ? args.start_datetime : `${args.start_datetime}Z`);
      if (!Number.isFinite(startMs)) return { successful: false };
      const durMs = ((args.event_duration_hour || 0) * 60 + (args.event_duration_minutes || 0)) * 60000;
      const a = ["calendar", "create", cal2, "-j",
        opt("--summary", args.summary || "予定"),
        opt("--from", isoZ(startMs)), opt("--to", isoZ(startMs + durMs))];
      if (args.location) a.push(opt("--location", args.location));
      if (args.description) a.push(opt("--description", args.description));
      try { exec(a, 30000); return { successful: true }; } catch { return { successful: false }; }
    },
    // Accepts {calendar_id, event_id, location, ...} (Composio dialect) → gog calendar update.
    async patchEvent(_uid, args = {}) {
      if (!acct || !args.event_id) return { successful: false };
      const cal2 = args.calendar_id || calId;
      if (isFlaglike(cal2) || isFlaglike(args.event_id)) return { successful: false }; // positionals
      const a = ["calendar", "update", cal2, args.event_id, "-j"];
      if (args.location != null) a.push(opt("--location", args.location));
      if (args.summary != null) a.push(opt("--summary", args.summary));
      try { exec(a, 30000); return { successful: true }; } catch { return { successful: false }; }
    },
  };
}

module.exports = { makeGogCalendar };
