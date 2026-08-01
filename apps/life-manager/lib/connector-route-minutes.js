"use strict";

const { directionsMinutes: productionDirectionsMinutes } = require("./travel.js");

function invalid() { throw new Error("Connector route invalid"); }
function unavailable() { throw new Error("Connector route unavailable"); }

function safeLocation(value) {
  const raw = String(value == null ? "" : value);
  if (/[\x00-\x1f\x7f]/.test(raw)) invalid();
  const text = raw.replace(/\s+/g, " ").trim();
  if (!text || text.length > 2_000 || /^-/.test(text)) invalid();
  return text;
}

function createConnectorRouteMinutes(options = {}) {
  const mapsKey = String(options.mapsKey == null ? "" : options.mapsKey).trim();
  if (!mapsKey) unavailable();
  const directionsMinutes = options.directionsMinutes || productionDirectionsMinutes;
  const now = options.now || Date.now;
  const homeRef = String(options.homeRef == null ? "" : options.homeRef).trim();
  const homeLocation = String(options.homeLocation == null ? "" : options.homeLocation).trim();
  if (typeof directionsMinutes !== "function" || typeof now !== "function") invalid();
  return async function routeMinutes(input = {}) {
    if (!['inbound', 'outbound'].includes(input.direction)) invalid();
    const resolveLocation = (value) => {
      const location = safeLocation(value);
      if (homeRef && location === homeRef) {
        if (!homeLocation) unavailable();
        return safeLocation(homeLocation);
      }
      return location;
    };
    const from = resolveLocation(input.from);
    const to = resolveLocation(input.to);
    const anchorAt = String(input.anchor_at == null ? "" : input.anchor_at).trim();
    const anchorMs = Date.parse(anchorAt);
    if (!Number.isFinite(anchorMs) || !/[zZ]|[+-]\d\d:\d\d$/.test(anchorAt)) invalid();
    let minutes;
    try {
      minutes = await directionsMinutes(
        from,
        to,
        mapsKey,
        anchorMs,
        Number(now()),
        input.direction === "outbound",
      );
    } catch { unavailable(); }
    if (!Number.isFinite(minutes) || minutes < 0 || minutes > 24 * 60) unavailable();
    return Math.ceil(minutes);
  };
}

module.exports = { createConnectorRouteMinutes };
