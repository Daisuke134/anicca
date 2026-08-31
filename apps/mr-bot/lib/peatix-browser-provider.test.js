"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { readPeatixRegistrationStateOnPage, submitPeatixOnPage } = require("./peatix-browser-provider.js");

const candidate = (extra = {}) => ({ provider: "peatix", event_ref: "peatix-event://event/5075819", canonical_url: "https://peatix.com/event/5075819", ticket_id: "6536845", registration_status: "available", ticket_price_status: "free", ticket_price_minor: 0, ...extra });
const profile = (extra = {}) => ({ name: "Dais Example", email: "dais@example.test", family_name_kana: "サクラ", given_name_kana: "テスト", accept_organizer_privacy: true, ...extra });

function fixture(options = {}) {
  let state = options.initial || "tickets"; const calls = []; const checked = new Set(); let finals = 0; let canonicalVisits = 0;
  const fields = options.fields || [
    { selector: "#name", kind: "name", visible: true, checked: false },
    { selector: "#email", kind: "email", visible: true, checked: false },
    { selector: "#privacy", kind: "privacy", visible: true, checked: false },
  ];
  const familySelector = '#confirm-form [name="lastname_edit"]'; const givenSelector = '#confirm-form [name="firstname_edit"]';
  const confirmControls = options.confirmControls || { [familySelector]: { count: 1, visible: true }, [givenSelector]: { count: 1, visible: true } };
  const formSelectors = new Set(["#name", "#email", "#privacy", "#form-submit-button", ...(options.formSelectors || [])]);
  const href = () => state === "tickets" ? "https://peatix.com/sales/event/5075819/tickets" : state === "billing" ? (options.billingUrl || "https://peatix.com/sales/event/5075819/billing") : state === "form" ? `https://peatix.com/sales/event/${options.formEvent || "5075819"}/form` : state === "confirm" ? (options.nextConfirmUrl || options.confirmUrl || `https://peatix.com/sales/event/${options.confirmEvent || "5075819"}/confirm`) : state === "pending-confirm" ? (options.pendingConfirmedUrl || "https://peatix.com/sales/event/5075819/confirm") : state === "confirmed" ? (options.confirmedUrl || "https://peatix.com/sales/event/5075819/confirmed") : state === "complete" ? "https://peatix.com/sales/event/5075819/complete" : state === "ambiguous" ? "https://peatix.com/sales/event/5075819/unknown" : state === "auth" ? "https://peatix.com/login" : state === "canonical" ? (options.canonicalUrl || "https://peatix.com/event/5075819") : state === "canonical-registered" ? (options.canonicalUrl || "https://peatix.com/event/5075819") : state === "ticket-registered" || state === "ticket-unproven" ? "https://peatix.com/event/5075819/ticket" : "https://peatix.com/event/9999999";
  const count = (s) => { if (state === "form" && /#[^\\[]*[\[\]]/.test(s)) throw new Error("invalid selector"); if (state === "confirm" && Object.hasOwn(confirmControls, s)) return confirmControls[s].count; return state === "tickets" && s === "input[name=number_of_tickets_6536845]" ? 1 : state === "tickets" && s === "#next-button" ? 1 : state === "form" && formSelectors.has(s) ? 1 : state === "confirm" && s === "#confirm-button" ? 1 : 0; };
  const navigate = (next) => options.asyncNavigation ? setTimeout(() => { state = next; }, 0) : (state = next);
  const locator = (selector) => {
    const kana = state === "confirm" && Object.hasOwn(confirmControls, selector) ? confirmControls[selector] : {};
    const result = {
      count: async () => count(selector),
      isVisible: async () => state === "confirm" && Object.hasOwn(confirmControls, selector) ? count(selector) === 1 && kana.visible === true : count(selector) === 1,
      isEnabled: async () => kana.disabled !== true,
      isEditable: async () => {
        if (kana.isEditableThrows === true) throw new Error("editable probe failed");
        if (Object.hasOwn(kana, "editable")) return kana.editable;
        return true;
      },
      fill: async (value) => calls.push(["fill", selector, value]),
      check: async () => { calls.push(["check", selector]); checked.add(selector); },
      isChecked: async () => checked.has(selector),
      click: async () => {
        calls.push(["click", selector]);
        if (selector === "#next-button") {
          if (options.nextPath === "billing") state = "billing";
          else if (options.nextPath === "billing-confirm") {
            state = "billing";
            setTimeout(() => { state = "confirm"; }, Number(options.nextDelayMs) || 0);
          } else navigate("form");
        }
        else if (selector === "#form-submit-button") navigate("confirm");
        else if (selector === "#confirm-button") {
          finals += 1;
          if (options.settlement === false) state = options.complete === false ? "ambiguous" : "complete";
          else if (options.settlement === "missing") state = "pending-confirm";
          else {
            state = "pending-confirm";
            setTimeout(() => { state = "confirmed"; }, Number(options.confirmedDelayMs) || 0);
          }
        }
      },
    };
    if (kana.isEditableMissing === true) delete result.isEditable;
    return result;
  };
  const page = {
    url: href,
    async goto(url) {
      calls.push(["goto", url]);
      state = /\/tickets$/.test(url) ? "tickets" : /\/form$/.test(url) ? "form" : /^https:\/\/peatix\.com\/event\/5075819$/.test(url) ? ((options.canonicalUnavailable || (options.canonicalUnavailableOnce && canonicalVisits++ === 0)) ? "canonical" : "canonical-registered") : /^https:\/\/peatix\.com\/event\/5075819\/ticket$/.test(url) ? (options.ticketRegistered ? "ticket-registered" : "ticket-unproven") : "confirm";
    },
    async waitForURL(predicate, waitOptions = {}) {
      calls.push(["wait-for-url", waitOptions]); const deadline = Date.now() + Math.min(Number(waitOptions.timeout) || 30_000, 50);
      while (Date.now() < deadline) { if (predicate(new URL(href()))) return; await new Promise((resolve) => setTimeout(resolve, 1)); }
      throw new Error("navigation timeout");
    },
    locator,
    async evaluate(_fn, payload) {
      assert.ok(payload && payload.mode);
      if (payload.mode === "form" && (options.domFields || options.domPrivacy)) {
        const previousDocument = global.document; const previousCSS = global.CSS;
        const nodes = (options.domFields || []).map((field) => ({ id: field.id || "", name: field.name || "", type: field.type || "text", hidden: false, checked: false, labels: field.label ? [{ textContent: field.label }] : [], getAttribute: (name) => name === "aria-label" ? field.ariaLabel || null : name === "data-label" ? field.dataLabel || null : name === "name" ? field.name || null : null }));
        const privacyDescriptions = options.domPrivacyGroups || (options.domPrivacy ? [options.domPrivacy] : []);
        const allPrivacyNodes = [];
        const privacyFields = privacyDescriptions.map((privacy) => {
          let field;
          const radioNodes = (privacy.options || []).map((option, index) => ({
            id: option.id || `privacy-${index}`,
            name: option.name || privacy.name || "organizer_privacy",
            type: "radio", hidden: false, disabled: !!option.disabled, checked: !!option.checked,
            labels: option.label ? [{ textContent: option.label }] : [],
            getAttribute: (name) => name === "aria-label" ? option.ariaLabel || null : name === "name" ? option.name || privacy.name || "organizer_privacy" : null,
            classList: { contains: () => false },
            closest: (selector) => selector === "dl.field.required" ? field : null,
          }));
          field = { className: "field required", querySelector: (selector) => selector.includes("dt") ? { textContent: privacy.prompt || "" } : null, querySelectorAll: (selector) => /input\[type=["']?radio/.test(selector) ? radioNodes : [] };
          allPrivacyNodes.push(...radioNodes);
          return field;
        });
        global.document = { querySelectorAll: (selector) => selector === "dl.field.required" ? privacyFields : selector.includes("input[type") ? allPrivacyNodes : nodes, querySelector: () => options.formSubmit === false ? null : {} }; global.CSS = { escape: (value) => String(value).replace(/[^A-Za-z0-9_-]/g, "\\$&") };
        try { return _fn(); } finally { global.document = previousDocument; global.CSS = previousCSS; }
      }
      if (payload.mode === "form") return { fields };
      if (payload.mode === "confirm_validation") { if (options.confirmValidationThrows) throw new Error("validator failed"); return options.confirmValidationMissing ? {} : { valid: options.confirmValid !== false }; }
      if (payload.mode === "confirm") return { text: options.confirmText || "チケットを申し込む", visible: true };
      if (state === "confirmed" || state === "pending-confirm") return { href: href(), markers: [], checkout: false };
      if (state === "complete") return { href: href(), markers: options.marker === false ? [] : [{ event_id: "5075819", ticket_id: "6536845" }], checkout: false };
      if (state === "canonical-registered") return { href: href(), markers: options.complete === false ? [] : [{ event_id: "5075819", ticket_id: "6536845" }], checkout: false };
      if (state === "ticket-registered") return { href: href(), markers: [], checkout: false, ticket_shell: false, swipe_shell: true };
      if (state === "ticket-unproven") return { href: href(), markers: [], checkout: false, ticket_shell: false, swipe_shell: false };
      if (state === "auth") return { href: href(), auth: true, markers: [], checkout: false };
      if (state === "cross") return { href: "https://peatix.com/sales/event/9999999/complete", markers: [{ event_id: "9999999", ticket_id: "6536845" }], checkout: false };
      if (state === "canonical" && options.markerEvent) return { href: href(), markers: [{ event_id: options.markerEvent, ticket_id: "6536845" }], checkout: false };
      return { href: href(), markers: [], checkout: ["tickets", "form", "confirm"].includes(state) };
    },
  };
  return { page, calls, finalCount: () => finals };
}

function readbackFixture(options = {}) {
  const href = options.href || "https://peatix.com/event/5075819";
  const url = new URL(href); const calls = [];
  const node = (item = {}) => ({ hidden: item.hidden === true, isConnected: item.detached !== true, style: item.style || {}, ownerDocument: { defaultView: { getComputedStyle: () => item.computedStyle || {} } }, getAttribute: (name) => item.attributes && item.attributes[name] || null, getBoundingClientRect: () => item.rect || { width: item.visible === false ? 0 : 120, height: item.visible === false ? 0 : 32 } });
  const shell = options.ticketShell || options.swipeShell || {}; const swipe = options.swipeShell || {}; const links = (options.ticketLinks || []).map((item) => node({ ...item, attributes: { href: item.href || `/event/${item.eventId || "5075819"}/ticket` } }));
  const list = (count, item) => Array.from({ length: count || 0 }, () => node(item));
  const document = {
    querySelectorAll(selector) {
      if (selector.includes("data-registration-status")) return options.markers || [];
      if (selector === "body.webticket") return list(shell.bodyCount, shell.body);
      if (selector === "section.ticket") return list(shell.sectionCount, shell.section);
      if (selector === "#qr-code img.js-qrcode-image") return list(shell.qrCount, shell.qr);
      if (selector === ".ticket_cover") return list(swipe.coverCount, swipe.cover);
      if (selector === ".ticket_event") return list(swipe.eventCount, swipe.event);
      if (selector === ".ticket_event-name") return list(swipe.eventNameCount, swipe.eventName);
      if (selector === ".ticket_summary") return list(swipe.summaryCount, swipe.summary);
      if (selector === "a[href]") return links;
      return [];
    },
    querySelector(selector) { return options.checkoutControls ? node() : null; },
  };
  const page = {
    url() { return href; },
    async goto(next) { calls.push(["goto", next]); throw new Error("submit must not run"); },
    async evaluate(fn, payload) {
      const previousDocument = global.document; const previousLocation = global.location;
      global.document = document; global.location = { href: url.href, pathname: url.pathname };
      try { return fn(payload); } finally { global.document = previousDocument; global.location = previousLocation; }
    },
  };
  return { page, calls };
}

test("invalid input fails closed and registered readback is an idempotent no-op", async () => {
  for (const [c, p] of [[candidate({ provider: "luma" }), profile()], [candidate({ ticket_price_status: "paid", ticket_price_minor: 100 }), profile()], [candidate(), profile({ accept_organizer_privacy: false })], [candidate(), profile({ accept_organizer_privacy: undefined })], [{ id: "5075819", ticket: "6536845" }, profile()], [candidate({ canonical_url: "https://peatix.com:444/event/5075819" }), profile()]]) {
    const f = fixture(); assert.deepEqual(await submitPeatixOnPage(f.page, c, p), { status: "unavailable", reason: "invalid_input" }); assert.equal(f.calls.some((x) => x[0] === "goto"), false); assert.equal(f.finalCount(), 0);
  }
  const f = fixture({ initial: "complete" }); assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" }); assert.equal(f.calls.some((x) => x[0] === "goto"), false); assert.equal(f.finalCount(), 0);
  const canonical = fixture({ initial: "canonical", canonicalUnavailableOnce: true }); assert.deepEqual(await submitPeatixOnPage(canonical.page, candidate(), profile()), { status: "registered" });
  const wrong = fixture({ initial: "wrong" }); assert.equal((await submitPeatixOnPage(wrong.page, candidate(), profile())).status, "unavailable"); assert.equal(wrong.calls.some((x) => x[0] === "goto"), false);
  const wrongMarker = fixture({ initial: "canonical", markerEvent: "9999999" }); assert.equal((await submitPeatixOnPage(wrongMarker.page, candidate(), profile())).status, "unavailable"); assert.equal(wrongMarker.calls.some((x) => x[0] === "goto"), false);
  const portCanonical = fixture({ initial: "canonical", canonicalUrl: "https://peatix.com:444/event/5075819" }); assert.equal((await submitPeatixOnPage(portCanonical.page, candidate(), profile())).status, "unavailable"); assert.equal(portCanonical.calls.some((x) => x[0] === "goto"), false);
});

test("measured ticket/form/confirm flow fills exact fields and clicks final boundary once", async () => {
  const f = fixture(); const p = profile(); const result = await submitPeatixOnPage(f.page, candidate(), p);
  assert.deepEqual(result, { status: "registered" }); assert.equal(f.finalCount(), 1);
  assert.deepEqual(f.calls.filter((x) => ["fill", "check", "click"].includes(x[0])), [["fill", "input[name=number_of_tickets_6536845]", "1"], ["click", "#next-button"], ["fill", "#name", p.name], ["fill", "#email", p.email], ["check", "#privacy"], ["click", "#form-submit-button"], ["fill", '#confirm-form [name="lastname_edit"]', p.family_name_kana], ["fill", '#confirm-form [name="firstname_edit"]', p.given_name_kana], ["click", "#confirm-button"]]);
  assert.equal(JSON.stringify(result).includes(p.email), false);
  assert.equal(JSON.stringify(result).includes(p.family_name_kana), false); assert.equal(JSON.stringify(result).includes("family_name_kana"), false);
});

test("hidden exact Kana pair skips fill and reaches jQuery validation and final readback", async () => {
  const family = '#confirm-form [name="lastname_edit"]'; const given = '#confirm-form [name="firstname_edit"]';
  const f = fixture({ confirmControls: { [family]: { count: 1, visible: false }, [given]: { count: 1, visible: false } } });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" });
  assert.equal(f.calls.filter(([name, selector]) => name === "fill" && [family, given].includes(selector)).length, 0);
  assert.equal(f.calls.filter(([name, selector]) => name === "click" && selector === "#confirm-button").length, 1);
});

test("hidden exact Kana pair with invalid jQuery validation fails before final click", async () => {
  const family = '#confirm-form [name="lastname_edit"]'; const given = '#confirm-form [name="firstname_edit"]';
  const f = fixture({ confirmValid: false, confirmControls: { [family]: { count: 1, visible: false }, [given]: { count: 1, visible: false } } });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "unavailable", reason: "confirm_validation_failed" });
  assert.equal(f.finalCount(), 0);
});

test("delayed exact confirmed settlement navigates canonical and reads registered once", async () => {
  const f = fixture({ confirmedDelayMs: 8 });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" });
  assert.equal(f.finalCount(), 1);
  assert.deepEqual(f.calls.filter(([name]) => name === "goto"), [
    ["goto", "https://peatix.com/sales/event/5075819/tickets"],
    ["goto", "https://peatix.com/event/5075819"],
  ]);
  assert.equal(f.calls.filter(([name, selector]) => name === "click" && selector === "#confirm-button").length, 1);
});

test("Peatix confirmed settlement rejects malformed or missing same-event URLs without retry", async () => {
  for (const confirmedUrl of [
    "https://peatix.com/sales/event/9999999/confirmed",
    "https://peatix.com/login",
    "https://peatix.com/sales/event/5075819/confirmed?x=1",
    "https://peatix.com/sales/event/5075819/confirmed#x",
    "https://user:pass@peatix.com/sales/event/5075819/confirmed",
    "https://peatix.com:444/sales/event/5075819/confirmed",
    "https://peatix.com/event/5075819",
  ]) {
    const f = fixture({ confirmedUrl });
    assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "unavailable", reason: "readback_unavailable" }, confirmedUrl);
    assert.equal(f.finalCount(), 1, confirmedUrl);
    assert.equal(f.calls.filter(([name]) => name === "goto").length, 1, confirmedUrl);
  }
  const missing = fixture({ settlement: "missing" });
  assert.deepEqual(await submitPeatixOnPage(missing.page, candidate(), profile()), { status: "unavailable", reason: "readback_unavailable" });
  assert.equal(missing.finalCount(), 1);
  assert.equal(missing.calls.filter(([name]) => name === "goto").length, 1);
  const confirmedOnly = fixture({ complete: false });
  assert.deepEqual(await submitPeatixOnPage(confirmedOnly.page, candidate(), profile()), { status: "unavailable", reason: "readback_unavailable" });
  assert.equal(confirmedOnly.finalCount(), 1);
  assert.deepEqual(confirmedOnly.calls.filter(([name]) => name === "goto"), [
    ["goto", "https://peatix.com/sales/event/5075819/tickets"],
    ["goto", "https://peatix.com/event/5075819"],
    ["goto", "https://peatix.com/event/5075819/ticket"],
    ["goto", "https://peatix.com/event/5075819"],
  ]);
});

test("billing transient then same-event confirm skips attendee form and settles through canonical readback", async () => {
  const f = fixture({ nextPath: "billing-confirm", nextDelayMs: 8 });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" });
  assert.equal(f.finalCount(), 1);
  assert.equal(f.calls.some(([name, selector]) => name === "click" && selector === "#form-submit-button"), false);
  assert.equal(f.calls.some(([name, selector]) => name === "fill" && ["#name", "#email", "#privacy"].includes(selector)), false);
  assert.equal(f.calls.filter(([name, selector]) => name === "click" && selector === "#confirm-button").length, 1);
  assert.deepEqual(f.calls.filter(([name]) => name === "goto"), [
    ["goto", "https://peatix.com/sales/event/5075819/tickets"],
    ["goto", "https://peatix.com/event/5075819"],
  ]);
});

test("billing停留 and malformed direct confirm transitions fail before final confirmation", async () => {
  for (const options of [
    { nextPath: "billing" },
    { nextPath: "billing-confirm", nextDelayMs: 8, nextConfirmUrl: "https://peatix.com/sales/event/9999999/confirm" },
    { nextPath: "billing-confirm", nextDelayMs: 8, nextConfirmUrl: "https://peatix.com/sales/event/5075819/confirm?x=1" },
    { nextPath: "billing-confirm", nextDelayMs: 8, nextConfirmUrl: "https://peatix.com/sales/event/5075819/confirm#x" },
    { nextPath: "billing-confirm", nextDelayMs: 8, nextConfirmUrl: "https://user:pass@peatix.com/sales/event/5075819/confirm" },
    { nextPath: "billing-confirm", nextDelayMs: 8, nextConfirmUrl: "https://peatix.com:444/sales/event/5075819/confirm" },
    { nextPath: "billing-confirm", nextDelayMs: 8, nextConfirmUrl: "https://peatix.com/login" },
    { nextPath: "billing-confirm", nextDelayMs: 8, nextConfirmUrl: "https://peatix.com/sales/event/5075819/other" },
  ]) {
    const f = fixture(options);
    assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "unavailable", reason: "form_navigation_failed" });
    assert.equal(f.finalCount(), 0);
    assert.equal(f.calls.some(([name, selector]) => name === "click" && ["#form-submit-button", "#confirm-button"].includes(selector)), false);
  }
});

test("a login-wall header at the stalled next-button step is reported as a session problem, not a generic navigation failure", async () => {
  const f = fixture({ nextPath: "billing" });
  const originalEvaluate = f.page.evaluate.bind(f.page);
  f.page.evaluate = async (fn, payload) => (
    payload && payload.mode === "session_check"
      ? { login: true, signup: true }
      : originalEvaluate(fn, payload)
  );
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "unavailable", reason: "session_expired" });
  assert.equal(f.finalCount(), 0);
  assert.equal(f.calls.some(([name, selector]) => name === "click" && ["#form-submit-button", "#confirm-button"].includes(selector)), false);
});

test("a login control alone, without the signup control, keeps the ordinary navigation-failed reason", async () => {
  const f = fixture({ nextPath: "billing" });
  const originalEvaluate = f.page.evaluate.bind(f.page);
  f.page.evaluate = async (fn, payload) => (
    payload && payload.mode === "session_check"
      ? { login: true, signup: false }
      : originalEvaluate(fn, payload)
  );
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "unavailable", reason: "form_navigation_failed" });
});

test("visible Kana controls require enabled, editable, boolean editable probes before final click", async () => {
  const family = '#confirm-form [name="lastname_edit"]'; const given = '#confirm-form [name="firstname_edit"]';
  for (const invalid of [
    { [family]: { count: 1, visible: true, editable: false }, [given]: { count: 1, visible: true } },
    { [family]: { count: 1, visible: true, editable: "true" }, [given]: { count: 1, visible: true } },
    { [family]: { count: 1, visible: true, isEditableMissing: true }, [given]: { count: 1, visible: true } },
    { [family]: { count: 1, visible: true, isEditableThrows: true }, [given]: { count: 1, visible: true } },
  ]) {
    const f = fixture({ confirmControls: invalid });
    assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "unavailable", reason: "kana_control_unavailable" });
    assert.equal(f.calls.some(([name, selector]) => name === "fill" && [family, given].includes(selector)), false);
    assert.equal(f.finalCount(), 0);
  }
});

test("asynchronous ticket and form navigation waits for exact same-event URLs", async () => {
  const f = fixture({ asyncNavigation: true });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" });
  assert.deepEqual(f.calls.filter(([name]) => name === "wait-for-url").map(([, options]) => options), [
    { waitUntil: "domcontentloaded", timeout: 30_000 }, { waitUntil: "domcontentloaded", timeout: 30_000 }, { waitUntil: "domcontentloaded", timeout: 30_000 },
  ]);
});

test("asynchronous wrong-event navigation stops before form inspection and final click", async () => {
  const f = fixture({ asyncNavigation: true, formEvent: "9999999" });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "unavailable", reason: "form_navigation_failed" });
  assert.equal(f.calls.filter(([name, selector]) => name === "click" && selector === "#form-submit-button").length, 0);
  assert.equal(f.finalCount(), 0);
});

test("missing navigation wait fails before the next click", async () => {
  const f = fixture(); delete f.page.waitForURL;
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "unavailable", reason: "form_navigation_failed" });
  assert.equal(f.calls.filter(([name, selector]) => name === "click" && selector === "#next-button").length, 0);
});

test("Kana profile and measured confirm controls fail closed before final click", async () => {
  const family = '#confirm-form [name="lastname_edit"]'; const given = '#confirm-form [name="firstname_edit"]';
  for (const invalid of [{ family_name_kana: "" }, { given_name_kana: "桜" }, { family_name_kana: "sakura" }, { family_name_kana: "サ".repeat(101) }]) { const f = fixture(); assert.notEqual((await submitPeatixOnPage(f.page, candidate(), profile(invalid))).status, "registered"); assert.equal(f.finalCount(), 0); }
  for (const confirmControls of [{ [family]: { count: 0, visible: true }, [given]: { count: 1, visible: true } }, { [family]: { count: 2, visible: true }, [given]: { count: 1, visible: true } }, { [family]: { count: 1, visible: false }, [given]: { count: 1, visible: true } }, { [family]: { count: 1, visible: true, disabled: true }, [given]: { count: 1, visible: true } }, { [family]: { count: 1, visible: true, editable: false }, [given]: { count: 1, visible: true } }]) { const f = fixture({ confirmControls }); assert.equal((await submitPeatixOnPage(f.page, candidate(), profile())).status, "unavailable"); assert.equal(f.finalCount(), 0); }
  for (const options of [{ confirmValid: false }, { confirmValidationMissing: true }, { confirmValidationThrows: true }]) { const f = fixture(options); assert.equal((await submitPeatixOnPage(f.page, candidate(), profile())).status, "unavailable"); assert.equal(f.finalCount(), 0); }
});

test("special-character DOM ids use escaped selectors before final confirmation", async () => {
  const f = fixture({ domFields: [{ id: "name[0]", name: "attendee_name", label: "name", type: "text" }, { id: "email[0]", name: "attendee_email", label: "email", type: "email" }], formSelectors: ["#name\\[0\\]", "#email\\[0\\]"] });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" }); assert.equal(f.finalCount(), 1);
});

test("measured organizer privacy radio is classified and checked before form submit", async () => {
  const f = fixture({
    domFields: [{ id: "name", name: "attendee_name", label: "name", type: "text" }, { id: "email", name: "attendee_email", label: "email", type: "email" }],
    domPrivacy: { prompt: "enXrossのプライバシーポリシーを読んだ・確認した", name: "organizer_privacy", options: [{ id: "organizer-privacy", label: "確認し同意する。" }] },
    formSelectors: ["#organizer-privacy"],
  });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" });
  assert.deepEqual(f.calls.filter((x) => ["fill", "check", "click"].includes(x[0])), [["fill", "input[name=number_of_tickets_6536845]", "1"], ["click", "#next-button"], ["fill", "#name", "Dais Example"], ["fill", "#email", "dais@example.test"], ["check", "#organizer-privacy"], ["click", "#form-submit-button"], ["fill", '#confirm-form [name="lastname_edit"]', "サクラ"], ["fill", '#confirm-form [name="firstname_edit"]', "テスト"], ["click", "#confirm-button"]]);
});

test("non-organizer, ambiguous, and malformed radio groups fail closed", async () => {
  const fields = [{ id: "name", name: "attendee_name", label: "name", type: "text" }, { id: "email", name: "attendee_email", label: "email", type: "email" }];
  for (const domPrivacy of [
    { prompt: "Peatixの利用規約を確認し同意する", options: [{ label: "確認し同意する。" }] },
    { prompt: "マーケティング配信に同意する", options: [{ label: "同意する" }] },
    { prompt: "個人情報を第三者と共有する", options: [{ label: "同意する" }] },
    { prompt: "イベント参加方法", options: [{ label: "オンライン" }] },
    { prompt: "enXrossのプライバシーを確認した", options: [{ label: "確認し同意する。" }] },
    { prompt: "enXrossのプライバシーポリシーを読んだ・確認した、マーケティング配信にも同意する", options: [{ label: "確認し同意する。" }] },
    { prompt: "enXrossのプライバシーポリシーを読んだ・確認した、第三者へのデータ共有に同意する", options: [{ label: "確認し同意する。" }] },
    { prompt: "enXrossのプライバシーポリシーを読んだ・確認した、イベント写真撮影にも同意する", options: [{ label: "確認し同意する。" }] },
    { prompt: "enXrossのプライバシーポリシーを読んだ・確認した", options: [] },
    { prompt: "enXrossのプライバシーポリシーを読んだ・確認した", options: [{ label: "確認し同意する。" }, { label: "確認しない" }] },
    { prompt: "enXrossのプライバシーポリシーを読んだ・確認した", options: [{ label: "同意しない" }] },
    { prompt: "enXrossのプライバシーポリシーを読んだ・確認した", options: [{ label: "確認し同意しない。" }] },
    { prompt: "Acme's privacy policy read and confirmed", options: [{ label: "I agree" }] },
    { prompt: "enXrossのプライバシーポリシーを読んだ・確認した", options: [{ label: "I do not agree" }] },
  ]) {
    const f = fixture({ domFields: fields, domPrivacy });
    assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "needs_fallback", reason: "unknown_required_field" }); assert.equal(f.calls.some((x) => x[0] === "check"), false); assert.equal(f.finalCount(), 0);
  }
  const duplicate = fixture({ domFields: fields, domPrivacyGroups: [{ prompt: "enXrossのプライバシーポリシーを読んだ・確認した", options: [{ label: "確認し同意する。" }] }, { prompt: "別主催者のプライバシーポリシーを読んだ・確認した", options: [{ label: "確認し同意する。" }] }] });
  assert.deepEqual(await submitPeatixOnPage(duplicate.page, candidate(), profile()), { status: "unavailable", reason: "privacy_control_unavailable" }); assert.equal(duplicate.finalCount(), 0);
});

test("optional privacy control still reaches final confirmation and duplicates fail closed", async () => {
  const optional = fixture({ fields: [{ selector: "#name", kind: "name", visible: true }, { selector: "#email", kind: "email", visible: true }] });
  assert.deepEqual(await submitPeatixOnPage(optional.page, candidate(), profile()), { status: "registered" }); assert.equal(optional.finalCount(), 1); assert.equal(optional.calls.some((x) => x[0] === "check"), false);
  const duplicate = fixture({ fields: [{ selector: "#name", kind: "name", visible: true }, { selector: "#email", kind: "email", visible: true }, { selector: "#privacy-a", kind: "privacy", visible: true }, { selector: "#privacy-b", kind: "privacy", visible: true }] });
  assert.deepEqual(await submitPeatixOnPage(duplicate.page, candidate(), profile()), { status: "unavailable", reason: "privacy_control_unavailable" }); assert.equal(duplicate.finalCount(), 0);
});

test("unknown required field stops before final application click", async () => {
  const f = fixture({ fields: [{ selector: "#name", kind: "name", visible: true }, { selector: "#phone", kind: "unknown", visible: true }] });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "needs_fallback", reason: "unknown_required_field" }); assert.equal(f.finalCount(), 0);
});

test("wrong ticket, event, and final button identity stay pre-submit", async () => {
  const ticket = fixture(); assert.deepEqual(await submitPeatixOnPage(ticket.page, candidate({ ticket_id: "9999999" }), profile()), { status: "unavailable", reason: "ticket_control_unavailable" }); assert.equal(ticket.finalCount(), 0);
  const event = fixture({ confirmEvent: "9999999" }); assert.deepEqual(await submitPeatixOnPage(event.page, candidate(), profile()), { status: "unavailable", reason: "confirm_event_mismatch" }); assert.equal(event.finalCount(), 0);
  const text = fixture({ confirmText: "戻る" }); assert.deepEqual(await submitPeatixOnPage(text.page, candidate(), profile()), { status: "unavailable", reason: "confirm_control_unavailable" }); assert.equal(text.finalCount(), 0);
  for (const confirmUrl of ["http://peatix.com/sales/event/5075819/confirm", "https://evil.example/sales/event/5075819/confirm", "https://peatix.com:444/sales/event/5075819/confirm", "https://peatix.com/sales/event/5075819/confirm?x=1", "https://peatix.com/sales/event/5075819/confirm#x"]) { const f = fixture({ confirmUrl }); assert.equal((await submitPeatixOnPage(f.page, candidate(), profile())).status, "unavailable"); assert.equal(f.finalCount(), 0); }
});

test("ambiguous post-click and cross-event/auth readbacks never report success", async () => {
  const ambiguous = fixture({ complete: false }); assert.deepEqual(await submitPeatixOnPage(ambiguous.page, candidate(), profile()), { status: "unavailable", reason: "readback_unavailable" }); assert.equal(ambiguous.finalCount(), 1);
  for (const [initial, expected] of [["tickets", { status: "absent" }], ["cross", { status: "unavailable", reason: "readback_unavailable" }], ["auth", { status: "unavailable", reason: "readback_unavailable" }]]) assert.deepEqual(await readPeatixRegistrationStateOnPage(fixture({ initial }).page, candidate()), expected);
});

test("measured Peatix ticket shell and canonical ticket link prove same-event registration", async () => {
  const ticket = readbackFixture({ href: "https://peatix.com/event/5075819/ticket", ticketShell: { bodyCount: 1, sectionCount: 1, qrCount: 1 } });
  const ticketResult = await readPeatixRegistrationStateOnPage(ticket.page, candidate());
  assert.deepEqual(ticketResult, { status: "registered" });
  assert.doesNotMatch(JSON.stringify(ticketResult), /6536845|webticket|qr-code/i);
  const canonical = readbackFixture({ ticketLinks: [{ eventId: "5075819" }] });
  assert.deepEqual(await readPeatixRegistrationStateOnPage(canonical.page, candidate()), { status: "registered" });
});

test("measured Peatix swipe ticket shell proves same-event registration without private ticket reads", async () => {
  const ticket = readbackFixture({
    href: "https://peatix.com/event/5075819/ticket",
    swipeShell: { bodyCount: 1, sectionCount: 1, coverCount: 1, eventCount: 1, eventNameCount: 1, summaryCount: 1 },
  });
  const result = await readPeatixRegistrationStateOnPage(ticket.page, candidate());
  assert.deepEqual(result, { status: "registered" });
  assert.doesNotMatch(JSON.stringify(result), /6536845|confirmation|ticket_number|ticket_value|ticket_text/i);
});

test("swipe ticket proof fails closed for malformed URL and missing, duplicate, hidden, or zero-size shell", async () => {
  for (const href of [
    "http://peatix.com/event/5075819/ticket", "https://peatix.com:444/event/5075819/ticket", "https://evil.example/event/5075819/ticket",
    "https://peatix.com/event/9999999/ticket", "https://peatix.com/event/5075819/other", "https://peatix.com/event/5075819/ticket?x=1",
    "https://peatix.com/event/5075819/ticket#x", "https://peatix.com/login",
  ]) {
    const page = readbackFixture({ href, swipeShell: { bodyCount: 1, sectionCount: 1, coverCount: 1, eventCount: 1, eventNameCount: 1, summaryCount: 1 } });
    assert.notEqual((await readPeatixRegistrationStateOnPage(page.page, candidate())).status, "registered", href);
  }
  for (const swipeShell of [
    { bodyCount: 1, sectionCount: 1, coverCount: 0, eventCount: 1, eventNameCount: 1, summaryCount: 1 },
    { bodyCount: 1, sectionCount: 1, coverCount: 2, eventCount: 1, eventNameCount: 1, summaryCount: 1 },
    { bodyCount: 1, sectionCount: 1, coverCount: 1, eventCount: 1, eventNameCount: 1, summaryCount: 1, cover: { visible: false } },
    { bodyCount: 1, sectionCount: 1, coverCount: 1, eventCount: 1, eventNameCount: 1, summaryCount: 1, summary: { rect: { width: 0, height: 0 } } },
  ]) {
    const page = readbackFixture({ href: "https://peatix.com/event/5075819/ticket", swipeShell });
    assert.notEqual((await readPeatixRegistrationStateOnPage(page.page, candidate())).status, "registered");
  }
});

test("canonical unavailable pre-readback recovers a registered swipe ticket without Submit", async () => {
  const f = fixture({ initial: "canonical", canonicalUnavailable: true, ticketRegistered: true });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" });
  assert.equal(f.finalCount(), 0);
  assert.deepEqual(f.calls.filter(([name]) => name === "goto"), [["goto", "https://peatix.com/event/5075819/ticket"]]);
});

test("unproven ticket probe restores canonical before continuing the normal flow", async () => {
  const f = fixture({ initial: "canonical", canonicalUnavailableOnce: true, ticketRegistered: false });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" });
  assert.equal(f.finalCount(), 1);
  assert.deepEqual(f.calls.filter(([name]) => name === "goto").slice(0, 3), [
    ["goto", "https://peatix.com/event/5075819/ticket"],
    ["goto", "https://peatix.com/event/5075819"],
    ["goto", "https://peatix.com/sales/event/5075819/tickets"],
  ]);
});

test("post-confirm canonical unavailable recovers a registered swipe ticket after one final click", async () => {
  const f = fixture({ canonicalUnavailable: true, ticketRegistered: true });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" });
  assert.equal(f.finalCount(), 1);
  assert.equal(f.calls.filter(([name, url]) => name === "goto" && url === "https://peatix.com/event/5075819/ticket").length, 1);
});

test("Peatix ticket readback fails closed for identity, auth, missing, duplicate, hidden, zero-size, competing, and checkout states", async () => {
  const urls = ["http://peatix.com/event/5075819/ticket", "https://peatix.com:444/event/5075819/ticket", "https://evil.example/event/5075819/ticket", "https://peatix.com/event/9999999/ticket", "https://peatix.com/event/5075819/other", "https://peatix.com/event/5075819/ticket?x=1", "https://peatix.com/event/5075819/ticket#x", "https://peatix.com/login"];
  for (const href of urls) {
    const page = readbackFixture({ href, ticketShell: { bodyCount: 1, sectionCount: 1, qrCount: 1 }, ticketLinks: [{ eventId: "5075819" }] });
    assert.notEqual((await readPeatixRegistrationStateOnPage(page.page, candidate())).status, "registered", href);
  }
  for (const shell of [{ bodyCount: 0, sectionCount: 1, qrCount: 1 }, { bodyCount: 2, sectionCount: 1, qrCount: 1 }, { bodyCount: 1, sectionCount: 1, qrCount: 1, qr: { visible: false } }, { bodyCount: 1, sectionCount: 1, qrCount: 1, qr: { rect: { width: 0, height: 0 } } }, { bodyCount: 1, sectionCount: 1, qrCount: 1, qr: { style: { opacity: 0 } } }]) {
    const page = readbackFixture({ href: "https://peatix.com/event/5075819/ticket", ticketShell: shell });
    assert.notEqual((await readPeatixRegistrationStateOnPage(page.page, candidate())).status, "registered");
  }
  for (const ticketLinks of [[{ eventId: "5075819" }, { eventId: "5075819" }], [{ eventId: "9999999" }], [{ eventId: "5075819" }, { eventId: "9999999" }], [{ eventId: "5075819", visible: false }], [{ eventId: "5075819", rect: { width: 0, height: 0 } }]]) {
    const page = readbackFixture({ ticketLinks, checkoutControls: ticketLinks.length === 1 && ticketLinks[0].eventId === "5075819" && !ticketLinks[0].visible });
    assert.notEqual((await readPeatixRegistrationStateOnPage(page.page, candidate())).status, "registered");
  }
  const checkout = readbackFixture({ ticketLinks: [{ eventId: "5075819" }], checkoutControls: true });
  assert.notEqual((await readPeatixRegistrationStateOnPage(checkout.page, candidate())).status, "registered");
});

test("pre-registered Peatix ticket readback is an idempotent direct-submit no-op", async () => {
  const page = readbackFixture({ ticketLinks: [{ eventId: "5075819" }] });
  assert.deepEqual(await submitPeatixOnPage(page.page, candidate(), profile()), { status: "registered" });
  assert.equal(page.calls.filter(([name]) => name === "goto").length, 0);
});

test("malformed Peatix readback markers fail closed without browser actions", async () => {
  for (const markers of ["", {}, null, undefined]) {
    const calls = []; const observed = {
      href: "https://peatix.com/event/5075819/ticket", auth: false, checkout: false,
      ticket_shell: true, canonical_ticket_link_count: 0, canonical_ticket_link_total: 0,
      competing_ticket_link_count: 0,
    };
    if (markers !== undefined) observed.markers = markers;
    const page = {
      url: () => observed.href,
      async evaluate() { return observed; },
      async goto() { calls.push("goto"); throw new Error("submit must not run"); },
      locator() { calls.push("locator"); throw new Error("submit must not run"); },
    };
    await assert.doesNotReject(async () => {
      assert.deepEqual(await readPeatixRegistrationStateOnPage(page, candidate()), { status: "unavailable", reason: "readback_unavailable" });
      assert.deepEqual(await submitPeatixOnPage(page, candidate(), profile()), { status: "unavailable", reason: "readback_unavailable" });
    });
    assert.deepEqual(calls, []);
  }
});
