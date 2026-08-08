"use strict";

const { MobileError, randomOpaque, normalizeLocale, sha256 } = require("./mobile-utils.js");
const { appendMobileMessage } = require("./mobile-outbox.js");
const { computeMobileRoute } = require("./mobile-route.js");
const { ensureMobileTravelBlock } = require("./mobile-travel-block.js");
const { getCalendar } = require("./transport/index.js");

const TERMINAL_STATES = Object.freeze(["route_ready", "needs_information", "no_upcoming_event", "route_unavailable", "failed"]);

function userField(user, ...names) {
  for (const name of names) if (user && user[name] !== undefined) return user[name];
  return null;
}

function messageKey(status) {
  return `chat.${status}`;
}

const TRAVEL_FAILURE_CODES = new Set([
  "provider_write_failed", "provider_readback_failed", "claim_pending", "budget_denied", "analysis_conflict", "provider_collision",
]);

function eventDateTime(event, field) {
  const value = event && event[field];
  if (typeof value === "string") return value;
  if (value && typeof value === "object") return value.dateTime || value.date_time || null;
  return null;
}

function travelReceiptId(uid, sourceEventId, leg = "go") {
  return `message:v1:travel-${sha256(`${uid}\u0000${sourceEventId}\u0000${leg}`).slice(0, 40)}`;
}

function travelPayload(event, route) {
  const startAt = route && (route.leaveAt || route.leave_at);
  const endAt = eventDateTime(event, "startIso") || eventDateTime(event, "start");
  const timezone = (event && (event.timezone || event.timeZone)) || (route && (route.timezone || route.timeZone));
  return {
    summary: `[Travel] ${event && (event.summary || event.id) || "Travel time"}`,
    description: "",
    location: event && event.location || "",
    timezone,
    start: { dateTime: startAt, timeZone: timezone },
    end: { dateTime: endAt, timeZone: timezone },
  };
}

function failureCode(result) {
  const status = result && (result.errorCode || result.error_code || result.status);
  if (status === "busy") return "claim_pending";
  if (TRAVEL_FAILURE_CODES.has(status)) return status;
  return "provider_write_failed";
}

function verifiedTravelResult(result) {
  return result && (result.status === "created" || result.status === "existing") && typeof result.providerEventId === "string" && result.providerEventId;
}

async function runTravelBlock(scope, user, event, route, input, deps) {
  const sourceEventId = String(event && event.id || route && (route.eventId || route.event_id) || "");
  const owner = user.calendar_composio_user_id || user.calendarComposioUserId || null;
  const account = user.gmail_account_id || user.gmailAccountId || null;
  const operation = deps.ensureMobileTravelBlock || deps.ensureTravelBlock || ensureMobileTravelBlock;
  const provider = deps.travelBlockProvider || deps.calendar || getCalendar({
    apiKey: deps.composioKey || deps.apiKey || process.env.COMPOSIO_API_KEY,
    composioUserId: owner || scope.uid,
    connectedAccountId: account,
    recordCall: deps.recordCall,
    recordProviderCost: deps.recordProviderCost,
    authorizeProviderOperation: deps.authorizeProviderOperation,
  });
  return operation({
    uid: scope.uid,
    eventKey: sourceEventId,
    sourceEventId,
    leg: "go",
    calendarId: "primary",
    analysisKey: input.analysisId,
    connectedAccountId: account,
    gmailAccountId: account,
    composioUserId: owner,
    calendarComposioUserId: owner,
    workerId: deps.workerId || "mobile-analysis",
    payload: travelPayload(event, route),
  }, {
    ...deps,
    store: deps.store,
    provider,
    serverSecret: deps.serverSecret || deps.travelBlockSecret || process.env.LM_TRAVEL_BLOCK_SECRET || process.env.LM_UID_SECRET,
  });
}

async function appendTravelReceipt(scope, event, route, result, deps, analysisId) {
  const sourceEventId = String(event && event.id || route && (route.eventId || route.event_id) || "");
  const payload = travelPayload(event, route);
  const success = verifiedTravelResult(result);
  const key = success ? "chat.travel_block_confirmed" : "chat.travel_block_not_added";
  const args = success
    ? {
      status: result.status,
      sourceEventId,
      providerEventId: result.providerEventId,
      calendar: "primary",
      leg: "go",
      blockStart: payload.start.dateTime,
      blockEnd: payload.end.dateTime,
      timezone: payload.timezone || null,
      verification: "provider_readback",
      verifiedAt: result.verifiedAt || result.verified_at || null,
    }
    : { reason: failureCode(result), sourceEventId, calendar: "primary", leg: "go" };
  return appendMobileMessage({ ...scope, productLocale: scope.productLocale || "en" }, {
    id: travelReceiptId(scope.uid, sourceEventId || analysisId, "go"),
    type: "system", key, args,
    userContent: { eventTitle: event && (event.summary || null), eventLocation: event && (event.location || null) },
  }, deps);
}

function requiredQuestion(type, event, deps = {}, analysisId = "") {
  const prompts = {
    calendar: "Connect Google Calendar to analyze your next event.",
    name: "What should Life Manager call you?",
    origin: "Where will you be leaving from?",
    destination: "Where will this event take place?",
  };
  return {
    id: `question:v1:${sha256(`${analysisId}:${type}:${event && event.id || ""}`).slice(0, 32)}`,
    type,
    prompt: prompts[type] || "I need one more detail before I can continue.",
    eventId: event && event.id ? event.id : null,
  };
}

async function setState(scope, state, deps) {
  if (deps.store && typeof deps.store.writeAnalysisState === "function") await deps.store.writeAnalysisState(scope, state);
  if (typeof deps.setAnalysisState === "function") await deps.setAnalysisState(scope, state);
}

async function appendTerminal(scope, status, event, route, question, deps, analysisId, reason) {
  const userContent = { eventTitle: event ? (event.summary || null) : null, eventLocation: event ? (event.location || null) : null };
  const messageId = String(analysisId || "").startsWith("analysis:v1:")
    ? `message:v1:${String(analysisId).slice("analysis:v1:".length)}`
    : `message:v1:${String(analysisId || "").replace(/[^A-Za-z0-9_-]/gu, "")}`;
  const message = await appendMobileMessage(scope, {
    type: status === "route_ready" ? "route" : status === "needs_information" ? "question" : status === "route_unavailable" ? "route_unavailable" : "system",
    key: messageKey(status),
    args: {
      eventTitle: "userContent.eventTitle", leaveAt: "route.leaveAt", arriveAt: "route.arriveAt", bufferSeconds: "route.bufferSeconds", reason: reason || null,
    },
    userContent, route, question, id: messageId,
  }, deps);
  return { status, analysisId, nextCursor: message.cursor, message };
}

async function analyzeNextEvent(scope, input = {}, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const store = deps.store;
  if (!store || typeof store.readUser !== "function") throw new MobileError("analysis_unavailable", "Analysis storage is unavailable.", 503, true);
  const user = await store.readUser(scope);
  if (!user) throw new MobileError("account_not_found", "The Life Manager account was not found.", 404);
  const locale = normalizeLocale(user.product_locale || user.productLocale || scope.productLocale || "en");
  const analysisId = input.analysisId || randomOpaque("analysis:v1:", deps);
  await setState(scope, { status: "reading_events", analysisId }, deps);
  const calendarConnected = user.calendar_status === "connected"
    || (Boolean(user.calendar_provider) && Boolean(user.gmail_account_id || user.gmailAccountId));
  if (!calendarConnected) {
    await setState(scope, { status: "needs_information", analysisId }, deps);
    const question = requiredQuestion("calendar", null, deps, analysisId);
    if (typeof store.createQuestion === "function") await store.createQuestion(scope, question);
    return appendTerminal({ ...scope, productLocale: locale }, "needs_information", null, null, question, deps, analysisId);
  }
  if (typeof user.name !== "string" || !user.name.trim()) {
    await setState(scope, { status: "needs_information", analysisId }, deps);
    const question = requiredQuestion("name", null, deps, analysisId);
    if (typeof store.createQuestion === "function") await store.createQuestion(scope, question);
    return appendTerminal({ ...scope, productLocale: locale }, "needs_information", null, null, question, deps, analysisId);
  }
  let events;
  try {
    const reader = deps.fetchUpcomingEvents || require("./mobile-calendar.js").fetchMobileUpcomingEvents;
    events = await reader(scope.uid, {
      nowMs: deps.now ? deps.now() : Date.now(), horizonH: input.horizonH || 18, calendar: deps.calendar,
      gmailAccountId: user.gmail_account_id || user.gmailAccountId,
      connectedAccountId: user.gmail_account_id || user.gmailAccountId,
      composioUserId: user.calendar_composio_user_id || user.calendarComposioUserId || scope.uid,
      apiKey: deps.composioKey || deps.apiKey,
    });
  } catch {
    await setState(scope, { status: "failed", analysisId }, deps);
    return appendTerminal({ ...scope, productLocale: locale }, "failed", null, null, null, deps, analysisId);
  }
  const event = Array.isArray(events) && events.length ? events[0] : null;
  if (!event) {
    await setState(scope, { status: "no_upcoming_event", analysisId }, deps);
    return appendTerminal({ ...scope, productLocale: locale }, "no_upcoming_event", null, null, null, deps, analysisId);
  }
  const home = user.home_address || user.home || input.origin || null;
  if (!home || !event.location) {
    await setState(scope, { status: "needs_information", analysisId }, deps);
    const question = requiredQuestion(!home ? "origin" : "destination", event, deps, analysisId);
    if (typeof store.createQuestion === "function") await store.createQuestion(scope, question);
    return appendTerminal({ ...scope, productLocale: locale }, "needs_information", event, null, question, deps, analysisId);
  }
  await setState(scope, { status: "checking_locations", analysisId }, deps);
  await setState(scope, { status: "calculating_route", analysisId }, deps);
  let route;
  try {
    route = typeof deps.computeMobileRoute === "function" ? await deps.computeMobileRoute(scope, event, home, deps) : await computeMobileRoute(scope, event, home, deps);
  } catch (error) {
    await setState(scope, { status: "failed", analysisId }, deps);
    return appendTerminal({ ...scope, productLocale: locale }, "failed", event, null, null, deps, analysisId, error && error.code);
  }
  if (!route) {
    await setState(scope, { status: "route_unavailable", analysisId }, deps);
    return appendTerminal({ ...scope, productLocale: locale }, "route_unavailable", event, null, null, deps, analysisId, "provider_unavailable");
  }
  await setState(scope, { status: "route_ready", analysisId }, deps);
  try {
    // Persist the route card before attempting the provider side effect. The
    // durable travel state machine is the only code allowed to create/read back
    // the Calendar block; a route card alone is never an insertion receipt.
    const routeResult = await appendTerminal({ ...scope, productLocale: locale }, "route_ready", event, route, null, deps, analysisId);
    let travelResult;
    try {
      travelResult = await runTravelBlock({ ...scope, productLocale: locale }, user, event, route, { ...input, analysisId }, deps);
    } catch (error) {
      travelResult = { status: failureCode({ errorCode: error && error.code }), errorCode: failureCode({ errorCode: error && error.code }) };
    }
    await appendTravelReceipt({ ...scope, productLocale: locale }, event, route, travelResult, deps, analysisId);
    return routeResult;
  } catch (error) {
    if (error && (error.code === "localization_unavailable" || error.code === "mixed_locale")) {
      await setState(scope, { status: "route_unavailable", analysisId }, deps);
      return appendTerminal({ ...scope, productLocale: locale }, "route_unavailable", event, null, null, deps, analysisId, "localization_unavailable");
    }
    throw error;
  }
}

module.exports = { TERMINAL_STATES, analyzeNextEvent };
