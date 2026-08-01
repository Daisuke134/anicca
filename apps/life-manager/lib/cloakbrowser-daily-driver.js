"use strict";
const { verifyPersistedFunderGates } = require("./funder-persisted-gate-verifier.js");

const DAILY_DRIVER_CDP = "http://127.0.0.1:9222";
const LUMA_HOSTS = new Set(["luma.com", "www.luma.com", "lu.ma"]);

function lumaUrl(value) {
  let url;
  try {
    url = new URL(String(value == null ? "" : value).trim());
  } catch {
    throw new Error("Luma URL invalid");
  }
  const hostname = url.hostname.toLowerCase();
  if (
    url.protocol !== "https:"
    || url.username
    || url.password
    || (!LUMA_HOSTS.has(hostname) && !hostname.endsWith(".luma.com"))
  ) {
    throw new Error("Luma URL invalid");
  }
  url.hash = "";
  return url.toString();
}

function funderUrl(value, policy = {}) {
  let url;
  try { url = new URL(String(value == null ? "" : value).trim()); }
  catch { throw new Error("Funder form URL invalid"); }
  const origins = policy.allowed_origins;
  if (url.protocol !== "https:" || url.username || url.password || !/^[a-z0-9][a-z0-9._-]{1,99}$/.test(String(policy.funder_id || ""))
    || !Array.isArray(origins) || origins.length < 1 || origins.length > 50
    || origins.some((origin) => {
      try { const allowed = new URL(origin); return allowed.origin !== origin || allowed.protocol !== "https:" || allowed.username || allowed.password; }
      catch { return true; }
    }) || !origins.includes(url.origin)) throw new Error("Funder form URL invalid");
  url.hash = "";
  return url.toString();
}

function tokyoDay(milliseconds) {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(milliseconds));
  const get = (type) => parts.find((part) => part.type === type).value;
  return `${get("year")}-${get("month")}-${get("day")}`;
}

function submissionDayGate(value, policy, now) {
  if (!value || value.schema_version !== 1 || value.decision !== "allow" || value.submit_allowed !== true
    || value.funder_id !== policy.funder_id || value.tenant_id !== policy.tenant_id || value.attempt_id !== policy.attempt_id
    || !String(value.tenant_id || "").trim()
    || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value.attempt_id || ""))
    || !/^funder-day-gate:[0-9a-f]{64}$/.test(String(value.gate_id || ""))
    || value.gate_digest !== value.gate_id.slice(value.gate_id.indexOf(":") + 1)
    || value.tokyo_day !== tokyoDay(now)) {
    throw new Error("Funder submission-day gate invalid");
  }
  return value;
}

function assetFreshnessGate(value, policy, now) {
  const evaluated = Date.parse(String(value && value.evaluated_at || ""));
  const expires = Date.parse(String(value && value.expires_at || ""));
  if (!value || value.schema_version !== 1 || value.decision !== "allow" || value.submit_allowed !== true
    || value.funder_id !== policy.funder_id || value.tenant_id !== policy.tenant_id || value.attempt_id !== policy.attempt_id
    || !String(value.tenant_id || "").trim()
    || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value.attempt_id || ""))
    || !/^funder-freshness-gate:[0-9a-f]{64}$/.test(String(value.gate_id || ""))
    || value.gate_digest !== value.gate_id.slice(value.gate_id.indexOf(":") + 1)
    || !Number.isFinite(evaluated) || !Number.isFinite(expires) || evaluated > now || expires <= now) {
    throw new Error("Funder asset freshness gate invalid");
  }
  return value;
}

function safePath(value) {
  const path = String(value == null ? "" : value).trim();
  return path.startsWith("/") && path.length <= 500 ? path : "/";
}

function classifyLumaLogin(input = {}) {
  if (input.origin !== "https://luma.com") {
    throw new Error("Luma login origin invalid");
  }
  const path = safePath(input.path);
  const loginRequired = input.loginForm === true
    || input.signInMarker === true
    || /(?:^|\/)(?:login|log-in|signin|sign-in)(?:\/|$)/i.test(path);
  const status = loginRequired
    ? "login_required"
    : input.authenticatedMarker === true
      ? "authenticated"
      : "unknown";
  return Object.freeze({ status, origin: input.origin, path });
}

function isPrivateIpv4(hostname) {
  const parts = String(hostname).split(".").map(Number);
  if (
    parts.length !== 4
    || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)
  ) return false;
  return parts[0] === 10
    || (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31)
    || (parts[0] === 192 && parts[1] === 168);
}

function resolvedDailyDriverEndpoint(value) {
  let url;
  try {
    url = new URL(String(value == null ? "" : value).trim());
  } catch {
    throw new Error("CloakBrowser resolved endpoint invalid");
  }
  const hostname = url.hostname.toLowerCase();
  if (
    url.protocol !== "http:"
    || url.username
    || url.password
    || url.port !== "9222"
    || url.pathname !== "/"
    || url.search
    || url.hash
    || (hostname !== "127.0.0.1" && hostname !== "localhost" && !isPrivateIpv4(hostname))
  ) {
    throw new Error("CloakBrowser resolved endpoint invalid");
  }
  return url.origin;
}

function createDriver(options = {}, persistedVerifier) {
  const endpoint = String(options.endpoint || DAILY_DRIVER_CDP).trim();
  const connectOverCDP = options.connectOverCDP;
  const resolveEndpoint = options.resolveEndpoint || (async () => endpoint);
  const now = options.now || (() => Date.now());
  if (endpoint !== DAILY_DRIVER_CDP) {
    throw new Error("CloakBrowser daily-driver endpoint invalid");
  }
  if (typeof connectOverCDP !== "function") {
    throw new Error("CloakBrowser daily-driver connector unavailable");
  }
  if (typeof resolveEndpoint !== "function") {
    throw new Error("CloakBrowser daily-driver resolver unavailable");
  }

  return Object.freeze({
    async withLumaPage(value, task) {
      return withOwnedPage(lumaUrl(value), task);
    },
    async withFunderPage(value, policy, gate, freshnessGate, submission, task) {
      const evaluatedNow = now();
      const verifiedDayGate = submissionDayGate(gate, policy, evaluatedNow);
      const verifiedFreshnessGate = assetFreshnessGate(freshnessGate, policy, evaluatedNow);
      if (verifiedDayGate.tenant_id !== verifiedFreshnessGate.tenant_id
        || verifiedDayGate.attempt_id !== verifiedFreshnessGate.attempt_id) {
        throw new Error("Funder gate attempt binding invalid");
      }
      const persisted = await persistedVerifier(verifiedDayGate, verifiedFreshnessGate, submission);
      if (!persisted || !persisted.submission || typeof persisted.cleanup !== "function") {
        throw new Error("Funder persisted gate verification invalid");
      }
      try {
        return await withOwnedPage(funderUrl(value, policy), (page, metadata) => task(page, Object.freeze({ ...metadata, submission: persisted.submission })));
      } finally {
        persisted.cleanup();
      }
    },
  });

  async function withOwnedPage(url, task) {
      if (typeof task !== "function") {
        throw new Error("CloakBrowser daily-driver task unavailable");
      }
      const connectionEndpoint = resolvedDailyDriverEndpoint(await resolveEndpoint(endpoint));
      const browser = await connectOverCDP(connectionEndpoint);
      const contexts = browser && typeof browser.contexts === "function"
        ? browser.contexts()
        : [];
      if (!Array.isArray(contexts) || contexts.length !== 1) {
        throw new Error("CloakBrowser shared context unavailable");
      }
      const context = contexts[0];
      const existingPages = typeof context.pages === "function" ? context.pages() : [];
      if (typeof context.newPage !== "function") {
        throw new Error("CloakBrowser shared context unavailable");
      }
      const page = await context.newPage();
      try {
        await page.goto(url, {
          waitUntil: "domcontentloaded",
          timeout: 30_000,
        });
        return await task(page, Object.freeze({
          endpoint,
          existing_page_count: Array.isArray(existingPages) ? existingPages.length : 0,
        }));
      } finally {
        if (page && typeof page.close === "function") await page.close();
      }
  }
}

function createCloakBrowserDailyDriver(options = {}) {
  return createDriver(options, verifyPersistedFunderGates);
}

function createCloakBrowserDailyDriverForTest(options = {}, persistedVerifier) {
  if (typeof persistedVerifier !== "function") throw new Error("test persisted gate verifier unavailable");
  return createDriver(options, persistedVerifier);
}

module.exports = {
  DAILY_DRIVER_CDP,
  classifyLumaLogin,
  createCloakBrowserDailyDriver,
  createCloakBrowserDailyDriverForTest,
  resolvedDailyDriverEndpoint,
};
