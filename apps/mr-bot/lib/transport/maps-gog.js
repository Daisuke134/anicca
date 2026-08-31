"use strict";

const { execFileSync } = require("node:child_process");

function invalid() { throw new Error("Connector route invalid"); }
function unavailable() { throw new Error("Connector route unavailable"); }

function location(value) {
  const raw = String(value == null ? "" : value);
  if (/[\x00-\x1f\x7f]/.test(raw)) invalid();
  const text = raw.replace(/\s+/g, " ").trim();
  if (!text || text.length > 2_000 || /^-/.test(text)) invalid();
  return text;
}

function validateAnchor(value) {
  if (value == null || value === "") return;
  const text = String(value).trim();
  if (!Number.isFinite(Date.parse(text)) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) invalid();
}

function parseMinutes(raw) {
  let value;
  try { value = JSON.parse(String(raw)); } catch { unavailable(); }
  const directions = value && value.directions;
  const route = directions && directions.status === "OK"
    && Array.isArray(directions.routes) && directions.routes[0];
  if (!route || !Array.isArray(route.legs) || route.legs.length < 1) unavailable();
  let seconds = 0;
  for (const leg of route.legs) {
    const duration = Number(leg && leg.duration && leg.duration.value);
    if (!Number.isFinite(duration) || duration <= 0 || duration > 24 * 60 * 60) unavailable();
    seconds += duration;
  }
  const minutes = Math.ceil(seconds / 60);
  if (!Number.isSafeInteger(minutes) || minutes < 1 || minutes > 24 * 60) unavailable();
  return minutes;
}

function makeGogRouteMinutes({ bin, run } = {}) {
  const gogBin = String(bin || process.env.GOG_BIN || "gog").trim();
  if (!gogBin || (!run && /^-/.test(gogBin))) invalid();
  const execute = run || ((args) => execFileSync(gogBin, args, {
    env: process.env,
    encoding: "utf8",
    timeout: 30_000,
    maxBuffer: 2 * 1024 * 1024,
  }));
  return async function routeMinutes(input = {}) {
    const from = location(input.from);
    const to = location(input.to);
    validateAnchor(input.anchor_at);
    if (from === to) return 0;
    let raw;
    try {
      raw = execute([
        "maps", "directions",
        `--origin=${from}`,
        `--destination=${to}`,
        "--mode=transit",
        "--language=ja",
        "--region=jp",
        "--json",
        "--no-input",
        "--enable-commands=maps.directions",
      ]);
    } catch { unavailable(); }
    return parseMinutes(raw);
  };
}

module.exports = { makeGogRouteMinutes };
