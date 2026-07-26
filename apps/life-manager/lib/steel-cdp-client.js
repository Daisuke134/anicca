"use strict";
// lib/steel-cdp-client.js — the self-hosted steel-browser rail (§10.0 裁定12).
//
// steel-browser runs as a SEPARATE Railway service in the same project as life-call. The OSS build
// ships no API auth, so it has NO public domain: it is reachable only over Railway private
// networking at steel-browser.railway.internal:3000. Nothing in this module may ever accept a
// public base URL by default.
//
// ─── ROUTES (verified against source, not memory) ────────────────────────────────────────────────
// steel-dev/steel-browser, api/src/steel-browser-plugin.ts:81
//     await fastify.register(sessionsRoutes, { prefix: "/v1" });
// steel-dev/steel-browser, api/src/modules/sessions/sessions.routes.ts
//     GET  /health                    → { status: "ok" } | 503 { status: "service_unavailable" }
//     POST /sessions                  → SessionDetails
//     GET  /sessions/:sessionId       → SessionDetails
//     POST /sessions/:sessionId/release → ReleaseSession
//     POST /sessions/release          → ReleaseSession   (release ALL)
// There is NO `DELETE /v1/sessions`: release is a POST. SessionDetails (sessions.schema.ts) carries
// `id`, `status` ∈ idle|live|released|failed, and `websocketUrl` — the CDP endpoint we connect to.
//
// ─── ONE SESSION AT A TIME ──────────────────────────────────────────────────────────────────────
// The OSS build holds a single activeSession, so every booking job must create a fresh session, use
// it, and release it. The executor's `finally` does the releasing; this module makes release cheap
// and also tears down the CDP socket, because a live socket against a released session is the same
// leak by another name.

const STEEL_BASE_URL = "http://steel-browser.railway.internal:3000";

// The page-side probe. Runs in the provider's page and returns the same field descriptor shape
// care-booking-executor.js reasons about: {selector, label, name, type, required}. The label is the
// text a human reads — <label for>, a wrapping <label>, aria-label, or the placeholder — because
// that is what the deterministic matcher matches on.
const READ_FORM_EXPRESSION = `(() => {
  const form = document.querySelector("form") || document.body;
  const nodes = [...form.querySelectorAll("input, select, textarea")];
  const labelOf = (el) => {
    if (el.id) {
      const explicit = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (explicit && explicit.textContent.trim()) return explicit.textContent.trim();
    }
    const wrapper = el.closest("label");
    if (wrapper && wrapper.textContent.trim()) return wrapper.textContent.trim();
    return (el.getAttribute("aria-label") || el.getAttribute("placeholder") || "").trim();
  };
  const selectorOf = (el, i) => (el.id ? "#" + CSS.escape(el.id)
    : el.name ? el.tagName.toLowerCase() + '[name="' + CSS.escape(el.name) + '"]'
    : "__lm_field_" + i);
  const fields = nodes
    .filter((el) => !["hidden", "submit", "button", "image", "reset"].includes((el.type || "").toLowerCase()))
    .map((el, i) => ({
      selector: selectorOf(el, i),
      label: labelOf(el),
      name: el.name || null,
      type: el.tagName.toLowerCase() === "textarea" ? "textarea"
        : el.tagName.toLowerCase() === "select" ? "select"
        : (el.type || "text").toLowerCase(),
      required: el.required === true || el.getAttribute("aria-required") === "true",
    }));
  const submit = form.querySelector('button[type="submit"], input[type="submit"], button:not([type])');
  return { submitSelector: submit ? (submit.id ? "#" + CSS.escape(submit.id) : 'form button[type="submit"], form input[type="submit"]') : null, fields };
})()`;

const READBACK_EXPRESSION = `({ text: document.body ? document.body.innerText.slice(0, 4000) : "", url: location.href })`;

function fillExpression(selector, value) {
  return `(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) throw new Error("field not found: " + ${JSON.stringify(selector)});
    const setter = Object.getOwnPropertyDescriptor(el.constructor.prototype, "value");
    if (setter && setter.set) setter.set.call(el, ${JSON.stringify(value)}); else el.value = ${JSON.stringify(value)};
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`;
}

function submitExpression(selector) {
  return `(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) throw new Error("submit control not found");
    el.click();
    return true;
  })()`;
}

async function readJson(response) {
  if (typeof response.json === "function") return response.json();
  return JSON.parse(await response.text());
}

// The real CDP connection is injected (`connectCdp`) so the protocol wiring can be swapped or
// stubbed without this module smuggling a websocket import into every test that touches booking.
function makeSteelCdpClient({ baseUrl = STEEL_BASE_URL, fetchImpl, connectCdp } = {}) {
  const doFetch = fetchImpl || globalThis.fetch;
  const connect = connectCdp || require("./cdp-connection.js").connectCdp;
  let connection = null;

  async function page() {
    if (!connection) throw new Error("no steel session — createSession() first");
    return connection;
  }

  return {
    baseUrl,
    async health() {
      const response = await doFetch(`${baseUrl}/v1/health`);
      return Boolean(response && response.ok);
    },
    async createSession(options = {}) {
      const response = await doFetch(`${baseUrl}/v1/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ blockAds: true, ...options }),
      });
      if (!response || !response.ok) {
        const body = response && typeof response.text === "function" ? await response.text().catch(() => "") : "";
        throw new Error(`steel session launch failed (${response ? response.status : "no response"})${body ? `: ${body.slice(0, 200)}` : ""}`);
      }
      const details = await readJson(response);
      if (!details || !details.id || !details.websocketUrl) throw new Error("steel session response carried no CDP endpoint");
      connection = await connect(details.websocketUrl);
      return { id: details.id, websocketUrl: details.websocketUrl };
    },
    async navigate(_sessionId, url) {
      return (await page()).navigate(url);
    },
    async readForm(_sessionId) {
      return (await page()).evaluate(READ_FORM_EXPRESSION);
    },
    async fill(_sessionId, selector, value) {
      return (await page()).evaluate(fillExpression(selector, value));
    },
    async submit(_sessionId, selector) {
      return (await page()).evaluate(submitExpression(selector));
    },
    async readConfirmation(_sessionId) {
      return (await page()).evaluate(READBACK_EXPRESSION);
    },
    async releaseSession(sessionId) {
      const open = connection;
      connection = null;
      if (open && typeof open.close === "function") {
        try { await open.close(); } catch { /* the HTTP release below is what actually frees the slot */ }
      }
      const response = await doFetch(`${baseUrl}/v1/sessions/${encodeURIComponent(sessionId)}/release`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!response || !response.ok) {
        throw new Error(`steel session release failed (${response ? response.status : "no response"})`);
      }
      return true;
    },
  };
}

module.exports = { makeSteelCdpClient, STEEL_BASE_URL, READ_FORM_EXPRESSION };
