"use strict";

const { MobileError, mobileRouteCacheKey, normalizeLocale, nowIso, safeTimeZone } = require("./mobile-utils.js");
const { projectRouteName } = require("./mobile-localization.js");
const { chooseRouter } = require("./transit.js");

function eventInstant(event, kind) {
  const value = event && (event[`${kind}Iso`] || (event[kind] && (event[kind].dateTime || event[kind].date)));
  return value || null;
}

function eventTimezone(event) {
  const value = event && (event.timezone || event.timeZone || (event.start && (event.start.timeZone || event.start.timezone)));
  if (!value) throw new MobileError("route_timezone_required", "The calendar event timezone is required for an anchored route.");
  try { return safeTimeZone(value); } catch (error) {
    if (error && error.code === "invalid_timezone") throw new MobileError("route_timezone_invalid", "The calendar event timezone is not a valid IANA timezone.");
    throw error;
  }
}

function localEventDate(instant, timezone) {
  const date = new Date(instant);
  if (Number.isNaN(date.getTime())) throw new MobileError("route_anchor_invalid", "The event start is not a valid instant.");
  let parts;
  try {
    parts = new Intl.DateTimeFormat("en-US", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  } catch {
    throw new MobileError("route_anchor_invalid", "The event timezone is not a valid IANA timezone.");
  }
  const values = Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function buildAnchoredRouteRequest({ event, origin, direction = "outbound" } = {}) {
  if (!event || !event.id) throw new MobileError("route_anchor_invalid", "A calendar event is required.");
  if (!origin) throw new MobileError("missing_origin", "A route origin is required.");
  if (direction !== "outbound" && direction !== "return") throw new MobileError("route_direction_invalid", "The route direction is invalid.");
  const start = eventInstant(event, "start");
  const end = eventInstant(event, "end");
  if (!start || (direction === "return" && !end)) throw new MobileError("route_anchor_invalid", "The event does not contain the instant required for this route.");
  const destination = event.location || event.destination || null;
  if (!destination) throw new MobileError("missing_destination", "A route destination is required.");
  const timezone = eventTimezone(event);
  return {
    eventId: String(event.id), eventDate: localEventDate(start, timezone), timezone,
    eventStart: start, eventEnd: end || null, origin: typeof origin === "string" ? origin : origin.displayName || origin.address || origin,
    destination, direction,
    arriveBy: direction === "outbound" ? start : null,
    departAt: direction === "return" ? end : null,
  };
}

function routeAccepted(value) {
  return Boolean(value && typeof value === "object" && (
    value.provider && (
      value.leaveAt || value.leave_at || value.arriveAt || value.arrive_at
      || (Array.isArray(value.steps) && value.steps.length > 0)
      || (Array.isArray(value.legs) && value.legs.length > 0)
      || (value.status === "route_ready" && value.eventId && value.origin && value.destination)
    )
  ));
}

async function readCache(scope, request, deps) {
  if (typeof deps.readRouteCache === "function") return deps.readRouteCache({ scope, request });
  if (deps.store && typeof deps.store.readRouteCache === "function") return deps.store.readRouteCache(scope, request);
  const cache = deps.routeCache || deps.cache || (deps.routeProviders && deps.routeProviders.routeCache);
  if (!cache || typeof cache.get !== "function") return null;
  return cache.get(mobileRouteCacheKey(scope, request), { uid: scope.uid });
}

async function writeCache(scope, request, value, deps) {
  if (typeof deps.writeRouteCache === "function") return deps.writeRouteCache({ scope, request, value });
  if (deps.store && typeof deps.store.writeRouteCache === "function") return deps.store.writeRouteCache(scope, request, value);
  const cache = deps.routeCache || deps.cache || (deps.routeProviders && deps.routeProviders.routeCache);
  if (!cache || typeof cache.set !== "function") return;
  return cache.set(mobileRouteCacheKey(scope, request), value, { uid: scope.uid });
}

async function computeMobileRoute(scope, event, origin, deps = {}) {
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const request = buildAnchoredRouteRequest({ event, origin, direction: deps.direction || "outbound" });
  const cached = await readCache(scope, request, deps);
  if (cached && routeAccepted(cached.value || cached)) return cached.value || cached;
  const production = deps.routeProviders || (deps.mapsKey ? createStructuredRouteProviders({
    mapsKey: deps.mapsKey,
    fetchImpl: deps.fetchImpl,
    routeCache: deps.routeCache,
    now: deps.now,
  }) : null);
  const transit = deps.transitProvider || deps.transitRoute || deps.transit || (production && production.transitProvider);
  const google = deps.googleProvider || deps.googleRoute || deps.google || (production && production.googleProvider);
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

function routeCacheFor(options = {}) {
  if (options.routeCache && typeof options.routeCache.get === "function" && typeof options.routeCache.set === "function") return options.routeCache;
  const store = options.cacheStore;
  const ttlMs = Number.isFinite(options.cacheTtlMs) ? Math.max(0, options.cacheTtlMs) : 10 * 60_000;
  const now = typeof options.now === "function" ? options.now : Date.now;
  const scopedKey = (key, scope = {}) => `${scope.uid == null ? "" : String(scope.uid)}\u0000${key}`;
  return {
    get(key, scope = {}) {
      if (!store || typeof store.get !== "function") return null;
      const processKey = scopedKey(key, scope);
      const hit = store.get(processKey);
      if (!hit || now() - hit.computedAt >= ttlMs) {
        if (hit) store.delete(processKey);
        return null;
      }
      return hit;
    },
    set(key, value, scope = {}) {
      if (store && typeof store.set === "function") store.set(scopedKey(key, scope), { value, computedAt: now() });
    },
  };
}

function structuredName(value) {
  const text = String(value || "").trim();
  return { displayNames: { en: text, ja: text }, userContent: text || null };
}

function anchorTimes(request, durationSeconds, now = Date.now, bufferSeconds = 0) {
  const anchor = Date.parse(request.direction === "return" ? request.departAt : request.arriveBy);
  if (!Number.isFinite(anchor) || !Number.isFinite(durationSeconds) || durationSeconds <= 0) return null;
  const buffer = Number.isFinite(Number(bufferSeconds)) ? Math.max(0, Number(bufferSeconds)) : 0;
  const leaveMs = request.direction === "return" ? anchor : anchor - buffer * 1000 - durationSeconds * 1000;
  const arriveMs = request.direction === "return" ? anchor + durationSeconds * 1000 : anchor - buffer * 1000;
  return { leaveAt: new Date(leaveMs).toISOString(), arriveAt: new Date(arriveMs).toISOString(), computedAt: nowIso({ now }) };
}

function firstDefined(value, ...keys) {
  for (const key of keys) if (value && value[key] !== undefined && value[key] !== null) return value[key];
  return null;
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function providerTime(value) {
  if (value === undefined || value === null || value === "") return null;
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    const milliseconds = Math.abs(numeric) >= 1e12 ? numeric : numeric * 1000;
    const date = new Date(milliseconds);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
  }
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function providerName(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  if (typeof value === "object") return firstDefined(value, "name", "displayName", "display_name") || null;
  return String(value);
}

// Keep this parser beside the mobile adapter so the public route can retain
// facts that the legacy wake-loop parser intentionally reduced away.
function parseStructuredTransitPlan(plan) {
  const journeys = plan && Array.isArray(plan.journeys) ? plan.journeys : [];
  if (!journeys.length) return null;
  const best = journeys.reduce((left, right) => {
    const leftArrival = numberOrNull(firstDefined(left, "arrivalSecs", "arrival_sec", "arrival"));
    const rightArrival = numberOrNull(firstDefined(right, "arrivalSecs", "arrival_sec", "arrival"));
    if (leftArrival === null) return right;
    if (rightArrival === null) return left;
    return rightArrival < leftArrival ? right : left;
  });
  const accessWalkSecs = numberOrNull(firstDefined(best, "accessWalkSecs", "access_walk_secs"));
  const egressWalkSecs = numberOrNull(firstDefined(best, "egressWalkSecs", "egress_walk_secs"));
  const baseDuration = numberOrNull(firstDefined(best, "durationSecs", "duration_sec"))
    ?? (() => {
      const departure = numberOrNull(firstDefined(best, "departureSecs", "departure_sec"));
      const arrival = numberOrNull(firstDefined(best, "arrivalSecs", "arrival_sec"));
      return departure !== null && arrival !== null ? Math.max(0, arrival - departure) : null;
    })();
  if (baseDuration === null) return null;
  const legs = Array.isArray(best.legs) ? best.legs : [];
  return {
    durationSecs: baseDuration + Math.max(0, accessWalkSecs || 0),
    inVehicleSecs: numberOrNull(firstDefined(best, "inVehicleSecs", "in_vehicle_secs")) ?? baseDuration,
    accessWalkSecs,
    egressWalkSecs,
    bufferSeconds: numberOrNull(firstDefined(best, "bufferSeconds", "buffer_seconds", "bufferSecs", "buffer_secs")),
    transferCount: numberOrNull(firstDefined(best, "transferCount", "transfer_count")),
    fare: firstDefined(best, "fare", "fareInfo", "fare_info"),
    legs: legs.map((leg) => {
      const departure = firstDefined(leg, "departureSecs", "departure_sec", "departureTime", "departure_time");
      const arrival = firstDefined(leg, "arrivalSecs", "arrival_sec", "arrivalTime", "arrival_time");
      const result = {
        kind: firstDefined(leg, "kind", "mode"), mode: firstDefined(leg, "mode", "kind") || "other",
        routeName: firstDefined(leg, "routeName", "route_name", "service"),
        from: providerName(firstDefined(leg, "from", "origin")), to: providerName(firstDefined(leg, "to", "destination")),
        instruction: firstDefined(leg, "instruction", "instructions"),
        departAt: providerTime(departure), arriveAt: providerTime(arrival),
        durationSeconds: numberOrNull(firstDefined(leg, "durationSecs", "duration_sec"))
          ?? (numberOrNull(departure) !== null && numberOrNull(arrival) !== null ? Math.max(0, numberOrNull(arrival) - numberOrNull(departure)) : null),
      };
      const optional = [
        ["trainType", ["trainType", "train_type"]],
        ["headsign", ["headsign", "direction"]],
        ["platform", ["platform", "platformName", "platform_name"]],
        ["availability", ["availability", "serviceAvailability", "service_availability"]],
      ];
      for (const [output, keys] of optional) {
        const value = firstDefined(leg, ...keys);
        if (value !== null) result[output] = value;
      }
      return result;
    }),
  };
}

function routeFromTransit(request, parsed, now) {
  const times = anchorTimes(request, parsed && parsed.durationSecs, now, parsed && parsed.bufferSeconds);
  if (!times) return null;
  return {
    status: "route_ready", provider: "transit", providerAttribution: "Transit API", eventId: request.eventId,
    computedAt: times.computedAt, timezone: request.timezone,
    origin: structuredName(request.origin), destination: structuredName(request.destination), ...times,
    durationSeconds: parsed.durationSecs, bufferSeconds: parsed.bufferSeconds ?? null, transferCount: parsed.transferCount ?? null,
    accessWalkSecs: parsed.accessWalkSecs ?? null, egressWalkSecs: parsed.egressWalkSecs ?? null,
    fare: parsed.fare ?? null, geometry: null,
    steps: (parsed.legs || []).map((leg, index) => ({
      sequence: index + 1, mode: leg.mode || leg.kind || "other", instruction: leg.instruction || null,
      from: leg.from || null, to: leg.to || null, service: leg.routeName || null,
      headsign: leg.headsign === undefined ? null : leg.headsign,
      platform: leg.platform === undefined ? null : leg.platform,
      departAt: leg.departAt || null, arriveAt: leg.arriveAt || null, durationSeconds: leg.durationSeconds ?? null,
      ...(leg.trainType === undefined ? {} : { trainType: leg.trainType }),
      ...(leg.availability === undefined ? {} : { availability: leg.availability }),
    })),
  };
}

function routeFromGoogle(request, body, now) {
  const source = body && Array.isArray(body.routes) ? body.routes[0] : null;
  const leg = source && Array.isArray(source.legs) ? source.legs[0] : null;
  const durationSeconds = Number(leg && leg.duration && leg.duration.value);
  const times = anchorTimes(request, durationSeconds, now);
  if (!times) return null;
  return {
    status: "route_ready", provider: "google", providerAttribution: "Google Maps", eventId: request.eventId,
    computedAt: times.computedAt, timezone: request.timezone,
    origin: structuredName(request.origin), destination: structuredName(request.destination), ...times,
    durationSeconds, bufferSeconds: null, transferCount: null,
    fare: source && (source.fare || source.fare_info) || null, geometry: null,
    steps: (leg && leg.steps || []).map((step, index) => ({
      sequence: index + 1, mode: String(step.travel_mode || "other").toLowerCase(),
      instruction: typeof step.html_instructions === "string" ? step.html_instructions.replace(/<[^>]+>/gu, "") : null,
      from: step.start_address || null, to: step.end_address || null, service: null, headsign: null,
      platform: null,
      departAt: step.departure_time && step.departure_time.value ? new Date(step.departure_time.value * 1000).toISOString() : null,
      arriveAt: step.arrival_time && step.arrival_time.value ? new Date(step.arrival_time.value * 1000).toISOString() : null,
      durationSeconds: Number(step.duration && step.duration.value) || null,
      ...(step.transit_details && step.transit_details.headsign ? { headsign: step.transit_details.headsign } : {}),
      ...(step.transit_details && step.transit_details.line && step.transit_details.line.vehicle && step.transit_details.line.vehicle.type
        ? { trainType: step.transit_details.line.vehicle.type } : {}),
      ...(step.transit_details && step.transit_details.departure_stop && step.transit_details.departure_stop.name
        ? { from: step.transit_details.departure_stop.name } : {}),
      ...(step.transit_details && step.transit_details.arrival_stop && step.transit_details.arrival_stop.name
        ? { to: step.transit_details.arrival_stop.name } : {}),
      ...(step.transit_details && step.transit_details.departure_stop && step.transit_details.departure_stop.platform
        ? { platform: step.transit_details.departure_stop.platform } : {}),
    })),
  };
}

function createStructuredRouteProviders(options = {}) {
  const mapsKey = String(options.mapsKey || process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY || "");
  const fetchImpl = options.fetchImpl || fetch;
  const now = typeof options.now === "function" ? options.now : Date.now;
  const cache = routeCacheFor(options);
  const geocodes = options.geocodeCache || new Map();
  async function geocode(address) {
    const key = String(address || "");
    if (geocodes.has(key)) return geocodes.get(key);
    if (!mapsKey || !key) return null;
    try {
      const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(key)}&key=${encodeURIComponent(mapsKey)}`;
      const response = await fetchImpl(url);
      const body = await response.json();
      const location = body && body.status === "OK" && body.results && body.results[0] && body.results[0].geometry && body.results[0].geometry.location;
      const value = location && Number.isFinite(Number(location.lat)) && Number.isFinite(Number(location.lng))
        ? { lat: Number(location.lat), lon: Number(location.lng) } : null;
      geocodes.set(key, value);
      return value;
    } catch { return null; }
  }
  async function transitProvider(request) {
    const [from, to] = await Promise.all([geocode(request.origin), geocode(request.destination)]);
    if (!from || !to || chooseRouter(from, to) !== "transit") return null;
    try {
      const url = `https://api.transit.ls8h.com/api/v1/plan?from=geo:${from.lat},${from.lon}&to=geo:${to.lat},${to.lon}`;
      const response = await fetchImpl(url);
      const parsed = parseStructuredTransitPlan(await response.json());
      return parsed ? routeFromTransit(request, parsed, now) : null;
    } catch { return null; }
  }
  async function googleProvider(request) {
    if (!mapsKey) return null;
    try {
      const params = new URLSearchParams({ origin: String(request.origin), destination: String(request.destination), mode: "transit", key: mapsKey });
      const anchor = Date.parse(request.direction === "return" ? request.departAt : request.arriveBy);
      if (Number.isFinite(anchor)) params.set(request.direction === "return" ? "departure_time" : "arrival_time", String(Math.floor(anchor / 1000)));
      const response = await fetchImpl(`https://maps.googleapis.com/maps/api/directions/json?${params.toString()}`);
      const body = await response.json();
      if (body && body.status === "OK") return routeFromGoogle(request, body, now);
    } catch { /* fall through to truthful unavailable */ }
    return null;
  }
  return { transitProvider, googleProvider, routeCache: cache };
}

function nullableName(value, locale, provenance) {
  if (value === null || value === undefined) return null;
  const projected = projectRouteName(value, locale);
  if (projected.source === "transliteration") provenance.used = true;
  return projected.value;
}

function projectStep(step, locale, sequence, provenance) {
  const output = {
    sequence: Number.isSafeInteger(step.sequence) ? step.sequence : sequence,
    mode: String(step.mode || step.kind || "other"),
    instruction: nullableName(step.instruction || "", locale, provenance),
    from: nullableName(step.from, locale, provenance), to: nullableName(step.to, locale, provenance),
    service: nullableName(step.service || step.routeName, locale, provenance),
    headsign: nullableName(step.headsign, locale, provenance),
    platform: step.platform === undefined ? null : step.platform,
    departAt: step.departAt || step.depart_at || null,
    arriveAt: step.arriveAt || step.arrive_at || null,
    durationSeconds: step.durationSeconds === undefined && step.duration_secs === undefined
      ? null : Number(step.durationSeconds ?? step.duration_secs),
  };
  const trainType = step.trainType === undefined ? step.train_type : step.trainType;
  if (trainType !== undefined) output.trainType = trainType;
  const availability = step.availability === undefined ? step.serviceAvailability : step.availability;
  if (availability !== undefined) output.availability = availability;
  for (const unsupported of ["entrance", "exit", "optimalCar", "crowding"]) delete output[unsupported];
  return output;
}

function projectMobileRoute(route, locale = "en") {
  if (!route || typeof route !== "object") throw new MobileError("route_unavailable", "The route is unavailable.", 422, true);
  const active = normalizeLocale(locale);
  const sourceSteps = Array.isArray(route.steps) ? route.steps : (Array.isArray(route.legs) ? route.legs : []);
  const provenance = { used: false };
  const providerAttribution = Object.hasOwn(route, "providerAttribution")
    ? route.providerAttribution
    : (Object.hasOwn(route, "provider_attribution") ? route.provider_attribution : null);
  const result = {
    status: route.status || "route_ready", provider: route.provider || null,
    providerAttribution: active === "ja" && route.provider === "transit" && providerAttribution !== null ? "交通情報（非公式）" : providerAttribution,
    computedAt: route.computedAt || route.computed_at || null, timezone: route.timezone || null, eventId: route.eventId || route.event_id || null,
    origin: { displayName: nullableName(route.origin, active, provenance), userContent: route.origin && (route.origin.userContent ?? route.origin.user_content ?? null) },
    destination: { displayName: nullableName(route.destination, active, provenance), userContent: route.destination && (route.destination.userContent ?? route.destination.user_content ?? null) },
    leaveAt: route.leaveAt || route.leave_at || null, arriveAt: route.arriveAt || route.arrive_at || null,
    durationSeconds: route.durationSeconds === undefined && route.duration_secs === undefined ? null : Number(route.durationSeconds ?? route.duration_secs),
    bufferSeconds: route.bufferSeconds === undefined && route.buffer_secs === undefined ? null : Number(route.bufferSeconds ?? route.buffer_secs),
    transferCount: route.transferCount === undefined && route.transfer_count === undefined ? null : Number(route.transferCount ?? route.transfer_count), fare: route.fare === undefined ? null : route.fare, geometry: route.geometry === undefined ? null : route.geometry,
    steps: sourceSteps.map((step, index) => projectStep(step, active, index + 1, provenance)),
  };
  for (const [key, aliases] of [
    ["accessWalkSeconds", ["access_walk_seconds", "accessWalkSecs", "access_walk_secs"]],
    ["egressWalkSeconds", ["egress_walk_seconds", "egressWalkSecs", "egress_walk_secs"]],
    ["freshness", ["sourceFreshness", "source_freshness"]],
  ]) {
    const source = [key, ...aliases].find((candidate) => Object.hasOwn(route, candidate));
    if (source) result[key] = route[source] === undefined ? null : route[source];
  }
  if (route.bufferReason !== undefined) result.bufferReason = route.bufferReason;
  for (const unsupported of ["entrance", "exit", "optimalCar", "crowding"]) delete result[unsupported];
  if (provenance.used) result.localization_source = "transliteration";
  return result;
}

module.exports = { buildAnchoredRouteRequest, computeMobileRoute, createStructuredRouteProviders, projectMobileRoute, routeAccepted };
