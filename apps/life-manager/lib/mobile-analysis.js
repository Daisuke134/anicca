"use strict";

const { MobileError, randomOpaque, normalizeLocale, sha256 } = require("./mobile-utils.js");
const { appendMobileMessage } = require("./mobile-outbox.js");
const { computeMobileRoute } = require("./mobile-route.js");

const TERMINAL_STATES = Object.freeze(["route_ready", "needs_information", "no_upcoming_event", "route_unavailable", "failed"]);

function userField(user, ...names) {
  for (const name of names) if (user && user[name] !== undefined) return user[name];
  return null;
}

function messageKey(status) {
  return `chat.${status}`;
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
    events = await reader(scope.uid, { nowMs: deps.now ? deps.now() : Date.now(), horizonH: input.horizonH || 18, calendar: deps.calendar, gmailAccountId: user.gmail_account_id || user.gmailAccountId, apiKey: deps.composioKey || deps.apiKey });
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
    return await appendTerminal({ ...scope, productLocale: locale }, "route_ready", event, route, null, deps, analysisId);
  } catch (error) {
    if (error && (error.code === "localization_unavailable" || error.code === "mixed_locale")) {
      await setState(scope, { status: "route_unavailable", analysisId }, deps);
      return appendTerminal({ ...scope, productLocale: locale }, "route_unavailable", event, null, null, deps, analysisId, "localization_unavailable");
    }
    throw error;
  }
}

module.exports = { TERMINAL_STATES, analyzeNextEvent };
