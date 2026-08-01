"use strict";

const { timingSafeEqual } = require("node:crypto");

const OPERATIONS = new Set([
  "calendar.list",
  "calendar.events",
  "calendar.find",
  "calendar.create",
  "route.minutes",
]);

function invalid() { throw new Error("Connector host bridge invalid"); }
function unavailable() { throw new Error("Connector host bridge unavailable"); }

function bridgeToken(value) {
  const token = String(value == null ? "" : value).trim();
  if (!/^[A-Za-z0-9_-]{32,256}$/.test(token)) invalid();
  return token;
}

function authorize(header, expected) {
  const supplied = String(header == null ? "" : header);
  const prefix = "Bearer ";
  if (!supplied.startsWith(prefix)) unavailable();
  const actual = Buffer.from(supplied.slice(prefix.length), "utf8");
  const wanted = Buffer.from(expected, "utf8");
  if (actual.length !== wanted.length || !timingSafeEqual(actual, wanted)) unavailable();
}

function exactEnvelope(body) {
  if (
    !body || typeof body !== "object" || Array.isArray(body)
    || Object.keys(body).sort().join(",") !== "input,operation"
    || !OPERATIONS.has(body.operation)
    || !body.input || typeof body.input !== "object" || Array.isArray(body.input)
  ) invalid();
  return body;
}

async function dispatchConnectorHostBridge(request = {}, dependencies = {}) {
  const token = bridgeToken(dependencies.token);
  authorize(request.authorization, token);
  const { operation, input } = exactEnvelope(request.body);
  const calendar = dependencies.calendar;
  try {
    if (operation === "calendar.list") {
      if (!calendar || typeof calendar.listCalendarsRaw !== "function") unavailable();
      return await calendar.listCalendarsRaw({ strict: true });
    }
    if (operation === "calendar.events") {
      if (!calendar || typeof calendar.listAllEventsRaw !== "function") unavailable();
      return await calendar.listAllEventsRaw(null, { ...input, strict: true });
    }
    if (operation === "calendar.find") {
      if (!calendar || typeof calendar.findConnectorEvents !== "function") unavailable();
      return await calendar.findConnectorEvents(input);
    }
    if (operation === "calendar.create") {
      if (!calendar || typeof calendar.createConnectorEvent !== "function") unavailable();
      return await calendar.createConnectorEvent(input);
    }
    if (typeof dependencies.routeMinutes !== "function") unavailable();
    const minutes = await dependencies.routeMinutes(input);
    if (!Number.isInteger(minutes) || minutes < 0 || minutes > 24 * 60) unavailable();
    return minutes;
  } catch (error) {
    if (error && /^Connector host bridge /.test(error.message)) throw error;
    unavailable();
  }
}

function bridgeEndpoint(value) {
  let url;
  try { url = new URL(String(value == null ? "" : value)); } catch { invalid(); }
  if (
    url.protocol !== "http:"
    || !["host.docker.internal", "127.0.0.1", "localhost"].includes(url.hostname)
    || !url.port || url.username || url.password
    || !["", "/"].includes(url.pathname) || url.search || url.hash
  ) invalid();
  return `${url.origin}/v1/connector`;
}

function createConnectorHostBridgeClient(options = {}) {
  const endpoint = bridgeEndpoint(options.baseUrl);
  const token = bridgeToken(options.token);
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (typeof fetchImpl !== "function") invalid();

  async function call(operation, input) {
    let response;
    try {
      response = await fetchImpl(endpoint, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ operation, input }),
        redirect: "error",
        signal: AbortSignal.timeout(30_000),
      });
      if (!response || response.ok !== true) unavailable();
      const value = await response.json();
      if (
        !value || typeof value !== "object" || Array.isArray(value)
        || Object.keys(value).sort().join(",") !== "ok,result"
        || value.ok !== true
      ) unavailable();
      return value.result;
    } catch { unavailable(); }
  }

  return Object.freeze({
    calendar: Object.freeze({
      listCalendarsRaw() { return call("calendar.list", {}); },
      listAllEventsRaw(_uid, input = {}) { return call("calendar.events", input); },
      findConnectorEvents(input = {}) { return call("calendar.find", input); },
      createConnectorEvent(input = {}) { return call("calendar.create", input); },
    }),
    routeMinutes(input = {}) { return call("route.minutes", input); },
  });
}

module.exports = {
  createConnectorHostBridgeClient,
  dispatchConnectorHostBridge,
};
