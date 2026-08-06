"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const CONNECTOR_CDP_ENDPOINT = "http://127.0.0.1:9222";

function normalizedEventUrl(value) {
  const parsed = new URL(value);
  if (parsed.protocol !== "https:" || !["luma.com", "lu.ma"].includes(parsed.hostname)) {
    throw new Error("Connector tab owner requires a public Luma URL");
  }
  return `${parsed.origin}${parsed.pathname.replace(/\/$/, "") || "/"}`;
}

function validPageWebsocket(value, targetId) {
  if (typeof value !== "string") return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "ws:"
      && parsed.hostname === "127.0.0.1"
      && parsed.port === "9222"
      && parsed.pathname === `/devtools/page/${targetId}`;
  } catch {
    return false;
  }
}

function isMatchingEventUrl(value, canonicalUrl) {
  try {
    return normalizedEventUrl(value) === canonicalUrl;
  } catch {
    return false;
  }
}

async function defaultListTargets(endpoint) {
  const response = await fetch(`${endpoint}/json/list`, { signal: AbortSignal.timeout(5_000) });
  if (!response.ok) throw new Error(`Connector target inventory failed with HTTP ${response.status}`);
  const targets = await response.json();
  if (!Array.isArray(targets)) throw new Error("Connector target inventory must be an array");
  return targets;
}

function writePrivateJson(filePath, value) {
  const parent = path.dirname(filePath);
  fs.mkdirSync(parent, { recursive: true, mode: 0o700 });
  const temporary = `${filePath}.${process.pid}.${crypto.randomUUID()}.tmp`;
  try {
    fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600, flag: "wx" });
    fs.renameSync(temporary, filePath);
    fs.chmodSync(filePath, 0o600);
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

function createConnectorTabOwner({
  endpoint = CONNECTOR_CDP_ENDPOINT,
  listTargets = () => defaultListTargets(endpoint),
  ownerToken = () => crypto.randomUUID(),
  now = () => new Date(),
} = {}) {
  if (endpoint !== CONNECTOR_CDP_ENDPOINT) {
    throw new Error("Connector tab owner is restricted to CloakBrowser :9222");
  }
  if (typeof listTargets !== "function") throw new Error("listTargets is required");

  return Object.freeze({
    async captureBaseline() {
      const targets = await listTargets();
      if (!Array.isArray(targets)) throw new Error("Connector target inventory must be an array");
      return Object.freeze(targets
        .filter((target) => target && target.type === "page" && typeof target.id === "string")
        .map((target) => target.id));
    },
    async claim({ canonicalUrl, baselineTargetIds = [], receiptPath } = {}) {
      const normalizedCanonicalUrl = normalizedEventUrl(canonicalUrl);
      const baseline = new Set(baselineTargetIds.map(String));
      const targets = await listTargets();
      if (!Array.isArray(targets)) throw new Error("Connector target inventory must be an array");
      const matches = targets.filter((target) => (
        target
        && target.type === "page"
        && typeof target.id === "string"
        && !baseline.has(target.id)
        && isMatchingEventUrl(target.url, normalizedCanonicalUrl)
        && validPageWebsocket(target.webSocketDebuggerUrl, target.id)
      ));
      if (matches.length !== 1) {
        throw new Error(`Expected exactly one owned Luma page; observed ${matches.length}`);
      }
      const target = matches[0];
      const token = ownerToken();
      if (typeof token !== "string" || token.length === 0) throw new Error("Owner token is required");
      const receipt = Object.freeze({
        schema_version: 1,
        endpoint,
        owner_token: token,
        target_id: target.id,
        page_websocket: target.webSocketDebuggerUrl,
        baseline_target_ids: [...baseline],
        canonical_url: normalizedCanonicalUrl,
        observed_at: now().toISOString(),
      });
      if (receiptPath !== undefined) writePrivateJson(receiptPath, receipt);
      return receipt;
    },
  });
}

module.exports = {
  CONNECTOR_CDP_ENDPOINT,
  createConnectorTabOwner,
};
