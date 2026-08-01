"use strict";

const {
  normalizeLumaEventDetail,
  readRawLumaEventDetail,
} = require("./luma-event-detail.js");

function providerError(message, code, unknownEffect) {
  const error = new Error(message);
  error.code = code;
  error.unknownEffect = unknownEffect === true;
  return error;
}

async function exactControlState(page) {
  return page.evaluate(() => {
    const values = [...document.querySelectorAll(
      'button, a[role="button"], input[type="submit"]',
    )].map((element) => (
      element.innerText || element.value || element.getAttribute("aria-label") || ""
    )).map((value) => value.replace(/\s+/g, " ").trim().toLowerCase()).filter(Boolean);
    const controls = new Set(values);
    return {
      registered: [
        "参加予定",
        "登録済み",
        "マイチケット",
        "my ticket",
        "you're going",
        "you’re going",
        "going",
      ]
        .some((value) => controls.has(value)),
    };
  });
}

async function submitLumaOnPage(page) {
  if (
    !page
    || typeof page.getByRole !== "function"
    || typeof page.waitForTimeout !== "function"
  ) {
    throw providerError("Luma RSVP page unavailable", "LUMA_PAGE_UNAVAILABLE", false);
  }
  const register = page.getByRole("button", {
    name: /^(?:参加登録|ワンクリックで参加登録|ワンクリック申し込み|Register)$/i,
    exact: true,
  }).first();
  if (await register.count() !== 1 || !await register.isVisible()) {
    throw providerError("Luma RSVP control unavailable", "LUMA_CONTROL_UNAVAILABLE", false);
  }
  let effectStarted = false;
  try {
    await register.click();
    effectStarted = true;
    await page.waitForTimeout(1000);
    if ((await exactControlState(page)).registered) {
      return { status: "registered", effect_started: true };
    }

    const dialog = page.getByRole("dialog").last();
    if (await dialog.count() === 1 && await dialog.isVisible()) {
      const required = dialog.locator("input[required], textarea[required], select[required]");
      for (let index = 0; index < await required.count(); index += 1) {
        const input = required.nth(index);
        if (!String(await input.inputValue()).trim()) {
          throw providerError(
            "Luma RSVP required form input unavailable",
            "LUMA_FORM_INPUT_REQUIRED",
            true,
          );
        }
      }
      const confirm = dialog.getByRole("button", {
        name: /^(?:参加登録|Register|Submit|Confirm RSVP)$/i,
        exact: true,
      }).last();
      if (await confirm.count() !== 1 || !await confirm.isVisible()) {
        throw providerError("Luma RSVP confirm control unavailable", "LUMA_CONFIRM_UNAVAILABLE", true);
      }
      await confirm.click();
      await page.waitForTimeout(1500);
      if ((await exactControlState(page)).registered) {
        return { status: "registered", effect_started: true };
      }
    }
    return { status: "unknown", effect_started: true };
  } catch (error) {
    if (error && typeof error === "object" && typeof error.unknownEffect === "boolean") {
      throw error;
    }
    throw providerError("Luma RSVP browser action failed", "LUMA_BROWSER_ACTION_FAILED", effectStarted);
  }
}

function createLumaBrowserProvider(options = {}) {
  const dailyDriver = options.dailyDriver;
  const evidenceStore = options.evidenceStore;
  const readRawDetail = options.readRawDetail || readRawLumaEventDetail;
  const submitOnPage = options.submitOnPage || submitLumaOnPage;
  const now = options.now || (() => new Date().toISOString());
  if (!dailyDriver || typeof dailyDriver.withLumaPage !== "function") {
    throw new Error("Luma browser provider daily-driver unavailable");
  }
  if (!evidenceStore || typeof evidenceStore.record !== "function") {
    throw new Error("Luma browser provider evidence store unavailable");
  }

  async function detail(page, contract) {
    const value = normalizeLumaEventDetail(
      await readRawDetail(page, contract.canonical_url),
    );
    if (!value || value.event_ref !== contract.event_ref) {
      return null;
    }
    return value;
  }

  async function proof(page, contract) {
    if (typeof page.screenshot !== "function") {
      throw providerError("Luma evidence screenshot unavailable", "LUMA_EVIDENCE_UNAVAILABLE", true);
    }
    const screenshot = await page.screenshot({ type: "png", fullPage: true });
    const refs = await evidenceStore.record({
      tenantId: contract.tenant_id,
      eventRef: contract.event_ref,
      observedAt: now(),
      screenshot,
    });
    return Object.freeze({
      state: "registered",
      external_receipt_ref: refs.external_receipt_ref,
      artifact_ref: refs.artifact_ref,
      canonical_url: contract.canonical_url,
    });
  }

  return Object.freeze({
    inspectRegistration(contract) {
      return dailyDriver.withLumaPage(contract.canonical_url, async (page) => {
        const value = await detail(page, contract);
        if (!value) return { state: "unknown" };
        if (value.auth_status === "login_required") return { state: "login_required" };
        if (value.rsvp_status === "registered") return proof(page, contract);
        if (
          value.event_status !== "scheduled"
          || ["full", "waitlist", "approval_required"].includes(value.rsvp_status)
        ) {
          return {
            state: "unavailable",
            reason: value.event_status !== "scheduled" ? value.event_status : value.rsvp_status,
          };
        }
        if (value.rsvp_status === "available") return { state: "absent" };
        return { state: "unknown" };
      });
    },

    submitRegistration(contract) {
      return dailyDriver.withLumaPage(contract.canonical_url, async (page) => {
        const before = await detail(page, contract);
        if (!before) throw providerError("Luma detail unavailable", "LUMA_DETAIL_UNAVAILABLE", false);
        if (before.auth_status === "login_required") {
          throw providerError("Luma login required", "LUMA_LOGIN_REQUIRED", false);
        }
        if (before.rsvp_status === "registered") return proof(page, contract);
        if (before.rsvp_status !== "available" || before.event_status !== "scheduled") {
          throw providerError("Luma RSVP unavailable", "LUMA_RSVP_UNAVAILABLE", false);
        }
        let outcome;
        try {
          outcome = await submitOnPage(page, contract);
        } catch (error) {
          if (error && typeof error === "object" && typeof error.unknownEffect === "boolean") {
            throw error;
          }
          throw providerError("Luma RSVP submit failed", "LUMA_SUBMIT_FAILED", true);
        }
        if (!outcome || outcome.status !== "registered") {
          throw providerError(
            "Luma RSVP result unverified",
            "LUMA_RESULT_UNVERIFIED",
            outcome && outcome.effect_started === true,
          );
        }
        return proof(page, contract);
      });
    },
  });
}

module.exports = {
  createLumaBrowserProvider,
  submitLumaOnPage,
};
