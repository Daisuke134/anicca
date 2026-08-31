"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createLumaBrowserProvider,
  readSavedLumaPaymentMethodOnPage,
  submitLumaOnPage,
} = require("./luma-browser-provider.js");

function eventJson(offers = { price: 0, priceCurrency: "JPY", availability: "https://schema.org/InStock" }) {
  return [{
    "@type": "Event",
    name: "Tokyo Agent Night",
    startDate: "2026-08-04T19:00:00.000+09:00",
    endDate: "2026-08-04T21:00:00.000+09:00",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    eventStatus: "https://schema.org/EventScheduled",
    location: { "@type": "Place", name: "Tokyo" },
    offers,
  }];
}

function contract() {
  return {
    tenant_id: "dais-local",
    event_ref: "luma-event://event/tokyo-agent-night",
    canonical_url: "https://luma.com/tokyo-agent-night",
  };
}

function fixture(controls, offers) {
  const calls = [];
  const page = {
    async screenshot(options) {
      calls.push(["screenshot", options]);
      return Buffer.from("png-fixture");
    },
  };
  return {
    calls,
    page,
    dailyDriver: {
      async withLumaPage(url, task) {
        calls.push(["withLumaPage", url]);
        return task(page);
      },
    },
    readRawDetail: async (seenPage, url) => {
      assert.equal(seenPage, page);
      return { canonicalUrl: url, jsonLd: eventJson(offers), controls };
    },
    evidenceStore: {
      async record(input) {
        calls.push(["record", input]);
        return {
          external_receipt_ref: "provider-receipt://luma/proof-1",
          artifact_ref: "object://sha256/" + "a".repeat(64),
        };
      },
    },
  };
}

test("inspection separates login, absence, unavailability, and existing registration", async () => {
  const login = fixture(["ログイン", "参加登録"]);
  assert.deepEqual(
    await createLumaBrowserProvider(login).inspectRegistration(contract()),
    { state: "login_required" },
  );

  const available = fixture(["参加登録"]);
  assert.deepEqual(
    await createLumaBrowserProvider(available).inspectRegistration(contract()),
    { state: "absent" },
  );

  const full = fixture(["Sold Out"]);
  assert.deepEqual(
    await createLumaBrowserProvider(full).inspectRegistration(contract()),
    { state: "unavailable", reason: "full" },
  );

  const registered = fixture(["参加予定"]);
  const proof = await createLumaBrowserProvider({
    ...registered,
    now: () => "2026-08-01T10:00:00.000Z",
  }).inspectRegistration(contract());
  assert.deepEqual(proof, {
    state: "registered",
    external_receipt_ref: "provider-receipt://luma/proof-1",
    artifact_ref: "object://sha256/" + "a".repeat(64),
    canonical_url: "https://luma.com/tokyo-agent-night",
  });
  assert.equal(registered.calls.some(([name]) => name === "record"), true);
});

test("Japanese Luma My Ticket readback is an existing registration", async () => {
  const fx = fixture(["マイチケット"]);
  const provider = createLumaBrowserProvider(fx);

  const result = await provider.inspectRegistration(contract());

  assert.equal(result.state, "registered");
  assert.equal(fx.calls.some((call) => call[0] === "record"), true);
});

test("submit rechecks the page, performs one bounded action, and records readback evidence", async () => {
  const fx = fixture(["参加登録"]);
  const provider = createLumaBrowserProvider({
    ...fx,
    now: () => "2026-08-01T10:00:00.000Z",
    submitOnPage: async (page, input) => {
      assert.equal(page, fx.page);
      assert.equal(input.event_ref, contract().event_ref);
      fx.calls.push(["submitOnPage"]);
      return { status: "registered", effect_started: true };
    },
  });

  const proof = await provider.submitRegistration(contract());
  assert.equal(proof.canonical_url, contract().canonical_url);
  assert.deepEqual(fx.calls.map(([name]) => name), [
    "withLumaPage",
    "submitOnPage",
    "screenshot",
    "record",
  ]);
});

test("pre-submit form failure remains known while post-click uncertainty is unknown", async () => {
  const known = fixture(["参加登録"]);
  const providerKnown = createLumaBrowserProvider({
    ...known,
    submitOnPage: async () => {
      const error = new Error("required questions unavailable");
      error.unknownEffect = false;
      throw error;
    },
  });
  await assert.rejects(providerKnown.submitRegistration(contract()), (error) => {
    assert.equal(error.unknownEffect, false);
    return true;
  });

  const unknown = fixture(["参加登録"]);
  const providerUnknown = createLumaBrowserProvider({
    ...unknown,
    submitOnPage: async () => ({ status: "unknown", effect_started: true }),
  });
  await assert.rejects(providerUnknown.submitRegistration(contract()), (error) => {
    assert.equal(error.unknownEffect, true);
    return true;
  });
});

test("submits the live Japanese one-click registration control", async () => {
  const calls = [];
  const control = {
    first() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() { calls.push("click"); },
  };
  const page = {
    getByRole(role, options) {
      assert.equal(role, "button");
      assert.equal(options.exact, true);
      assert.equal(options.name.test("ワンクリックで参加登録"), true);
      assert.equal(options.name.test("参加リクエスト"), true);
      return control;
    },
    async waitForTimeout() {},
    async evaluate(expression) {
      assert.match(String(expression), /承認待ち/);
      return { registered: true };
    },
  };

  assert.deepEqual(await submitLumaOnPage(page), {
    status: "registered",
    effect_started: true,
  });
  assert.deepEqual(calls, ["click"]);
});

test("confirms an approval-request dialog with the same Japanese action", async () => {
  const calls = [];
  const initial = {
    first() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() { calls.push("initial-click"); },
  };
  const confirm = {
    last() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() { calls.push("confirm-click"); },
  };
  const required = { async count() { return 0; } };
  const dialog = {
    last() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async evaluate() { return null; },
    locator() { return required; },
    getByRole(role, options) {
      assert.equal(role, "button");
      assert.equal(options.exact, true);
      assert.equal(options.name.test("参加リクエスト"), true);
      return confirm;
    },
  };
  let reads = 0;
  const page = {
    getByRole(role) {
      assert.equal(role, reads === 0 ? "button" : "dialog");
      return reads === 0 ? initial : dialog;
    },
    async waitForTimeout() {},
    async evaluate() {
      reads += 1;
      return { registered: reads === 2 };
    },
  };

  assert.deepEqual(await submitLumaOnPage(page), {
    status: "registered",
    effect_started: true,
  });
  assert.deepEqual(calls, ["initial-click", "confirm-click"]);
});

test("a required Luma form without dialog role is a known pre-confirmation failure", async () => {
  const control = {
    first() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() {},
  };
  const requiredInput = {
    async count() { return 1; },
    nth() { return { async inputValue() { return ""; } }; },
  };
  const page = {
    getByRole(role) {
      if (role === "button") return control;
      return { last() { return this; }, async count() { return 0; }, async isVisible() { return false; } };
    },
    locator(selector) {
      assert.equal(selector, "input[required], textarea[required], select[required]");
      return requiredInput;
    },
    async waitForTimeout() {},
    async evaluate(task) {
      return String(task).includes("data-luma-form-field")
        ? [{
          label: "Required question *",
          name: "registration_answers.0.value",
          tag: "input",
          type: "text",
          html_required: true,
          app_required: true,
          options: [],
        }]
        : { registered: false };
    },
  };

  await assert.rejects(submitLumaOnPage(page), (error) => {
    assert.equal(error.code, "LUMA_REQUIRED_PROFILE_FIELD_UNAVAILABLE");
    assert.equal(error.unknownEffect, false);
    return true;
  });
});

test("a missing private profile answer stops before the Luma confirm click", async () => {
  const calls = [];
  const initial = {
    first() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() { calls.push("initial-click"); },
  };
  const confirm = {
    last() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() { calls.push("confirm-click"); },
  };
  const dialog = {
    last() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async evaluate() {
      return [{
        label: "Which Instagram handle do you move through the world with? *",
        name: "registration_answers.1.value",
        tag: "input",
        type: "text",
        html_required: true,
        app_required: true,
        options: [],
      }];
    },
    locator() {
      return { async count() { return 0; } };
    },
    getByRole(role) {
      assert.equal(role, "button");
      return confirm;
    },
  };
  let controls = 0;
  const page = {
    getByRole(role) {
      if (role === "button") {
        controls += 1;
        return initial;
      }
      assert.equal(role, "dialog");
      return dialog;
    },
    async waitForTimeout() {},
    async evaluate() { return { registered: false }; },
  };

  await assert.rejects(
    submitLumaOnPage(page, {}, {
      readLumaFormProfile: () => ({ form_answers: {} }),
    }),
    (error) => {
      assert.equal(error.code, "LUMA_REQUIRED_PROFILE_FIELD_UNAVAILABLE");
      assert.equal(error.unknownEffect, false);
      return true;
    },
  );
  assert.equal(controls, 1);
  assert.deepEqual(calls, ["initial-click"]);
});

test("Terra resolves an ordinary novel question once while the parent owns every browser action", async () => {
  const calls = [];
  const initial = {
    first() { return this; }, async count() { return 1; }, async isVisible() { return true; },
    async click() { calls.push("parent-open"); },
  };
  const confirm = {
    last() { return this; }, async count() { return 1; }, async isVisible() { return true; },
    async click() { calls.push("parent-submit"); },
  };
  let filled = "";
  const dialog = {
    last() { return this; }, async count() { return 1; }, async isVisible() { return true; },
    async evaluate() {
      return [{ label: "What brings you here? *", name: "answer.0", tag: "textarea", type: "", html_required: true, app_required: true, options: [] }];
    },
    locator(selector) {
      assert.equal(selector, '[name="answer.0"]');
      return { async count() { return 1; }, async fill(value) { filled = value; calls.push("parent-fill"); }, async inputValue() { return filled; } };
    },
    getByRole() { return confirm; },
  };
  let reads = 0;
  const page = {
    getByRole(role) { return role === "button" ? initial : dialog; },
    async waitForTimeout() {},
    async evaluate() { reads += 1; return { registered: reads > 1 }; },
  };
  let agentCalls = 0;
  const result = await submitLumaOnPage(page, contract(), {
    readLumaFormProfile: () => ({ full_name: "Private Person", form_answers: {} }),
    agenticRegister: async (input) => {
      agentCalls += 1;
      assert.equal(input.schema.kind, "luma_registration_form");
      assert.deepEqual(input.unresolved, [{ key: "answer.0", label: "What brings you here?" }]);
      return { status: "ready", answers: [{ key: "answer.0", control: "textarea", value: "To meet builders." }] };
    },
  });

  assert.equal(agentCalls, 1);
  assert.deepEqual(result, { status: "registered", effect_started: true });
  assert.deepEqual(calls, ["parent-open", "parent-fill", "parent-submit"]);
});

test("provider fills only trusted-profile form answers before locating the confirm control", async () => {
  const calls = [];
  const initial = {
    first() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() { calls.push("initial-click"); },
  };
  const confirm = {
    last() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async click() { calls.push("confirm-click"); },
  };
  const selected = new Set();
  const dialog = {
    last() { return this; },
    async count() { return 1; },
    async isVisible() { return true; },
    async evaluate() {
      return [{
        label: "Which field best describes your work? *",
        name: "registration_answers.0.value",
        tag: "div",
        type: "multi-select",
        html_required: false,
        app_required: true,
        options: ["Technology", "Design"],
      }, {
        label: "I agree to the Code of Conduct and Media Release. *",
        name: "agreement",
        tag: "div",
        type: "checkbox",
        html_required: false,
        app_required: true,
        options: [],
      }];
    },
    locator(selector) {
      assert.equal(selector, '[name="agreement"]');
      return {
        async count() { return 1; },
        async check() { calls.push("check-agreement"); selected.add("agreement"); },
        async isChecked() { return selected.has("agreement"); },
      };
    },
    getByText(option, options) {
      assert.equal(option, "Technology");
      assert.deepEqual(options, { exact: true });
      return {
        async count() { return 1; },
        async click() { calls.push("select-technology"); selected.add("Technology"); },
        async getAttribute(name) {
          assert.equal(name, "aria-pressed");
          return selected.has("Technology") ? "true" : "false";
        },
      };
    },
    getByRole(role) {
      assert.equal(role, "button");
      return confirm;
    },
  };
  let registrationChecks = 0;
  const page = {
    getByRole(role) {
      if (role === "button") return initial;
      assert.equal(role, "dialog");
      return dialog;
    },
    async waitForTimeout() {},
    async evaluate() {
      registrationChecks += 1;
      return { registered: registrationChecks > 1 };
    },
    async screenshot() { return Buffer.from("png-fixture"); },
  };
  const profile = Object.freeze({
    form_answers: { "Which field best describes your work?": ["Technology"] },
    consents: { code_of_conduct_and_media_release: true },
  });
  const provider = createLumaBrowserProvider({
    dailyDriver: { async withLumaPage(_url, task) { return task(page); } },
    evidenceStore: {
      async record() {
        return {
          external_receipt_ref: "provider-receipt://luma/proof-1",
          artifact_ref: "object://sha256/" + "a".repeat(64),
        };
      },
    },
    readRawDetail: async (_page, url) => ({
      canonicalUrl: url,
      jsonLd: eventJson(),
      controls: ["参加登録"],
    }),
    readLumaFormProfile(...args) {
      assert.deepEqual(args, []);
      calls.push("profile-read");
      return profile;
    },
  });

  const proof = await provider.submitRegistration(contract());

  assert.equal(proof.state, "registered");
  assert.deepEqual(calls, [
    "initial-click",
    "profile-read",
    "select-technology",
    "check-agreement",
    "confirm-click",
  ]);
});

test("paid registration cannot click without a matching verified spend authorization", async () => {
  const paidOffer = { price: 2500, priceCurrency: "JPY", availability: "https://schema.org/InStock" };
  const blocked = fixture(["参加登録"], paidOffer);
  let blockedSubmits = 0;
  const blockedProvider = createLumaBrowserProvider({
    ...blocked,
    submitOnPage: async () => { blockedSubmits += 1; },
  });
  await assert.rejects(blockedProvider.submitRegistration(contract()), (error) => {
    assert.equal(error.code, "LUMA_SPEND_AUTHORIZATION_UNAVAILABLE");
    assert.equal(error.unknownEffect, false);
    return true;
  });
  assert.equal(blockedSubmits, 0);

  const allowed = fixture(["参加登録"], paidOffer);
  const decision = Object.freeze({ opaque: "verified-by-policy-module" });
  let authorizedInput;
  const allowedProvider = createLumaBrowserProvider({
    ...allowed,
    authorizeSpendEffect(input) { authorizedInput = input; return { mode: "saved" }; },
    submitOnPage: async () => ({ status: "registered", effect_started: true }),
  });
  await allowedProvider.submitRegistration(contract(), decision);
  assert.equal(authorizedInput.decision, decision);
  assert.equal(authorizedInput.eventDetail.ticket_price_minor, 2500);
  assert.equal(authorizedInput.eventDetail.ticket_currency, "JPY");
});

test("saved payment inspection returns only a browser-side hash", async () => {
  const binding = "sha256:" + "b".repeat(64);
  const page = {
    async evaluate(task) {
      assert.equal(typeof task, "function");
      return { status: "saved", provider_binding: binding };
    },
  };
  assert.deepEqual(await readSavedLumaPaymentMethodOnPage(page), {
    status: "saved", provider_binding: binding,
  });
  await assert.rejects(readSavedLumaPaymentMethodOnPage({
    async evaluate() { return { status: "saved", provider_binding: "card-number" }; },
  }), (error) => {
    assert.equal(error.code, "LUMA_SAVED_PAYMENT_UNAVAILABLE");
    assert.equal(error.unknownEffect, false);
    return true;
  });

  const fx = fixture(["参加登録"]);
  let seenUrl;
  const provider = createLumaBrowserProvider({
    ...fx,
    dailyDriver: {
      async withLumaPage(url, task) {
        seenUrl = url;
        return task(page);
      },
    },
  });
  assert.deepEqual(await provider.inspectSavedPaymentMethod(), {
    status: "saved", provider_binding: binding,
  });
  assert.equal(seenUrl, "https://luma.com/settings/payment");
});
