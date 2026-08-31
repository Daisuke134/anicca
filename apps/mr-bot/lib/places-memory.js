"use strict";
// lib/places-memory.js — PHASE C / PC-1 (C3 ask→remember): per-user remembered locations so a recurring
// vague event ("Lunch with Mai", "おばあちゃんの家") is asked ONCE then auto-filled from memory. Supabase
// lm_user_places (NOT mem0 — pooled-compatible, no new dep). The key is a DETERMINISTIC normalization of the
// event summary (bookkeeping, like lm_ask_log keys by event_id) — NOT the regex-for-judgment anti-pattern.

// placeKey(summary) → normalized phrase. PURE: lowercase, collapse internal whitespace, trim. Empty → "".
function placeKey(summary, recurringEventId) {
  if (recurringEventId) return `series:${String(recurringEventId).trim()}`;
  return String(summary || "").toLowerCase().replace(/\s+/g, " ").trim();
}

function hdr(key, extra) {
  return Object.assign({ apikey: key, Authorization: `Bearer ${key}` }, extra || {});
}

// recallPlace(uid, phrase) → remembered address | null. Missing phrase/uid/creds → null (no memory).
// TTL (FIND-002): only memory UPDATED within ttlDays (default LM_PLACE_TTL_DAYS or 90) is recalled — so a
// stale memory expires, the event is asked again, and the answer refreshes it (a venue can change). ttlDays<=0
// disables the bound. This is the in-product staleness-refresh path that a permanent pin would block.
async function recallPlace(uid, phrase, supaUrl, supaKey, fetchImpl, ttlDays) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey || !uid || !phrase) return null;
  const days = Number(ttlDays != null ? ttlDays : (process.env.LM_PLACE_TTL_DAYS || 90));
  let url = `${supaUrl}/rest/v1/lm_user_places?uid=eq.${encodeURIComponent(uid)}&phrase=eq.${encodeURIComponent(phrase)}&select=address&limit=1`;
  if (days > 0) {
    const since = new Date(Date.now() - days * 86400 * 1000).toISOString();
    url += `&updated_at=gt.${encodeURIComponent(since)}`;
  }
  const r = await f(url, { headers: hdr(supaKey) }).catch(() => null);
  if (!r || !r.ok) return null;
  const d = await r.json().catch(() => []);
  return Array.isArray(d) && d[0] && d[0].address ? d[0].address : null;
}

// rememberPlace(uid, phrase, address) → bool. Upsert (POST, resolution=merge-duplicates on UNIQUE(uid,phrase)).
// No-op (false) if any arg is missing — never stores an empty memory.
async function rememberPlace(uid, phrase, address, supaUrl, supaKey, fetchImpl) {
  const f = fetchImpl || fetch;
  if (!supaUrl || !supaKey || !uid || !phrase || !address) return false;
  // on_conflict=uid,phrase tells PostgREST WHICH unique constraint to upsert on — without it a 2nd write for
  // the same (uid,phrase) hits the unique violation (409) instead of merging/updating (caught by live E2E).
  const r = await f(`${supaUrl}/rest/v1/lm_user_places?on_conflict=uid,phrase`, {
    method: "POST",
    headers: hdr(supaKey, { "Content-Type": "application/json", Prefer: "resolution=merge-duplicates,return=minimal" }),
    body: JSON.stringify({ uid, phrase, address, updated_at: new Date().toISOString() }),
  }).catch(() => null);
  return !!r && (r.status === 201 || r.status === 200 || r.status === 204);
}

module.exports = { placeKey, recallPlace, rememberPlace };
