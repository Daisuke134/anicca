"use strict";

function providerError(message, code, unknownEffect) {
  const error = new Error(message);
  error.code = code;
  error.unknownEffect = unknownEffect === true;
  return error;
}

function verifiedContract(value) {
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || !/^[a-z0-9][a-z0-9._-]{0,63}$/.test(String(value.tenant_id || ""))
    || !/^connpass-event:\/\/event\/[1-9][0-9]*$/.test(String(value.event_ref || ""))
  ) throw providerError("Connpass contract unavailable", "CONNPASS_CONTRACT_UNAVAILABLE", false);
  let url;
  try { url = new URL(String(value.canonical_url || "")); } catch {
    throw providerError("Connpass contract unavailable", "CONNPASS_CONTRACT_UNAVAILABLE", false);
  }
  if (
    url.protocol !== "https:" || url.username || url.password
    || !(url.hostname === "connpass.com" || url.hostname.endsWith(".connpass.com"))
  ) throw providerError("Connpass contract unavailable", "CONNPASS_CONTRACT_UNAVAILABLE", false);
  return value;
}

async function readConnpassRegistrationStateOnPage(page) {
  if (!page || typeof page.evaluate !== "function") {
    throw providerError("Connpass page unavailable", "CONNPASS_PAGE_UNAVAILABLE", false);
  }
  let value;
  try {
    value = await page.evaluate(() => {
      const path = String(location.pathname || "").toLowerCase();
      const body = String(document.body && document.body.innerText || "").replace(/\s+/g, " ").trim();
      const controls = [...document.querySelectorAll('button,a[role="button"],a.btn,input[type="submit"]')]
        .map((element) => String(element.innerText || element.value || element.getAttribute("aria-label") || "")
          .replace(/\s+/g, " ").trim()).filter(Boolean);
      const exact = (values) => controls.some((control) => values.includes(control));
      if (/\/(?:login|signin)(?:\/|$)/.test(path) || exact(["ログイン", "Login"])) {
        return { state: "login_required" };
      }
      if (exact(["参加票を表示", "受付票を見る", "申し込みをキャンセル", "キャンセルする", "Registered"])) {
        return { state: "registered" };
      }
      if (/抽選待ち|補欠|承認待ち|キャンセル待ち/.test(body)) return { state: "pending" };
      if (/受付終了|募集終了|満員|定員に達しました/.test(body)) return { state: "unavailable", reason: "closed" };
      if (exact(["このイベントに申し込む", "イベントに申し込む", "参加申し込み", "申し込む"])) {
        return { state: "absent" };
      }
      return { state: "unknown" };
    });
  } catch {
    throw providerError("Connpass readback unavailable", "CONNPASS_READBACK_UNAVAILABLE", false);
  }
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || !["absent", "login_required", "registered", "pending", "unavailable", "unknown"].includes(value.state)
  ) throw providerError("Connpass readback unavailable", "CONNPASS_READBACK_UNAVAILABLE", false);
  return Object.freeze({ state: value.state, ...(value.state === "unavailable" ? { reason: "closed" } : {}) });
}

async function submitConnpassOnPage(page, _contract, dependencies = {}) {
  const readState = dependencies.readState || readConnpassRegistrationStateOnPage;
  const before = await readState(page);
  if (["registered", "pending"].includes(before.state)) {
    return { status: before.state, effect_started: false };
  }
  if (before.state !== "absent") {
    throw providerError(`Connpass registration ${before.state}`, "CONNPASS_REGISTRATION_UNAVAILABLE", false);
  }
  if (!page || typeof page.getByRole !== "function" || typeof page.waitForTimeout !== "function") {
    throw providerError("Connpass control unavailable", "CONNPASS_CONTROL_UNAVAILABLE", false);
  }
  const control = page.getByRole("link", {
    name: /^(?:このイベントに申し込む|イベントに申し込む|参加申し込み|申し込む)$/,
    exact: true,
  }).first();
  if (await control.count() !== 1 || !await control.isVisible()) {
    throw providerError("Connpass control unavailable", "CONNPASS_CONTROL_UNAVAILABLE", false);
  }
  try {
    await control.click();
    await page.waitForTimeout(1_000);
    const after = await readState(page);
    return { status: after.state, effect_started: true };
  } catch (error) {
    if (error && typeof error.unknownEffect === "boolean") throw error;
    throw providerError("Connpass browser action failed", "CONNPASS_BROWSER_ACTION_FAILED", true);
  }
}

function createConnpassBrowserProvider(options = {}) {
  const dailyDriver = options.dailyDriver;
  const evidenceStore = options.evidenceStore;
  const readState = options.readState || readConnpassRegistrationStateOnPage;
  const submitOnPage = options.submitOnPage || ((page, contract) => (
    submitConnpassOnPage(page, contract, { readState })
  ));
  const now = options.now || (() => new Date().toISOString());
  if (!dailyDriver || typeof dailyDriver.withEventPage !== "function") {
    throw new Error("Connpass browser provider daily-driver unavailable");
  }
  if (!evidenceStore || typeof evidenceStore.record !== "function") {
    throw new Error("Connpass browser provider evidence store unavailable");
  }

  async function proof(page, contract, registrationStatus) {
    if (!page || typeof page.screenshot !== "function") {
      throw providerError("Connpass screenshot unavailable", "CONNPASS_EVIDENCE_UNAVAILABLE", true);
    }
    const screenshot = await page.screenshot({ type: "png", fullPage: true });
    const refs = await evidenceStore.record({
      tenantId: contract.tenant_id, eventRef: contract.event_ref, observedAt: now(), screenshot,
    });
    return Object.freeze({
      state: "registered", registration_status: registrationStatus,
      external_receipt_ref: refs.external_receipt_ref,
      artifact_ref: refs.artifact_ref,
      canonical_url: contract.canonical_url,
    });
  }

  return Object.freeze({
    inspectRegistration(rawContract) {
      const contract = verifiedContract(rawContract);
      return dailyDriver.withEventPage("connpass", contract.canonical_url, async (page) => {
        const state = await readState(page);
        if (["registered", "pending"].includes(state.state)) return proof(page, contract, state.state);
        return state;
      });
    },
    submitRegistration(rawContract) {
      const contract = verifiedContract(rawContract);
      return dailyDriver.withEventPage("connpass", contract.canonical_url, async (page) => {
        const before = await readState(page);
        if (["registered", "pending"].includes(before.state)) return proof(page, contract, before.state);
        if (before.state !== "absent") {
          throw providerError("Connpass registration unavailable", "CONNPASS_REGISTRATION_UNAVAILABLE", false);
        }
        const outcome = await submitOnPage(page, contract);
        if (!outcome || !["registered", "pending"].includes(outcome.status)) {
          throw providerError("Connpass result unverified", "CONNPASS_RESULT_UNVERIFIED", outcome && outcome.effect_started);
        }
        return proof(page, contract, outcome.status);
      });
    },
  });
}

module.exports = {
  createConnpassBrowserProvider,
  readConnpassRegistrationStateOnPage,
  submitConnpassOnPage,
};
