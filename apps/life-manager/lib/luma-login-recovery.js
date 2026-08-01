"use strict";

const {
  classifyLumaLogin,
} = require("./cloakbrowser-daily-driver.js");

const LUMA_HOME_URL = "https://luma.com/home";

async function inspectLumaAuthPage(page) {
  if (!page || typeof page.evaluate !== "function") {
    throw new Error("Luma login recovery page unavailable");
  }
  const snapshot = await page.evaluate(() => {
    const labels = [...document.querySelectorAll('button, a[role="button"], a')]
      .map((element) => (
        element.innerText || element.getAttribute("aria-label") || ""
      ).replace(/\s+/g, " ").trim())
      .filter(Boolean);
    return {
      origin: location.origin,
      path: location.pathname,
      loginForm: Boolean(document.querySelector(
        'form input[type="email"], form input[autocomplete="email"], form input[autocomplete="webauthn"]',
      )),
      signInMarker: labels.some((value) => (
        /^(?:sign in|log in|ログイン|新規登録)$/i.test(value)
      )),
      authenticatedMarker: Boolean(document.querySelector(
        'a[href="/create"], a[href="/home/calendars"]',
      )),
    };
  });
  return classifyLumaLogin(snapshot);
}

async function visible(locator) {
  return locator
    && await locator.count() === 1
    && await locator.isVisible();
}

async function signInWithExistingGoogleSession(page, options = {}) {
  if (
    !page
    || typeof page.getByRole !== "function"
    || typeof page.context !== "function"
  ) {
    throw new Error("Luma Google login unavailable");
  }
  const context = page.context();
  const beforePages = new Set(context.pages());
  const google = page.getByRole("button", {
    name: /^(?:Sign in with Google|Googleでログイン|Googleで続行)$/i,
    exact: true,
  }).first();
  if (!await visible(google)) throw new Error("Luma Google login unavailable");

  const popupPromise = typeof context.waitForEvent === "function"
    ? context.waitForEvent("page", { timeout: 5_000 }).catch(() => null)
    : Promise.resolve(null);
  await google.click();
  const popup = await popupPromise;
  const authPage = popup || page;
  const ownsPopup = popup && !beforePages.has(popup);
  try {
    if (typeof authPage.waitForLoadState === "function") {
      await authPage.waitForLoadState("domcontentloaded", { timeout: 15_000 }).catch(() => {});
    }
    const account = String(options.account || "").trim();
    if (account && typeof authPage.getByText === "function") {
      const accountChoice = authPage.getByText(account, { exact: true }).first();
      if (await visible(accountChoice)) await accountChoice.click();
    }
    if (typeof authPage.getByRole === "function") {
      const consent = authPage.getByRole("button", {
        name: /^(?:Continue|続行)$/i,
        exact: true,
      }).first();
      if (await visible(consent)) await consent.click();
    }
    const deadline = Date.now() + 30_000;
    while (Date.now() < deadline) {
      const lumaPage = [page, authPage].find((candidate) => {
        try {
          return !candidate.isClosed() && new URL(candidate.url()).origin === "https://luma.com";
        } catch {
          return false;
        }
      });
      if (lumaPage) {
        const result = await inspectLumaAuthPage(lumaPage).catch(() => null);
        if (result && result.status === "authenticated") return;
      }
      if (typeof page.waitForTimeout === "function") await page.waitForTimeout(500);
      else await new Promise((resolve) => setTimeout(resolve, 500));
    }
    throw new Error("Luma Google login unavailable");
  } finally {
    if (ownsPopup && popup && !popup.isClosed()) await popup.close().catch(() => {});
  }
}

function createLumaLoginRecovery(options = {}) {
  const dailyDriver = options.dailyDriver;
  const inspectAuth = options.inspectAuth || inspectLumaAuthPage;
  const signInWithGoogle = options.signInWithGoogle || signInWithExistingGoogleSession;
  const account = String(options.account || "").trim();
  if (!dailyDriver || typeof dailyDriver.withLumaPage !== "function") {
    throw new Error("Luma login recovery daily-driver unavailable");
  }
  if (typeof inspectAuth !== "function" || typeof signInWithGoogle !== "function") {
    throw new Error("Luma login recovery dependency unavailable");
  }

  let inFlight = null;
  async function recoverOnce() {
    return dailyDriver.withLumaPage(LUMA_HOME_URL, async (page) => {
      const before = await inspectAuth(page);
      if (before && before.status === "authenticated") {
        return Object.freeze({ ...before, recovered: false });
      }
      if (!before || before.status !== "login_required") {
        throw new Error("Luma login recovery unverified");
      }
      await signInWithGoogle(page, { account });
      const after = await inspectAuth(page);
      if (!after || after.status !== "authenticated") {
        throw new Error("Luma login recovery unverified");
      }
      return Object.freeze({ ...after, recovered: true });
    });
  }

  return Object.freeze({
    recover() {
      if (inFlight) return inFlight;
      inFlight = recoverOnce().finally(() => { inFlight = null; });
      return inFlight;
    },
  });
}

module.exports = {
  createLumaLoginRecovery,
  inspectLumaAuthPage,
  signInWithExistingGoogleSession,
};
