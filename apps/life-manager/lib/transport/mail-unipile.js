// lib/transport/mail-unipile.js — CLOUD mail transport (#74). Wraps Unipile (send + inbox read) behind
// the mail adapter interface so ask.js/notify.js never touch a provider directly. Local will swap in
// mail-gog.js. Behaviour-identical to the inline Unipile calls it replaces.
"use strict";

function makeUnipileMail({ accountId, token, dsn } = {}) {
  const base = dsn ? `https://${dsn}` : "";
  const headers = { "X-API-KEY": token, "Content-Type": "application/json", accept: "application/json" };
  return {
    kind: "unipile",
    ready: () => !!(accountId && token && dsn),
    // Send an email FROM the user's connected Gmail. Returns boolean ok.
    async send(to, subject, body) {
      if (!accountId || !token || !dsn) return false;
      try {
        const r = await fetch(`${base}/api/v1/emails`, {
          method: "POST", headers,
          body: JSON.stringify({ account_id: accountId, to: [{ identifier: to }], subject, body }),
        });
        return r.ok;
      } catch { return false; }
    },
    // Recent inbox messages (for reading location replies). Returns the raw items array.
    async listInbox({ limit = 15 } = {}) {
      if (!accountId || !token || !dsn) return [];
      try {
        const r = await fetch(`${base}/api/v1/emails?account_id=${encodeURIComponent(accountId)}&limit=${limit}`, { headers });
        const j = await r.json().catch(() => ({}));
        return j.items || [];
      } catch { return []; }
    },
    // Free-text subject/body search used only as optional context for search-before-ask.
    async searchInbox(query, { limit = 10 } = {}) {
      if (!accountId || !token || !dsn || !query) return [];
      try {
        const qs = new URLSearchParams({ account_id: accountId, limit: String(limit), search: query });
        const r = await fetch(`${base}/api/v1/emails?${qs}`, { headers });
        const j = await r.json().catch(() => ({}));
        return j.items || [];
      } catch { return []; }
    },
  };
}

module.exports = { makeUnipileMail };
