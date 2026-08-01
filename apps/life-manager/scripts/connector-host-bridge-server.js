#!/usr/bin/env node
"use strict";

const http = require("node:http");

const { dispatchConnectorHostBridge } = require("../lib/connector-host-bridge.js");
const { createConnectorRouteMinutes } = require("../lib/connector-route-minutes.js");
const { makeGogCalendar } = require("../lib/transport/calendar-gog.js");

const MAX_BODY_BYTES = 16 * 1024;

function json(res, statusCode, value) {
  const body = Buffer.from(JSON.stringify(value), "utf8");
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": String(body.length),
    "Cache-Control": "no-store",
  });
  res.end(body);
}

function createConnectorHostBridgeServer(dependencies = {}) {
  return http.createServer((req, res) => {
    if (req.method !== "POST" || req.url !== "/v1/connector") {
      json(res, 404, { ok: false, error: "not_found" });
      return;
    }
    if (!/^application\/json(?:\s*;|$)/i.test(String(req.headers["content-type"] || ""))) {
      json(res, 415, { ok: false, error: "unsupported_media_type" });
      return;
    }
    const chunks = [];
    let size = 0;
    let oversized = false;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) oversized = true;
      else chunks.push(chunk);
    });
    req.on("error", () => {
      if (!res.headersSent) json(res, 400, { ok: false, error: "bad_request" });
    });
    req.on("end", async () => {
      if (oversized) {
        json(res, 413, { ok: false, error: "payload_too_large" });
        return;
      }
      let body;
      try { body = JSON.parse(Buffer.concat(chunks).toString("utf8")); }
      catch {
        json(res, 400, { ok: false, error: "bad_request" });
        return;
      }
      try {
        const result = await dispatchConnectorHostBridge({
          authorization: req.headers.authorization,
          body,
        }, dependencies);
        json(res, 200, { ok: true, result });
      } catch (error) {
        const invalid = error && / bridge invalid$/.test(error.message);
        json(res, invalid ? 400 : 503, {
          ok: false,
          error: invalid ? "bridge_invalid" : "bridge_unavailable",
        });
      }
    });
  });
}

function requiredEnv(env, name) {
  const value = String(env[name] == null ? "" : env[name]).trim();
  if (!value) throw new Error("Connector host bridge unavailable");
  return value;
}

function runConnectorHostBridgeServer(env = process.env, dependencies = {}) {
  const calendar = dependencies.calendar || makeGogCalendar({
    bin: env.GOG_BIN,
    account: requiredEnv(env, "GOG_ACCOUNT"),
    keyring: env.GOG_KEYRING_PASSWORD,
  });
  const routeMinutes = dependencies.routeMinutes || createConnectorRouteMinutes({
    mapsKey: requiredEnv(env, "GOOGLE_API_KEY_DIRECTIONS"),
  });
  const server = createConnectorHostBridgeServer({
    token: requiredEnv(env, "LM_CONNECTOR_BRIDGE_TOKEN"),
    calendar,
    routeMinutes,
  });
  const port = Number(env.LM_CONNECTOR_BRIDGE_PORT || 18793);
  if (!Number.isSafeInteger(port) || port < 1 || port > 65_535) {
    throw new Error("Connector host bridge unavailable");
  }
  const host = String(env.LM_CONNECTOR_BRIDGE_HOST || "127.0.0.1").trim();
  if (host !== "127.0.0.1") throw new Error("Connector host bridge unavailable");
  server.listen(port, host);
  return server;
}

if (require.main === module) {
  try {
    runConnectorHostBridgeServer();
  } catch {
    process.stderr.write("Connector host bridge unavailable\n");
    process.exitCode = 1;
  }
}

module.exports = {
  createConnectorHostBridgeServer,
  runConnectorHostBridgeServer,
};
