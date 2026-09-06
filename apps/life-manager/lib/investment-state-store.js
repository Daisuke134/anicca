"use strict";

const LIFECYCLES = new Set(["setup_required", "in_review", "approved", "active", "rejected", "action_required"]);
const DEPLOYMENTS = new Set(["local", "cloud"]);
const MODES = new Set(["paper", "shadow", "live"]);
const UID = /^[A-Za-z0-9._-]{1,200}$/;
const DIGEST = /^[a-f0-9]{64}$/;
const SECRET_REF = /^secret:\/\/alpaca\/[a-z0-9][a-z0-9._/-]{0,190}$/i;
const RECEIPT_REF = /^(?:provider-receipt|object):\/\/[a-z0-9._~:/?#@!$&'()*+,;=%-]{1,950}$/i;
const ROW_KEYS = Object.freeze([
  "alpaca_api_key_ref", "alpaca_api_secret_ref", "core_digest", "deployment", "killed",
  "lifecycle", "mode", "paused", "receipt_refs", "uid",
]);

function invalid() { throw new Error("investment state invalid"); }

function normalizeInvestmentState(value, expectedUid) {
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid();
  if (Object.keys(value).sort().join(",") !== [...ROW_KEYS].sort().join(",")) invalid();
  if (!UID.test(value.uid) || value.uid !== expectedUid) invalid();
  if (!LIFECYCLES.has(value.lifecycle) || !DEPLOYMENTS.has(value.deployment) || !MODES.has(value.mode)) invalid();
  if (typeof value.paused !== "boolean" || typeof value.killed !== "boolean") invalid();
  if (value.core_digest !== null && !DIGEST.test(value.core_digest)) invalid();
  if (!Array.isArray(value.receipt_refs) || value.receipt_refs.length > 100
    || value.receipt_refs.some((ref) => typeof ref !== "string" || !RECEIPT_REF.test(ref))) invalid();
  if (value.alpaca_api_key_ref !== null && !SECRET_REF.test(value.alpaca_api_key_ref)) invalid();
  if (value.alpaca_api_secret_ref !== null && !SECRET_REF.test(value.alpaca_api_secret_ref)) invalid();
  return Object.freeze({ ...value, receipt_refs: Object.freeze([...value.receipt_refs]) });
}

function createInvestmentStateStore({ supaUrl, supaKey, fetchImpl = fetch } = {}) {
  const base = String(supaUrl || "").replace(/\/$/, "");
  if (!base || !supaKey || typeof fetchImpl !== "function") throw new Error("investment state store unavailable");
  const headers = { apikey: supaKey, Authorization: `Bearer ${supaKey}` };
  return Object.freeze({
    async read(uid) {
      if (!UID.test(String(uid || ""))) invalid();
      const response = await fetchImpl(
        `${base}/rest/v1/lm_investment_states?uid=eq.${encodeURIComponent(uid)}&select=${ROW_KEYS.join(",")}&limit=1`,
        { headers },
      );
      if (!response.ok) throw new Error("investment state store unavailable");
      const rows = await response.json().catch(() => null);
      if (!Array.isArray(rows) || rows.length > 1) throw new Error("investment state store unavailable");
      return rows.length === 0 ? Object.freeze({ lifecycle: "setup_required" }) : normalizeInvestmentState(rows[0], uid);
    },

    async upsert(uid, state) {
      if (!UID.test(String(uid || ""))) invalid();
      const body = normalizeInvestmentState({ ...state, uid }, uid);
      const response = await fetchImpl(
        `${base}/rest/v1/lm_investment_states?on_conflict=uid&select=${ROW_KEYS.join(",")}`,
        {
        method: "POST",
        headers: { ...headers, "content-type": "application/json", Prefer: "resolution=merge-duplicates,return=representation" },
        body: JSON.stringify(body),
        },
      );
      if (!response.ok) throw new Error("investment state store unavailable");
      const rows = await response.json().catch(() => null);
      if (!Array.isArray(rows) || rows.length !== 1) throw new Error("investment state store unavailable");
      return normalizeInvestmentState(rows[0], uid);
    },
  });
}

module.exports = { createInvestmentStateStore, normalizeInvestmentState };
