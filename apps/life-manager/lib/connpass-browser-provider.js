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
      const rawPath = String(location.pathname || "");
      const path = rawPath.toLowerCase();
      const bodyText = String(document.body && document.body.innerText || "");
      const body = bodyText.replace(/\s+/g, " ").trim();
      const lines = bodyText.split(/\r?\n/).map((line) => line.replace(/\s+/g, " ").trim()).filter(Boolean);
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
      if (/^\/event\/[1-9][0-9]*\/$/.test(rawPath) && ["抽選待ち", "補欠", "承認待ち", "キャンセル待ち"].some((marker) => lines.includes(marker))) return { state: "pending" };
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

// Rules (owner-decided): a tier qualifies only if it is free (no yen
// amount), not disabled, has room (an "n/m人" cap with n < m, or no cap at
// all), and carries none of Dais's disqualifying restriction markers.
// Among qualifying tiers, an in-person one is preferred over an online one;
// first qualifying tier in document order wins within each preference.
const TIER_RESTRICTION_PATTERN = /学生|招待|登壇|発表|LT枠|スタッフ|関係者|主催|懇親会のみ/;
const TIER_YEN_PATTERN = /¥|\d[,\d]*\s*円/;
const TIER_ONLINE_PATTERN = /オンライン|リモート|配信|視聴|Zoom|Google\s*meet/i;
const TIER_CAPACITY_PATTERN = /(\d+)\s*\/\s*(\d+)\s*人/;

function selectParticipationTierIndex(tiers) {
  const qualifying = (Array.isArray(tiers) ? tiers : [])
    .map((tier, index) => ({
      index,
      disabled: tier && tier.disabled === true,
      label: String((tier && tier.label) || ""),
    }))
    .filter((tier) => {
      if (tier.disabled) return false;
      if (!/無料/.test(tier.label) || TIER_YEN_PATTERN.test(tier.label)) return false;
      if (TIER_RESTRICTION_PATTERN.test(tier.label)) return false;
      const capacity = tier.label.match(TIER_CAPACITY_PATTERN);
      if (capacity && !(Number(capacity[1]) < Number(capacity[2]))) return false;
      return true;
    });
  if (qualifying.length === 0) return -1;
  const inPerson = qualifying.find((tier) => !TIER_ONLINE_PATTERN.test(tier.label));
  return (inPerson || qualifying[0]).index;
}

async function selectParticipationTier(participationGroup) {
  const tiers = await participationGroup.evaluateAll((radios) => radios.map((radio) => {
    const row = radio.closest("li,tr,div,label");
    const label = String((row && row.innerText) || "").replace(/\s+/g, " ").trim();
    return { disabled: radio.disabled === true, label };
  }));
  const index = selectParticipationTierIndex(tiers);
  if (index === -1) {
    throw providerError("Connpass participation tier unavailable", "CONNPASS_TIER_UNAVAILABLE", false);
  }
  await participationGroup.nth(index).check();
}

// Real Connpass join pages (measured live, see
// connector-production-browser-harness.js's connpassJoin handling and
// docs/superpowers/plans/2026-08-11-connector-connpass-real-dom-observation-14e.md)
// wrap the participation-type tier radios AND any organizer-added custom
// questions in the same `.question_list` container structure, each with a
// direct `.question` child whose text starts with `必須` (required) or `任意`
// (optional). The tier group is excluded here — it is validated and clicked
// by selectParticipationTier above, not by this check — leaving only
// organizer questionnaire groups. Connpass silently no-ops the confirm click
// when a required questionnaire field is empty, so this must run before any
// radio is checked or the confirm button is clicked.
async function hasUnansweredRequiredQuestionnaire(page) {
  const groups = page.locator(".question_list");
  return groups.evaluateAll((elements) => elements.some((group) => {
    if (group.querySelector('input[name="participation_type"]')) return false;
    const questionElement = group.querySelector(":scope > .question");
    const questionText = String((questionElement && (questionElement.textContent || questionElement.innerText)) || "")
      .replace(/\s+/g, " ").trim();
    if (!/^必須/.test(questionText)) return false;
    const fields = [...group.querySelectorAll("input,textarea,select")]
      .filter((field) => String(field.type || "").toLowerCase() !== "hidden" && field.disabled !== true);
    if (fields.length === 0) return false;
    const answered = (field) => {
      const type = String(field.type || "").toLowerCase();
      if (type === "radio" || type === "checkbox") {
        const name = String(field.name || "");
        return name
          ? fields.some((candidate) => String(candidate.name || "") === name && candidate.checked === true)
          : field.checked === true;
      }
      return String(field.value || "").trim().length > 0;
    };
    return !fields.every(answered);
  }));
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
  if (
    !page || typeof page.getByRole !== "function" || typeof page.waitForTimeout !== "function"
    || typeof page.locator !== "function" || typeof page.url !== "function" || typeof page.goto !== "function"
  ) {
    throw providerError("Connpass control unavailable", "CONNPASS_CONTROL_UNAVAILABLE", false);
  }
  // Captured before anything is clicked: the confirm click lands on
  // connpass's own post-submission page, not the event page, so the
  // readback below needs to navigate back here to see the registered
  // controls at all.
  const eventUrl = String(page.url() || "");
  if (!eventUrl) {
    throw providerError("Connpass control unavailable", "CONNPASS_CONTROL_UNAVAILABLE", false);
  }
  const joinControl = page.getByRole("link", {
    name: /^(?:このイベントに申し込む|イベントに申し込む|参加申し込み|申し込む)$/,
    exact: true,
  }).first();
  if (await joinControl.count() !== 1 || !await joinControl.isVisible()) {
    throw providerError("Connpass control unavailable", "CONNPASS_CONTROL_UNAVAILABLE", false);
  }

  // Clicking the join link only navigates to the /join/ page — it does not
  // register anyone. Nothing below this point has an external effect until
  // the confirm control is clicked, so failures here are safe to retry.
  let confirmControl;
  try {
    await joinControl.click();
    await page.waitForTimeout(1_000);

    // Fail closed before touching anything else on the join page: a required
    // organizer questionnaire field left empty makes Connpass silently no-op
    // the confirm click later (page stays on /join/, nothing registers). See
    // hasUnansweredRequiredQuestionnaire above for what this matches on.
    if (await hasUnansweredRequiredQuestionnaire(page)) {
      throw providerError("Connpass questionnaire requires an answer", "CONNPASS_QUESTIONNAIRE_REQUIRED", false);
    }

    // On the join page: validate BOTH the participation-type radio and the
    // free-confirm control before touching either. Fail closed — nothing is
    // clicked on this page until both targets are proven present.
    const participationGroup = page.locator('input[name="participation_type"]');
    if (await participationGroup.count() < 1) {
      throw providerError("Connpass control unavailable", "CONNPASS_CONTROL_UNAVAILABLE", false);
    }
    confirmControl = page.locator("button#FreeButton");
    const confirmLabel = (await confirmControl.count() === 1 && await confirmControl.isVisible())
      ? String((await confirmControl.innerText()) || "").replace(/\s+/g, " ").trim()
      : "";
    if (confirmLabel !== "申し込みを確定する") {
      throw providerError("Connpass confirm control unavailable", "CONNPASS_CONFIRM_UNAVAILABLE", false);
    }
    // Pick the first free, open, unrestricted tier in document order,
    // preferring in-person over online (see selectParticipationTierIndex).
    // Fails closed with CONNPASS_TIER_UNAVAILABLE if none qualify — nothing
    // below this point is clicked in that case.
    await selectParticipationTier(participationGroup);
  } catch (error) {
    if (error && typeof error.unknownEffect === "boolean") throw error;
    throw providerError("Connpass control unavailable", "CONNPASS_CONTROL_UNAVAILABLE", false);
  }

  // Past this point the confirm control is about to be clicked. Any failure
  // from here on is an unknown external effect — never safe to retry — even
  // if the underlying error would otherwise look like a known/safe one. That
  // includes the navigation back to the event page and the readback below:
  // the registration itself already happened, so neither can be treated as
  // safe-to-retry just because their own error code would normally be.
  try {
    await confirmControl.click();
    await page.waitForTimeout(1_000);
    await page.goto(eventUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
    const after = await readState(page);
    return { status: after.state, effect_started: true };
  } catch {
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
