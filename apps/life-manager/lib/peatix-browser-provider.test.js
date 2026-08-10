"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { readPeatixRegistrationStateOnPage, submitPeatixOnPage } = require("./peatix-browser-provider.js");

const candidate = (extra = {}) => ({ provider: "peatix", event_ref: "peatix-event://event/5075819", canonical_url: "https://peatix.com/event/5075819", ticket_id: "6536845", registration_status: "available", ticket_price_status: "free", ticket_price_minor: 0, ...extra });
const profile = (extra = {}) => ({ name: "Dais Example", email: "dais@example.test", accept_organizer_privacy: true, ...extra });

function fixture(options = {}) {
  let state = options.initial || "tickets"; const calls = []; const checked = new Set(); let finals = 0;
  const fields = options.fields || [
    { selector: "#name", kind: "name", visible: true, checked: false },
    { selector: "#email", kind: "email", visible: true, checked: false },
    { selector: "#privacy", kind: "privacy", visible: true, checked: false },
  ];
  const formSelectors = new Set(["#name", "#email", "#privacy", "#form-submit-button", ...(options.formSelectors || [])]);
  const href = () => state === "tickets" ? "https://peatix.com/sales/event/5075819/tickets" : state === "form" ? "https://peatix.com/sales/event/5075819/form" : state === "confirm" ? (options.confirmUrl || `https://peatix.com/sales/event/${options.confirmEvent || "5075819"}/confirm`) : state === "complete" ? "https://peatix.com/sales/event/5075819/complete" : state === "ambiguous" ? "https://peatix.com/sales/event/5075819/unknown" : state === "auth" ? "https://peatix.com/login" : state === "canonical" ? (options.canonicalUrl || "https://peatix.com/event/5075819") : "https://peatix.com/event/9999999";
  const count = (s) => { if (state === "form" && /#[^\\[]*[\[\]]/.test(s)) throw new Error("invalid selector"); return state === "tickets" && s === "input[name=number_of_tickets_6536845]" ? 1 : state === "tickets" && s === "#next-button" ? 1 : state === "form" && formSelectors.has(s) ? 1 : state === "confirm" && s === "#confirm-button" ? 1 : 0; };
  const locator = (selector) => ({ count: async () => count(selector), isVisible: async () => count(selector) === 1, fill: async (value) => calls.push(["fill", selector, value]), check: async () => { calls.push(["check", selector]); checked.add(selector); }, isChecked: async () => checked.has(selector), click: async () => { calls.push(["click", selector]); if (selector === "#next-button") state = "form"; else if (selector === "#form-submit-button") state = "confirm"; else if (selector === "#confirm-button") { finals += 1; state = options.complete === false ? "ambiguous" : "complete"; } } });
  const page = {
    url: href,
    async goto(url) { calls.push(["goto", url]); state = /\/tickets$/.test(url) ? "tickets" : /\/form$/.test(url) ? "form" : "confirm"; },
    locator,
    async evaluate(_fn, payload) {
      assert.ok(payload && payload.mode);
      if (payload.mode === "form" && options.domFields) {
        const previousDocument = global.document; const previousCSS = global.CSS;
        const nodes = options.domFields.map((field) => ({ id: field.id || "", name: field.name || "", type: field.type || "text", hidden: false, checked: false, labels: field.label ? [{ textContent: field.label }] : [], getAttribute: (name) => name === "aria-label" ? field.ariaLabel || null : name === "data-label" ? field.dataLabel || null : name === "name" ? field.name || null : null }));
        global.document = { querySelectorAll: () => nodes, querySelector: () => options.formSubmit === false ? null : {} }; global.CSS = { escape: (value) => String(value).replace(/[^A-Za-z0-9_-]/g, "\\$&") };
        try { return _fn(); } finally { global.document = previousDocument; global.CSS = previousCSS; }
      }
      if (payload.mode === "form") return { fields };
      if (payload.mode === "confirm") return { text: options.confirmText || "チケットを申し込む", visible: true };
      if (state === "complete") return { href: href(), markers: options.marker === false ? [] : [{ event_id: "5075819", ticket_id: "6536845" }], checkout: false };
      if (state === "auth") return { href: href(), auth: true, markers: [], checkout: false };
      if (state === "cross") return { href: "https://peatix.com/sales/event/9999999/complete", markers: [{ event_id: "9999999", ticket_id: "6536845" }], checkout: false };
      if (state === "canonical" && options.markerEvent) return { href: href(), markers: [{ event_id: options.markerEvent, ticket_id: "6536845" }], checkout: false };
      return { href: href(), markers: [], checkout: ["tickets", "form", "confirm"].includes(state) };
    },
  };
  return { page, calls, finalCount: () => finals };
}

test("invalid input fails closed and registered readback is an idempotent no-op", async () => {
  for (const [c, p] of [[candidate({ provider: "luma" }), profile()], [candidate({ ticket_price_status: "paid", ticket_price_minor: 100 }), profile()], [candidate(), profile({ accept_organizer_privacy: false })], [{ id: "5075819", ticket: "6536845" }, profile()], [candidate({ canonical_url: "https://peatix.com:444/event/5075819" }), profile()]]) {
    const f = fixture(); assert.deepEqual(await submitPeatixOnPage(f.page, c, p), { status: "unavailable", reason: "invalid_input" }); assert.equal(f.calls.some((x) => x[0] === "goto"), false); assert.equal(f.finalCount(), 0);
  }
  const f = fixture({ initial: "complete" }); assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" }); assert.equal(f.calls.some((x) => x[0] === "goto"), false); assert.equal(f.finalCount(), 0);
  const canonical = fixture({ initial: "canonical" }); assert.deepEqual(await submitPeatixOnPage(canonical.page, candidate(), profile()), { status: "registered" });
  const wrong = fixture({ initial: "wrong" }); assert.equal((await submitPeatixOnPage(wrong.page, candidate(), profile())).status, "unavailable"); assert.equal(wrong.calls.some((x) => x[0] === "goto"), false);
  const wrongMarker = fixture({ initial: "canonical", markerEvent: "9999999" }); assert.equal((await submitPeatixOnPage(wrongMarker.page, candidate(), profile())).status, "unavailable"); assert.equal(wrongMarker.calls.some((x) => x[0] === "goto"), false);
  const portCanonical = fixture({ initial: "canonical", canonicalUrl: "https://peatix.com:444/event/5075819" }); assert.equal((await submitPeatixOnPage(portCanonical.page, candidate(), profile())).status, "unavailable"); assert.equal(portCanonical.calls.some((x) => x[0] === "goto"), false);
});

test("measured ticket/form/confirm flow fills exact fields and clicks final boundary once", async () => {
  const f = fixture(); const p = profile(); const result = await submitPeatixOnPage(f.page, candidate(), p);
  assert.deepEqual(result, { status: "registered" }); assert.equal(f.finalCount(), 1);
  assert.deepEqual(f.calls.filter((x) => ["fill", "check", "click"].includes(x[0])), [["fill", "input[name=number_of_tickets_6536845]", "1"], ["click", "#next-button"], ["fill", "#name", p.name], ["fill", "#email", p.email], ["check", "#privacy"], ["click", "#form-submit-button"], ["click", "#confirm-button"]]);
  assert.equal(JSON.stringify(result).includes(p.email), false);
});

test("special-character DOM ids use escaped selectors before final confirmation", async () => {
  const f = fixture({ domFields: [{ id: "name[0]", name: "attendee_name", label: "name", type: "text" }, { id: "email[0]", name: "attendee_email", label: "email", type: "email" }], formSelectors: ["#name\\[0\\]", "#email\\[0\\]"] });
  assert.deepEqual(await submitPeatixOnPage(f.page, candidate(), profile()), { status: "registered" }); assert.equal(f.finalCount(), 1);
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
