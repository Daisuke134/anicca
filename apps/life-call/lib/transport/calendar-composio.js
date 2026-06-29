// lib/transport/calendar-composio.js — CLOUD calendar transport (#74 convergence). Wraps the Composio
// managed-OAuth GOOGLECALENDAR_* tools behind the adapter interface every life-logic module will use,
// so the same JS runs cloud (this) or local (calendar-gog.js, slice 5). Behaviour-identical to the
// inline Composio calls it replaces — the live caller is unchanged.
"use strict";

const COMPOSIO_EXEC = "https://backend.composio.dev/api/v3/tools/execute";

async function exec(tool, uid, args, apiKey) {
  const r = await fetch(`${COMPOSIO_EXEC}/${tool}`, {
    method: "POST",
    headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: uid, arguments: args }),
  });
  return r.json();
}

function makeComposioCalendar({ apiKey } = {}) {
  const key = apiKey || process.env.COMPOSIO_API_KEY;
  return {
    kind: "composio",
    ready: () => !!key,
    // Raw Google Calendar items (each consumer maps to its own shape) for [timeMin, timeMax] (ISO Z).
    async listEventsRaw(uid, { timeMin, timeMax, maxResults } = {}) {
      if (!key || !uid) return [];
      const args = { calendarId: "primary", singleEvents: true, orderBy: "startTime", timeMin, timeMax };
      if (maxResults) args.maxResults = maxResults;
      let j;
      try {
        j = await exec("GOOGLECALENDAR_EVENTS_LIST", uid, args, key);
      } catch { return []; }
      if (!j || !j.successful) return [];
      const d = j.data || {};
      return d.items || d.events || [];
    },
    async createEvent(uid, args) {
      if (!key) return { successful: false };
      try { return await exec("GOOGLECALENDAR_CREATE_EVENT", uid, args, key); } catch { return { successful: false }; }
    },
    async patchEvent(uid, args) {
      if (!key) return { successful: false };
      try { return await exec("GOOGLECALENDAR_PATCH_EVENT", uid, args, key); } catch { return { successful: false }; }
    },
  };
}

module.exports = { makeComposioCalendar };
