// lib/transport/calendar-composio.js — CLOUD calendar transport (#74 convergence). Wraps the Composio
// managed-OAuth GOOGLECALENDAR_* tools behind the adapter interface every life-logic module will use,
// so the same JS runs cloud (this) or local (calendar-gog.js, slice 5). Behaviour-identical to the
// inline Composio calls it replaces — the live caller is unchanged.
"use strict";
const crypto = require("node:crypto");
const { recordComposioOperation } = require("../provider-cost-adapters.js");
const { authorizeProviderOperation: authorizeBudget } = require("../provider-budget.js");

const COMPOSIO_EXEC = "https://backend.composio.dev/api/v3/tools/execute";
const COMPOSIO_EXEC_V31 = "https://backend.composio.dev/api/v3.1/tools/execute";
// Proxy Execute is the only Composio route that can send a caller-generated
// Google event id.  Keep this separate from the managed-tool endpoint above:
// the proxy contract uses v3.1 and returns the upstream HTTP status in the
// response body (Composio itself may still answer HTTP 200).
const COMPOSIO_PROXY_EXEC = "https://backend.composio.dev/api/v3.1/tools/execute/proxy";

async function exec(tool, uid, args, apiKey, fetchImpl = globalThis.fetch, connectedAccountId = null, endpoint = COMPOSIO_EXEC) {
  const payload = { user_id: uid, arguments: args };
  // A mobile Calendar connection is routed by the exact provider account returned by
  // Composio's callback.  Keep the legacy user_id-only payload for web callers, but never
  // silently substitute a different connected account when the mobile path supplies one.
  if (connectedAccountId) payload.connected_account_id = connectedAccountId;
  const r = await fetchImpl(`${endpoint}/${tool}`, {
    method: "POST",
    headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return r.json();
}

function makeComposioCalendar({ apiKey, recordCall, recordProviderCost, fetchImpl, authorizeProviderOperation } = {}) {
  const key = apiKey || process.env.COMPOSIO_API_KEY;
  const ledger = recordCall || ((uid, tool, requestId) => {
    if (!recordProviderCost && (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY)) return false;
    return recordComposioOperation({ uid, tool, requestId }, { recordProviderCost });
  });
  const budgetGate = authorizeProviderOperation || (process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY
    ? (input) => authorizeBudget(input, { supaUrl: process.env.SUPABASE_URL, supaKey: process.env.SUPABASE_SERVICE_ROLE_KEY })
    : undefined);
  const execute = async (tool, uid, args, operationOptions = {}) => {
    const requestId = `composio:${uid || "anonymous"}:${tool}:${Date.now()}:${crypto.randomUUID()}`;
    if (typeof budgetGate === "function") {
      const decision = await budgetGate({
        uid, provider: "composio", operation: operationOptions.operation || "refresh",
        essential: operationOptions.essential === true, cacheHit: operationOptions.cacheHit === true, requestId,
      });
      if (decision && decision.allowed === false) throw new Error(`provider budget denied: ${decision.reason || "stopped"}`);
    }
    let result;
    let failure;
    try {
      const endpoint = operationOptions.endpointVersion === "v3.1" ? COMPOSIO_EXEC_V31 : COMPOSIO_EXEC;
      result = await exec(tool, uid, args, key, fetchImpl || globalThis.fetch, operationOptions.connectedAccountId || null, endpoint);
    } catch (error) {
      failure = error;
    } finally {
      await Promise.resolve(ledger(uid, tool, requestId)).catch(() => false);
    }
    if (failure) throw failure;
    return result;
  };
  const executeProxy = async (uid, request, operationOptions = {}) => {
    if (!key) return { status: 503, data: null, headers: {} };
    const requestId = `composio-proxy:${uid || "anonymous"}:${operationOptions.operation || "request"}:${Date.now()}:${crypto.randomUUID()}`;
    if (typeof budgetGate === "function") {
      const decision = await budgetGate({
        uid, provider: "composio", operation: operationOptions.operation || "proxy_execute",
        essential: operationOptions.essential === true, cacheHit: operationOptions.cacheHit === true, requestId,
      });
      if (decision && decision.allowed === false) {
        const error = new Error(`provider budget denied: ${decision.reason || "stopped"}`);
        error.code = "budget_denied";
        throw error;
      }
    }
    let response;
    let result;
    let failure;
    try {
      response = await (fetchImpl || globalThis.fetch)(COMPOSIO_PROXY_EXEC, {
        method: "POST",
        headers: { "x-api-key": key, "Content-Type": "application/json" },
        body: JSON.stringify({
          connected_account_id: request.connectedAccountId,
          endpoint: request.endpoint,
          method: request.method,
          ...(request.body === undefined ? {} : { body: request.body }),
          ...(request.parameters === undefined ? {} : { parameters: request.parameters }),
        }),
      });
      const raw = await response.json().catch(() => ({}));
      // v3.1 normally returns `{status,data,headers}` with HTTP 200.  On a
      // Composio-side failure there may be only an HTTP status; preserving it
      // as the normalized status keeps provider-read failures fail-closed.
      result = {
        status: Number.isFinite(Number(raw && raw.status)) ? Number(raw.status) : Number(response.status || 500),
        data: raw && Object.hasOwn(raw, "data") ? raw.data : null,
        headers: raw && raw.headers && typeof raw.headers === "object" ? raw.headers : {},
      };
      if (!response.ok && !Number.isFinite(Number(raw && raw.status))) result.status = Number(response.status || 500);
    } catch (error) {
      failure = error;
    } finally {
      await Promise.resolve(ledger(uid, "PROXY_EXECUTE", requestId)).catch(() => false);
    }
    if (failure) throw failure;
    return result;
  };
  // ONE page of Google Calendar items PLUS the cursor that unlocks the next. events.list returns at
  // most `maxResults` items per page (250 by default, 2500 max) and sets data.nextPageToken whenever
  // more remain — measured against this exact endpoint on 2026-07-26: a 548-day window came back as
  // 250 + 250 + 203 with a live token on the first two pages, and the identical 703 events arrive in
  // one call at maxResults=2500 with NO token. listEventsRaw used to drop that token on the floor,
  // which left "the calendar holds 703 events" and "it holds 7000 and you were handed page one"
  // indistinguishable to every caller. A caller that persists an append-only record
  // (fetchCalendarHistory → lm_care_scan_log) cannot live with that ambiguity, so the cursor is now
  // part of the transport contract.
  // Error contract unchanged and shared with listEventsRaw: default (wake path) swallows every
  // failure to an empty page — load-bearing, a transport blip must not crash the 60s tick — while
  // strict (history path) THROWS, because "empty calendar" and "the read failed" must never merge.
  const listEventsPage = async (uid, { timeMin, timeMax, maxResults, pageToken, strict, cacheHit, connectedAccountId } = {}) => {
    const empty = { items: [], nextPageToken: null };
    if (!key || !uid) {
      if (strict) throw new Error(`calendar transport not ready (missing ${key ? "uid" : "API key"})`);
      return empty;
    }
    const args = { calendarId: "primary", singleEvents: true, orderBy: "startTime", timeMin, timeMax };
    if (maxResults) args.maxResults = maxResults;
    if (pageToken) args.pageToken = pageToken;
    let j;
    try {
      j = await execute("GOOGLECALENDAR_EVENTS_LIST", uid, args, { essential: false, cacheHit, connectedAccountId });
    } catch (e) {
      if (strict) throw e;
      return empty;
    }
    if (!j || !j.successful) {
      if (strict) throw new Error(`calendar list failed: ${String((j && (j.error || j.message)) || "unsuccessful response")}`);
      return empty;
    }
    const d = j.data || {};
    return {
      items: d.items || d.events || [],
      nextPageToken: typeof d.nextPageToken === "string" && d.nextPageToken ? d.nextPageToken : null,
    };
  };
  return {
    kind: "composio",
    ready: () => !!key,
    listEventsPage,
    // Raw Google Calendar items (each consumer maps to its own shape) for [timeMin, timeMax] (ISO Z),
    // FIRST page only — the wake path reads an 18-hour horizon and has never approached a page
    // boundary. Callers that need provable completeness follow listEventsPage's cursor instead.
    async listEventsRaw(uid, opts = {}) {
      return (await listEventsPage(uid, opts)).items;
    },
    async readPrimaryCalendar(uid, { connectedAccountId } = {}) {
      if (!key || !uid || !connectedAccountId) throw new Error("calendar connection is not routed");
      const response = await execute("GOOGLECALENDAR_CALENDAR_LIST_GET", uid, { calendarId: "primary" }, {
        essential: true,
        connectedAccountId,
        endpointVersion: "v3.1",
      });
      if (!response || !response.successful) throw new Error("calendar primary read failed");
      const data = response.data?.response_data || response.response_data || response.data || {};
      const items = Array.isArray(data.items) ? data.items : Array.isArray(data.calendars) ? data.calendars : [];
      return items.find((item) => item && (item.id === "primary" || item.primary === true)) || items[0] || data;
    },
    // Exact provider read/write seam for the mobile travel-block state
    // machine.  The stable Life Manager uid is used only for budget/cost
    // attribution; provider ownership is selected exclusively by the exact
    // stored connected_account_id.
    async getExactEvent(uid, { calendarId = "primary", providerEventId, composioUserId, connectedAccountId } = {}) {
      if (!composioUserId || !connectedAccountId || !providerEventId) return { status: 400, data: null, headers: {} };
      return executeProxy(uid, {
        connectedAccountId,
        endpoint: `/calendars/${encodeURIComponent(String(calendarId))}/events/${encodeURIComponent(String(providerEventId))}`,
        method: "GET",
      }, { operation: "travel_block_read", essential: true });
    },
    async createExactEvent(uid, { calendarId = "primary", providerEventId, composioUserId, connectedAccountId, body } = {}) {
      if (!composioUserId || !connectedAccountId || !providerEventId || !body || typeof body !== "object") return { status: 400, data: null, headers: {} };
      return executeProxy(uid, {
        connectedAccountId,
        endpoint: `/calendars/${encodeURIComponent(String(calendarId))}/events`,
        method: "POST",
        body: { ...body, id: providerEventId },
      }, { operation: "travel_block_create", essential: true });
    },
    async createEvent(uid, args, { connectedAccountId } = {}) {
      if (!key) return { successful: false };
      try { return await execute("GOOGLECALENDAR_CREATE_EVENT", uid, args, { connectedAccountId }); } catch { return { successful: false }; }
    },
    async patchEvent(uid, args, { connectedAccountId } = {}) {
      if (!key) return { successful: false };
      try { return await execute("GOOGLECALENDAR_PATCH_EVENT", uid, args, { connectedAccountId }); } catch { return { successful: false }; }
    },
  };
}

module.exports = { makeComposioCalendar };
