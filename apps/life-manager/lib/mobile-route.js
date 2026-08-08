"use strict";

const { MobileError, normalizeLocale } = require("./mobile-utils.js");
const { projectLocalizedRouteName } = require("./mobile-localization.js");

function eventInstant(event, kind) {
  const value = event && (event[`${kind}Iso`] || (event[kind] && (event[kind].dateTime || event[kind].date)));
  return value || null;
}

function eventTimezone(event) {
  return (event && (event.timezone || event.timeZone || (event.start && (event.start.timeZone || event.start.timezone)))) || "UTC";
}

function buildAnchoredRouteRequest({ event, origin, direction = "outbound" } = {}) {
  if (!event || !event.id) throw new MobileError("route_anchor_invalid", "A calendar event is required.");
  if (!origin) throw new MobileError("missing_origin", "A route origin is required.");
  if (direction !== "outbound" && direction !== "return") throw new MobileError("route_direction_invalid", "The route direction is invalid.");
  const start = eventInstant(event, "start");
  const end = eventInstant(event, "end");
  if (!start || !end) throw new MobileError("route_anchor_invalid", "The event must have start and end instants.");
  const timezone = eventTimezone(event);
  return {
    eventId: String(event.id), eventDate: String(start).split("T")[0], timezone,
    eventStart: start, eventEnd: end, origin: typeof origin === "string" ? origin : origin.displayName || origin.address || origin,
    destination: event.location || event.destination || null, direction,
    arriveBy: direction === "outbound" ? start : null,
    departAt: direction === "return" ? end : null,
  };
}

function routeAccepted(value) {
  return Boolean(value && typeof value === "object" && (value.status === "route_ready" || value.provider || Array.isArray(value.steps) || Array.isArray(value.legs)));
}

async function readCache(scope, request, deps) {
  if (typeof deps.readRouteCache === "function") return deps.readRouteCache({ scope, request });
  const cache = deps.routeCache || deps.cache;
  if (!cache || typeof cache.get !== "function") return null;
  return cache.get(JSON.stringify([scope.uid, request.origin, request.destination, request.arriveBy, request.departAt, request.timezone]));
}

async function writeCache(scope, request, value, deps) {
  if (typeof deps.writeRouteCache === "function") return deps.writeRouteCache({ scope, request, value });
  const cache = deps.routeCache || deps.cache;
  if (!cache || typeof cache.set !== "function") return;
  return cache.set(JSON.stringify([scope.uid, request.origin, request.destination, request.arriveBy, request.departAt, request.timezone]), value);
}

async function computeMobileRoute(scope, event, origin, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const request = buildAnchoredRouteRequest({ event, origin, direction: deps.direction || "outbound" });
  const cached = await readCache(scope, request, deps);
  if (cached && routeAccepted(cached.value || cached)) return cached.value || cached;
  const transit = deps.transitProvider || deps.transitRoute || deps.transit;
  const google = deps.googleProvider || deps.googleRoute || deps.google;
  let candidate = null;
  if (typeof transit === "function") {
    try { candidate = await transit(request, { scope }); } catch { candidate = null; }
  }
  if (routeAccepted(candidate)) {
    await writeCache(scope, request, candidate, deps);
    return candidate;
  }
  if (typeof google === "function") {
    try { candidate = await google(request, { scope }); } catch { candidate = null; }
  }
  if (routeAccepted(candidate)) {
    await writeCache(scope, request, candidate, deps);
    return candidate;
  }
  return null;
}

function nullableName(value, locale) {
  if (value === null || value === undefined) return null;
  return projectLocalizedRouteName(value, locale);
}

function projectStep(step, locale, sequence) {
  const output = {
    sequence: Number.isSafeInteger(step.sequence) ? step.sequence : sequence,
    mode: String(step.mode || step.kind || "other"),
    instruction: nullableName(step.instruction || "", locale),
    from: nullableName(step.from, locale), to: nullableName(step.to, locale),
    service: nullableName(step.service || step.routeName, locale),
    headsign: nullableName(step.headsign, locale),
    platform: step.platform === undefined ? null : step.platform,
    departAt: step.departAt || step.depart_at || null,
    arriveAt: step.arriveAt || step.arrive_at || null,
    durationSeconds: Number(step.durationSeconds ?? step.duration_secs ?? 0),
  };
  for (const unsupported of ["entrance", "exit", "optimalCar", "crowding"]) delete output[unsupported];
  return output;
}

function projectMobileRoute(route, locale = "en") {
  if (!route || typeof route !== "object") throw new MobileError("route_unavailable", "The route is unavailable.", 422, true);
  const active = normalizeLocale(locale);
  const sourceSteps = Array.isArray(route.steps) ? route.steps : (Array.isArray(route.legs) ? route.legs : []);
  const result = {
    status: route.status || "route_ready", provider: route.provider || "transit",
    providerAttribution: active === "ja" && (route.provider || "transit") === "transit" ? "交通情報（非公式）" : (route.providerAttribution || route.provider_attribution || "Transit API"),
    computedAt: route.computedAt || route.computed_at || new Date().toISOString(), timezone: route.timezone || "UTC", eventId: String(route.eventId || route.event_id || ""),
    origin: { displayName: projectLocalizedRouteName(route.origin, active), userContent: route.origin && (route.origin.userContent ?? route.origin.user_content ?? null) },
    destination: { displayName: projectLocalizedRouteName(route.destination, active), userContent: route.destination && (route.destination.userContent ?? route.destination.user_content ?? null) },
    leaveAt: route.leaveAt || route.leave_at || null, arriveAt: route.arriveAt || route.arrive_at || null,
    durationSeconds: Number(route.durationSeconds ?? route.duration_secs ?? 0), bufferSeconds: Number(route.bufferSeconds ?? route.buffer_secs ?? 0),
    transferCount: Number(route.transferCount ?? route.transfer_count ?? 0), fare: route.fare === undefined ? null : route.fare, geometry: route.geometry === undefined ? null : route.geometry,
    steps: sourceSteps.map((step, index) => projectStep(step, active, index + 1)),
  };
  if (route.bufferReason !== undefined) result.bufferReason = route.bufferReason;
  for (const unsupported of ["entrance", "exit", "optimalCar", "crowding"]) delete result[unsupported];
  return result;
}

module.exports = { buildAnchoredRouteRequest, computeMobileRoute, projectMobileRoute, routeAccepted };
