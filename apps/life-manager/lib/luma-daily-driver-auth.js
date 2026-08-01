"use strict";

const {
  completeLumaPostAuth,
  requestLumaEmailLogin,
  submitLumaCode,
} = require("../scripts/browser-auth-luma-bootstrap.js");

const LUMA_HOME_URL = "https://luma.com/home";
const LUMA_SIGNIN_URL = "https://luma.com/signin";

function unavailable() {
  return new Error("Luma authentication unavailable");
}

function requiredText(value, max = 320) {
  const text = String(value == null ? "" : value).trim();
  return text && text.length <= max ? text : "";
}

async function inspectDailyDriverLumaAuth(page) {
  if (!page || typeof page.evaluate !== "function") throw unavailable();
  const state = await page.evaluate(() => {
    const visible = (element) => {
      if (!element) return false;
      const style = getComputedStyle(element);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
        return false;
      }
      const rect = element.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };
    const body = String(document.body && document.body.innerText || "").toLowerCase();
    const marker = ["create event", "my events", "manage events"]
      .find((text) => body.includes(text)) || null;
    const authInput = Array.from(document.querySelectorAll("input")).filter(visible).some((input) => {
      const type = String(input.type || "").toLowerCase();
      const autocomplete = String(input.autocomplete || "").toLowerCase();
      return type === "email" || type === "password" || autocomplete === "one-time-code";
    });
    const authAction = Array.from(document.querySelectorAll("button, a[href], [role=button]"))
      .filter(visible)
      .some((element) => /^(?:sign\s*in|log\s*in|login)$/i.test(
        String(element.innerText || element.getAttribute("aria-label") || "").trim(),
      ));
    return {
      origin: location.origin,
      path: location.pathname,
      authenticated: Boolean(marker) && !authInput && !authAction,
      loginRequired: authInput || authAction || /(?:^|\/)(?:login|signin|sign-in)(?:\/|$)/i.test(location.pathname),
    };
  });
  if (!state || state.origin !== "https://luma.com") throw unavailable();
  if (state.authenticated === true) return Object.freeze({ status: "authenticated" });
  if (state.loginRequired === true) return Object.freeze({ status: "login_required" });
  return Object.freeze({ status: "unknown" });
}

function createLumaDailyDriverAuth(options = {}) {
  const dailyDriver = options.dailyDriver;
  const email = requiredText(options.email);
  const name = requiredText(options.name);
  const now = options.now || Date.now;
  const inspectAuth = options.inspectAuth || inspectDailyDriverLumaAuth;
  const readLoginCode = options.readLoginCode;
  const submitCode = options.submitCode || submitLumaCode;
  const finishPostAuth = options.finishPostAuth || ((page, fullName) => (
    completeLumaPostAuth(
      page,
      fullName,
      (ms) => typeof page.waitForTimeout === "function"
        ? page.waitForTimeout(ms)
        : new Promise((resolve) => setTimeout(resolve, ms)),
    )
  ));
  const requestLogin = options.requestLogin || (async (page, account) => {
    if (!page || typeof page.goto !== "function") throw unavailable();
    await page.goto(LUMA_SIGNIN_URL, { waitUntil: "domcontentloaded", timeout: 30_000 });
    await requestLumaEmailLogin(page, account);
    if (typeof page.waitForTimeout === "function") await page.waitForTimeout(2_000);
  });
  if (
    !dailyDriver
    || typeof dailyDriver.withLumaPage !== "function"
    || !email
    || !/^[^@\s]+@[^@\s]+$/.test(email)
    || !name
    || typeof now !== "function"
    || typeof inspectAuth !== "function"
    || typeof requestLogin !== "function"
    || typeof readLoginCode !== "function"
    || typeof submitCode !== "function"
    || typeof finishPostAuth !== "function"
  ) throw unavailable();

  let inFlight = null;
  async function run() {
    return dailyDriver.withLumaPage(LUMA_HOME_URL, async (page) => {
      const before = await inspectAuth(page);
      if (before && before.status === "authenticated") {
        return Object.freeze({ status: "authenticated", recovered: false });
      }
      if (!before || !["login_required", "unknown"].includes(before.status)) throw unavailable();
      const afterMs = Number(now());
      if (!Number.isSafeInteger(afterMs) || afterMs < 0) throw unavailable();
      await requestLogin(page, email);
      const code = String(await readLoginCode({ afterMs, account: email }) || "");
      if (!/^\d{6}$/.test(code)) throw unavailable();
      await submitCode(page, code);
      await finishPostAuth(page, name);
      const after = await inspectAuth(page);
      if (!after || after.status !== "authenticated") throw unavailable();
      return Object.freeze({ status: "authenticated", recovered: true });
    });
  }

  return Object.freeze({
    ensureAuthenticated() {
      if (!inFlight) {
        inFlight = run().finally(() => { inFlight = null; });
      }
      return inFlight;
    },
  });
}

function createAuthAwareLumaDailyDriver(options = {}) {
  const dailyDriver = options.dailyDriver;
  const auth = options.auth;
  if (
    !dailyDriver
    || typeof dailyDriver.withLumaPage !== "function"
    || !auth
    || typeof auth.ensureAuthenticated !== "function"
  ) throw unavailable();
  return Object.freeze({
    async withLumaPage(url, task) {
      if (typeof task !== "function") throw new Error("CloakBrowser daily-driver task unavailable");
      await auth.ensureAuthenticated();
      return dailyDriver.withLumaPage(url, task);
    },
  });
}

module.exports = {
  LUMA_HOME_URL,
  createAuthAwareLumaDailyDriver,
  createLumaDailyDriverAuth,
  inspectDailyDriverLumaAuth,
};
