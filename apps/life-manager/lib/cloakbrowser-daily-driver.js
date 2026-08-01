"use strict";

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

function createCloakBrowserDailyDriver(options = {}) {
  const endpoint = String(options.endpoint || DAILY_DRIVER_CDP).trim();
  const connectOverCDP = options.connectOverCDP;
  const resolveEndpoint = options.resolveEndpoint || (async () => endpoint);
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
      const url = lumaUrl(value);
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
    },
  });
}

module.exports = {
  DAILY_DRIVER_CDP,
  classifyLumaLogin,
  createCloakBrowserDailyDriver,
  resolvedDailyDriverEndpoint,
};
