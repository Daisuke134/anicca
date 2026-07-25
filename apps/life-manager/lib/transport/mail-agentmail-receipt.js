"use strict";
// CORE-8e recipient-side delivery proof.
//
// Resend answers a send with its OWN queue id (lib/mail-resend.js), which proves acceptance, not arrival.
// The DAILY journey's done condition needs the real RFC Message-ID of the late notice as it landed in the
// recipient mailbox. makeGogMail().findReceipt does that for a Gmail-readable mailbox; this is its sibling
// for an AgentMail-hosted inbox, which we can read over an API instead of needing the recipient's Gmail auth.
//
// Same contract as makeGogMail().findReceipt: fail closed on anything unproven, and return only safe
// metadata — never a body, an address, or a subject line.
const API_BASE = "https://api.agentmail.to/v0";
const NONCE_PATTERN = /^[a-f0-9]{16,64}$/i;

// A single instant, expressed as an interval so callers can share one comparison shape across providers
// (gog only knows the minute an message landed in; AgentMail gives an exact timestamp).
function receivedInterval(message) {
  const raw = String((message && (message.timestamp || message.created_at)) || "");
  const instantMs = Date.parse(raw);
  return Number.isFinite(instantMs) ? { lowerMs: instantMs, upperMs: instantMs } : null;
}

function makeAgentMailReceipt({ apiKey, inbox, fetchImpl, limit = 20 } = {}) {
  const key = String(apiKey || "");
  const box = String(inbox || "");
  const f = fetchImpl || fetch;

  return {
    kind: "agentmail",
    ready: () => Boolean(key && box),
    async findReceipt({ nonce, afterMs, signal } = {}) {
      if (!key || !box) return null;
      if (!NONCE_PATTERN.test(String(nonce || ""))) return null;
      const after = Number.isFinite(afterMs) ? afterMs : 0;
      try {
        const url = `${API_BASE}/inboxes/${encodeURIComponent(box)}/messages?limit=${limit}`;
        const response = await f(url, { headers: { Authorization: `Bearer ${key}` }, signal });
        if (!response || !response.ok) return null;
        const payload = await response.json().catch(() => ({}));
        const messages = Array.isArray(payload && payload.messages)
          ? payload.messages
          : (Array.isArray(payload) ? payload : []);
        for (const message of messages) {
          const haystack = `${(message && message.subject) || ""}\n${(message && message.preview) || ""}`;
          if (!haystack.includes(nonce)) continue;
          const interval = receivedInterval(message);
          if (!interval || interval.upperMs < after) continue;
          // No RFC Message-ID means we cannot satisfy the done condition, so this is not a receipt.
          const rfcMessageId = String((message && message.smtp_id) || "");
          if (!rfcMessageId) continue;
          return {
            id: String((message && message.message_id) || ""),
            rfcMessageId,
            matchedNonce: String(nonce),
            receivedAtLowerMs: interval.lowerMs,
            receivedAtUpperMs: interval.upperMs,
          };
        }
      } catch {}
      return null;
    },
  };
}

module.exports = { makeAgentMailReceipt };
