"use strict";

// scripts/browser-matrix-tally-bootstrap.js — BROWSER-MATRIX-1 §0.4.6a controlled inquiry asset.
//
// One-time fixture setup, NOT a routine action path (§0.4.6a As-Is/To-Be "provider fixture"): it
// creates the agent-owned Tally responder that the resident production browser loop will later
// submit an inquiry to. It runs in the deployed Railway container so the local/Mac browser side
// effect stays 0 (§0.4.6a MUST 6), reaches Steel only over Railway private networking (the base URL
// lives in lib/steel-cdp-client.js and is never taken from a public env), and emits ONLY the public
// form URL — never the OTP, the mail body, cookies, or an editor/admin URL (§0.4.6a MUST 5).
//
// Tally login is passwordless: submit the agent mailbox address, read the 6-digit code from
// AgentMail, submit the code. Structure mirrors scripts/browser-auth-luma-bootstrap.js so both
// email-code providers share one proven shape: injectable boundaries, fixed failure stages, a
// tenant-bound encrypted auth context via lib/browser-auth-session-store.js, and a release in
// `finally` on every path.

const TALLY_ORIGIN = "https://tally.so";
const TALLY_LOGIN_URL = "https://tally.so/signin";
// ASSUMPTION (live iteration confirms): the editor for a brand new form opens at /new.
const TALLY_NEW_FORM_URL = "https://tally.so/new";
const AGENTMAIL_API = "https://api.agentmail.to/v0";
const REQUIRED_ENV = Object.freeze([
  "BROWSER_MATRIX_TENANT_UID",
  "LM_AGENT_BROWSER_EMAIL",
  "LM_AGENT_BROWSER_NAME",
  "LM_AGENTMAIL_API_KEY",
  "LM_AGENTMAIL_INBOX_ID",
  "LM_BROWSER_SESSION_KEY",
  "LM_FEEDBACK_DATABASE_URL",
]);
const AUTH_MARKERS = new Map([
  ["new form", "new_form"],
  ["my forms", "my_forms"],
  ["workspace", "workspace"],
]);
// The controlled inquiry contract: exactly three fields, no personal data beyond what a public
// responder form always asks for.
const INQUIRY_FORM = Object.freeze({
  title: "Life Manager inquiry",
  fields: Object.freeze([
    Object.freeze({ label: "name", kind: "text", block: "Short answer" }),
    Object.freeze({ label: "email", kind: "email", block: "Email" }),
    Object.freeze({ label: "message", kind: "long_text", block: "Long answer" }),
  ]),
});
const LOGIN_CODE_TIMEOUT_MS = 120_000;
const LOGIN_CODE_INTERVAL_MS = 3_000;
const LOGIN_CODE_MAX_ATTEMPTS = 60;
const BOOTSTRAP_FAILURE_CODES = new Set([
  "CONFIG",
  "OPEN_STEEL",
  "SUBMIT_EMAIL",
  "POLL_EMAIL",
  "SUBMIT_CODE",
  "VERIFY_AUTH",
  "EXPORT_CONTEXT",
  "SAVE_CONTEXT",
  "CREATE_FORM",
  "PUBLISH_FORM",
  "READ_FORM_URL",
  "RELEASE",
]);

class TallyBootstrapError extends Error {
  constructor(message, code) {
    super(message);
    this.name = "TallyBootstrapError";
    if (BOOTSTRAP_FAILURE_CODES.has(code)) this.code = code;
  }
}

function required(value) {
  return String(value || "").trim();
}

// Names only. A value never reaches the message, so a misconfigured secret cannot leak here.
function requiredEnvironment(env) {
  const missing = REQUIRED_ENV.filter((name) => !required(env && env[name]));
  if (missing.length) {
    throw new TallyBootstrapError(
      `Tally inquiry asset configuration unavailable: missing ${missing.join(", ")}`,
      "CONFIG",
    );
  }
  return true;
}

function safeTallyLoginCode(value) {
  const code = required(value);
  if (!/^\d{6}$/.test(code)) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  return code;
}

// The ONLY URL this script is allowed to emit: a published public responder link. Editor/admin
// paths (/forms/<id>/edit) and any query/fragment token are rejected, not sanitised into silence.
function safeTallyFormUrl(value) {
  let url;
  try {
    url = new URL(String(value || ""));
  } catch {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  const host = url.hostname.toLowerCase();
  if (
    url.protocol !== "https:"
    || url.username
    || url.password
    || (host !== "tally.so" && !host.endsWith(".tally.so"))
    // ASSUMPTION (live iteration confirms): published Tally forms are served at /r/<formId>.
    || !/^\/r\/[A-Za-z0-9_-]{1,64}$/.test(url.pathname)
    || url.search
    || url.hash
  ) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  return `${url.origin}${url.pathname}`;
}

function confirmedTallyAuth(value) {
  if (!value || value.confirmed !== true || !AUTH_MARKERS.has(
    String(value.marker || "").replaceAll("_", " ").toLowerCase(),
  )) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  let current;
  try {
    current = new URL(String(value.currentUrl || ""));
  } catch {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  if (
    value.origin !== TALLY_ORIGIN
    || current.origin !== TALLY_ORIGIN
    || /(?:^|\/)(?:login|log-in|signin|sign-in)(?:\/|$)/i.test(current.pathname)
  ) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  return { origin: TALLY_ORIGIN, marker: AUTH_MARKERS.get(String(value.marker).replaceAll("_", " ").toLowerCase()) };
}

async function runTallyInquiryBootstrap({ env = process.env, deps } = {}) {
  requiredEnvironment(env);
  const uid = required(env.BROWSER_MATRIX_TENANT_UID);
  const email = required(env.LM_AGENT_BROWSER_EMAIL);
  if (!/^[^@\s]+@[^@\s]+$/.test(email)) {
    throw new TallyBootstrapError(
      "Tally inquiry asset configuration unavailable: missing LM_AGENT_BROWSER_EMAIL",
      "CONFIG",
    );
  }
  if (
    !deps
    || typeof deps.now !== "function"
    || typeof deps.openBrowser !== "function"
    || typeof deps.readLoginCode !== "function"
    || typeof deps.saveContext !== "function"
  ) {
    throw new TallyBootstrapError("Tally inquiry asset configuration unavailable", "CONFIG");
  }

  const afterMs = deps.now();
  let browser;
  let released = false;
  let stage = "OPEN_STEEL";
  try {
    browser = await deps.openBrowser();
    if (
      !browser
      || !required(browser.sessionId)
      || typeof browser.requestLoginCode !== "function"
      || typeof browser.submitLoginCode !== "function"
      || typeof browser.inspectAuthenticated !== "function"
      || typeof browser.exportContext !== "function"
      || typeof browser.createInquiryForm !== "function"
      || typeof browser.publishForm !== "function"
      || typeof browser.readPublicFormUrl !== "function"
      || typeof browser.release !== "function"
    ) {
      throw new TallyBootstrapError("Tally inquiry asset configuration unavailable", "OPEN_STEEL");
    }
    stage = "SUBMIT_EMAIL";
    await browser.requestLoginCode(email);
    stage = "POLL_EMAIL";
    const code = safeTallyLoginCode(await deps.readLoginCode({ afterMs }));
    stage = "SUBMIT_CODE";
    await browser.submitLoginCode(code);
    stage = "VERIFY_AUTH";
    const auth = confirmedTallyAuth(await browser.inspectAuthenticated());
    stage = "EXPORT_CONTEXT";
    const context = await browser.exportContext();
    stage = "SAVE_CONTEXT";
    const saved = await deps.saveContext({
      uid,
      origin: TALLY_ORIGIN,
      principalKind: "agent_owned",
      context,
    });
    if (
      !saved
      || !/^[a-f0-9]{64}$/.test(String(saved.context_sha256 || ""))
      || !Number.isSafeInteger(saved.key_version)
      || saved.key_version < 1
    ) {
      throw new TallyBootstrapError("Tally inquiry asset unavailable");
    }
    stage = "CREATE_FORM";
    if (await browser.createInquiryForm(INQUIRY_FORM) !== true) {
      throw new TallyBootstrapError("Tally inquiry asset unavailable");
    }
    stage = "PUBLISH_FORM";
    if (await browser.publishForm() !== true) {
      throw new TallyBootstrapError("Tally inquiry asset unavailable");
    }
    stage = "READ_FORM_URL";
    const formUrl = safeTallyFormUrl(await browser.readPublicFormUrl());
    stage = "RELEASE";
    released = await browser.release() === true;
    browser = null;
    if (!released || auth.origin !== TALLY_ORIGIN) {
      throw new TallyBootstrapError("Tally inquiry asset unavailable");
    }
    return Object.freeze({
      origin: TALLY_ORIGIN,
      form_url: formUrl,
      context_saved: true,
      steel_released: true,
    });
  } catch (error) {
    if (error instanceof TallyBootstrapError && error.code) throw error;
    throw new TallyBootstrapError("Tally inquiry asset unavailable", stage);
  } finally {
    if (browser && typeof browser.release === "function") {
      try { await browser.release(); } catch { /* the safe generic failure above stays authoritative */ }
    }
  }
}

// ─── AgentMail: read a 6-digit code and NOTHING else ─────────────────────────────────────────────

// URLs, hex colours and entity noise are removed BEFORE matching, so a tracking link that happens
// to carry six digits can never be mistaken for the code. Two different six-digit candidates in the
// same body are ambiguous, and ambiguity fails closed rather than guessing.
function sixDigitCode(value) {
  const cleaned = String(value || "")
    .replace(/https?:\/\/[^\s"'<>]+/gi, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/#[0-9a-fA-F]{3,8}\b/g, " ")
    .replace(/&[a-zA-Z#0-9]{1,10};/g, " ");
  const matches = cleaned.match(/(?<![0-9])[0-9]{6}(?![0-9])/g) || [];
  const unique = [...new Set(matches)];
  return unique.length === 1 ? unique[0] : null;
}

function extractTallyLoginCode(message) {
  if (!/tally/i.test(String(message && message.from || ""))) return null;
  for (const body of [
    message && message.text,
    message && message.extracted_text,
    message && message.preview,
    message && message.html,
    message && message.extracted_html,
  ]) {
    const code = sixDigitCode(body);
    if (code) return code;
  }
  return null;
}

function timestampMs(message) {
  const value = Date.parse(String(message && (message.timestamp || message.created_at) || ""));
  return Number.isFinite(value) ? value : 0;
}

// Bounded on BOTH axes: a wall-clock deadline and a hard attempt cap, so an unmoving clock cannot
// turn this into an unbounded loop. Nothing from a mail is ever logged or returned but the digits.
async function pollTallyLoginCode({
  afterMs,
  apiKey,
  inbox,
  fetchImpl,
  now,
  sleep,
}) {
  const deadline = now() + LOGIN_CODE_TIMEOUT_MS;
  for (let attempt = 0; attempt < LOGIN_CODE_MAX_ATTEMPTS; attempt += 1) {
    if (now() >= deadline) break;
    const listResponse = await fetchImpl(
      `${AGENTMAIL_API}/inboxes/${encodeURIComponent(inbox)}/messages?limit=20`,
      { headers: { Authorization: `Bearer ${apiKey}` } },
    );
    if (listResponse && listResponse.ok) {
      const payload = await listResponse.json().catch(() => ({}));
      const messages = Array.isArray(payload && payload.messages) ? payload.messages : [];
      const candidates = messages
        .filter((message) => timestampMs(message) >= afterMs - 5_000)
        .sort((a, b) => timestampMs(b) - timestampMs(a));
      for (const message of candidates) {
        const messageId = required(message && message.message_id);
        if (!messageId) continue;
        const detailResponse = await fetchImpl(
          `${AGENTMAIL_API}/inboxes/${encodeURIComponent(inbox)}/messages/${encodeURIComponent(messageId)}`,
          { headers: { Authorization: `Bearer ${apiKey}` } },
        );
        if (!detailResponse || !detailResponse.ok) continue;
        const detail = await detailResponse.json().catch(() => ({}));
        const code = extractTallyLoginCode({
          ...detail,
          from: detail && detail.from ? detail.from : message.from,
          subject: message.subject,
          preview: message.preview,
        });
        if (code) return code;
      }
    }
    await sleep(LOGIN_CODE_INTERVAL_MS);
  }
  throw new TallyBootstrapError("Tally inquiry asset unavailable");
}

// ─── Page steps: small, injectable, role/name/text based ─────────────────────────────────────────

async function requestTallyEmailLogin(page, email) {
  if (!page || typeof page.evaluate !== "function") {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  const submitted = await page.evaluate(`(async () => {
    const input = document.querySelector('input[type="email"], input[name="email"], input[autocomplete="email"]');
    if (!input) return false;
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    if (!descriptor || typeof descriptor.set !== "function") return false;
    descriptor.set.call(input, ${JSON.stringify(email)});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 250));
    const form = input.closest("form");
    const submit = (form && form.querySelector('button[type="submit"]'))
      || Array.from(document.querySelectorAll("button")).find((button) =>
        /^(?:continue|continue with email|sign in|log in|login|send code|get started)$/i.test(
          String(button.innerText || button.getAttribute("aria-label") || "").replace(/\\s+/g, " ").trim()
        ))
      || document.querySelector('button[type="submit"]');
    if (!submit) return false;
    submit.click();
    return true;
  })()`);
  if (submitted !== true) throw new TallyBootstrapError("Tally inquiry asset unavailable");
  return true;
}

// Handles both measured shapes without branching in JS: six one-character boxes, or a single
// six-character one-time-code input.
async function submitTallyLoginCode(page, code) {
  const submitted = await page.evaluate(`(async () => {
    const digits = ${JSON.stringify(code)}.split("");
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    if (!descriptor || typeof descriptor.set !== "function") return false;
    const fill = async (input, value) => {
      descriptor.set.call(input, value);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, 100));
    };
    const boxes = Array.from(document.querySelectorAll("input")).filter((input) =>
      input.maxLength === 1
      || String(input.autocomplete || "").toLowerCase() === "one-time-code"
      || String(input.inputMode || "").toLowerCase() === "numeric");
    if (boxes.length >= 6) {
      for (let index = 0; index < 6; index += 1) await fill(boxes[index], digits[index]);
      return true;
    }
    const single = boxes[0]
      || document.querySelector('input[autocomplete="one-time-code"], input[name="code"], input[type="text"]');
    if (!single) return false;
    await fill(single, digits.join(""));
    const form = single.closest("form");
    const submit = (form && form.querySelector('button[type="submit"]'))
      || Array.from(document.querySelectorAll("button")).find((button) =>
        /^(?:continue|verify|sign in|log in|login|submit)$/i.test(
          String(button.innerText || button.getAttribute("aria-label") || "").replace(/\\s+/g, " ").trim()
        ));
    if (submit) submit.click();
    return true;
  })()`);
  if (submitted !== true) throw new TallyBootstrapError("Tally inquiry asset unavailable");
  return true;
}

function authenticatedTallySnapshotExpression() {
  return `(() => {
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
    const marker = ["new form", "my forms", "workspace"].find((text) => body.includes(text)) || null;
    const inputs = Array.from(document.querySelectorAll("input")).filter(visible);
    const authInput = inputs.some((input) => {
      const type = String(input.type || "").toLowerCase();
      const autocomplete = String(input.autocomplete || "").toLowerCase();
      return type === "password" || type === "email" || autocomplete === "email"
        || autocomplete === "username" || autocomplete === "one-time-code";
    });
    const authAction = Array.from(document.querySelectorAll("button, a[href], [role=button]"))
      .filter(visible)
      .some((element) => {
        const label = String(element.innerText || element.getAttribute("aria-label") || "")
          .replace(/\\s+/g, " ").trim();
        const href = String(element.getAttribute("href") || "");
        return /^(?:sign\\s*in|log\\s*in|login|get\\s+started|continue\\s+with\\s+email|send\\s+code)$/i.test(label)
          || /(?:^|\\/)(?:login|signin|sign-in)(?:[/?#]|$)/i.test(href);
      });
    return {
      currentUrl: location.href,
      origin: location.origin,
      marker,
      confirmed: location.origin === "https://tally.so" && Boolean(marker) && !authInput && !authAction,
    };
  })()`;
}

// The editor is a rich SPA, so text goes in through trusted CDP input at a point the PAGE reported —
// never through a hand-written selector string that can drift from the element it describes.
async function tallyEditorPoint(page) {
  const point = await page.evaluate(`(() => {
    const candidates = Array.from(document.querySelectorAll('[contenteditable="true"], textarea, input[type="text"]'));
    const target = candidates.find((element) => {
      const rect = element.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
    if (!target) return null;
    const rect = target.getBoundingClientRect();
    return { x: Math.round(rect.left + Math.min(rect.width / 2, 40)), y: Math.round(rect.top + rect.height / 2) };
  })()`);
  if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  return { x: Number(point.x), y: Number(point.y) };
}

// ASSUMPTION (live iteration confirms): the block menu opens with "/", filters by the block name,
// and Enter inserts it; the label is then typed into the inserted question.
async function insertTallyFieldBlock(page, field, sleep) {
  await page.pressKey({ key: "Enter", code: "Enter" });
  await sleep(800);
  await page.insertText("/");
  await sleep(800);
  await page.insertText(String(field.block));
  await sleep(1_200);
  await page.pressKey({ key: "Enter", code: "Enter" });
  await sleep(1_200);
  await page.insertText(String(field.label));
  await sleep(800);
  return true;
}

async function createTallyInquiryForm(page, form, sleep) {
  await page.navigate(TALLY_NEW_FORM_URL);
  await sleep(6_000);
  await page.clickAt(await tallyEditorPoint(page));
  await sleep(800);
  await page.insertText(String(form.title));
  await sleep(800);
  for (const field of form.fields) {
    await insertTallyFieldBlock(page, field, sleep);
  }
  return true;
}

async function publishTallyForm(page) {
  const clicked = await page.evaluate(`(() => {
    const button = Array.from(document.querySelectorAll('button, [role=button], a[href]')).find((element) =>
      /^publish(?:\\s+form)?$/i.test(String(element.innerText || element.getAttribute("aria-label") || "")
        .replace(/\\s+/g, " ").trim()));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  if (clicked !== true) throw new TallyBootstrapError("Tally inquiry asset unavailable");
  return true;
}

// Reads the share surface only. Editor URLs never match, because only /r/<id> is collected.
async function readTallyPublicFormUrl(page) {
  const found = await page.evaluate(`(() => {
    const pattern = /https:\\/\\/tally\\.so\\/r\\/[A-Za-z0-9_-]{1,64}/;
    const sources = [];
    for (const input of Array.from(document.querySelectorAll("input, textarea"))) {
      sources.push(String(input.value || ""));
    }
    for (const anchor of Array.from(document.querySelectorAll("a[href]"))) {
      sources.push(String(anchor.getAttribute("href") || ""));
    }
    sources.push(String(document.body && document.body.innerText || ""));
    for (const source of sources) {
      const match = source.match(pattern);
      if (match) return match[0];
    }
    return null;
  })()`);
  return found;
}

function makeProductionDeps(env = process.env, boundaries = {}) {
  const { makeSteelCdpClient } = require("../lib/steel-cdp-client.js");
  const { connectCdp: defaultConnectCdp } = require("../lib/cdp-connection.js");
  const { upsertBrowserAuthSession } = require("../lib/browser-auth-session-store.js");
  requiredEnvironment(env);
  const steel = boundaries.steel || makeSteelCdpClient();
  const connectCdp = boundaries.connectCdp || defaultConnectCdp;
  const fetchImpl = boundaries.fetchImpl || globalThis.fetch;
  const sleep = boundaries.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const now = boundaries.now || (() => Date.now());
  const apiKey = required(env.LM_AGENTMAIL_API_KEY);
  const inbox = required(env.LM_AGENTMAIL_INBOX_ID);

  return {
    now,
    async openBrowser() {
      const session = await steel.createRawSession({ blockAds: true });
      let page;
      try {
        page = await connectCdp(session.websocketUrl, { timeoutMs: 30_000 });
        return {
          sessionId: String(session.id),
          async requestLoginCode(email) {
            await page.navigate(TALLY_LOGIN_URL);
            await sleep(3_000);
            await requestTallyEmailLogin(page, email);
            await sleep(2_000);
          },
          async submitLoginCode(code) {
            await submitTallyLoginCode(page, code);
            await sleep(6_000);
          },
          async inspectAuthenticated() {
            return page.evaluate(authenticatedTallySnapshotExpression());
          },
          async exportContext() {
            return steel.getSessionContext(String(session.id));
          },
          async createInquiryForm(form) {
            return createTallyInquiryForm(page, form, sleep);
          },
          async publishForm() {
            const published = await publishTallyForm(page);
            await sleep(5_000);
            return published;
          },
          async readPublicFormUrl() {
            return readTallyPublicFormUrl(page);
          },
          async release() {
            try { await page.close(); } catch { /* Steel owns the actual cloud slot. */ }
            return steel.releaseSession(String(session.id));
          },
        };
      } catch (error) {
        if (page) {
          try { await page.close(); } catch {}
        }
        try { await steel.releaseSession(String(session.id)); } catch {}
        throw error;
      }
    },
    async readLoginCode({ afterMs }) {
      return pollTallyLoginCode({ afterMs, apiKey, inbox, fetchImpl, now, sleep });
    },
    async saveContext(input) {
      return upsertBrowserAuthSession(input);
    },
  };
}

async function main() {
  try {
    requiredEnvironment(process.env);
    const deps = makeProductionDeps(process.env);
    const result = await runTallyInquiryBootstrap({ env: process.env, deps });
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    const message = error instanceof TallyBootstrapError && error.code === "CONFIG"
      ? error.message
      : "Tally inquiry asset unavailable";
    const code = BOOTSTRAP_FAILURE_CODES.has(error && error.code) ? error.code : "CONFIG";
    process.stderr.write(`${message} [${code}]\n`);
    process.exitCode = 1;
  }
}

if (require.main === module) main();

module.exports = {
  INQUIRY_FORM,
  TALLY_ORIGIN,
  authenticatedTallySnapshotExpression,
  createTallyInquiryForm,
  extractTallyLoginCode,
  insertTallyFieldBlock,
  makeProductionDeps,
  pollTallyLoginCode,
  publishTallyForm,
  readTallyPublicFormUrl,
  requestTallyEmailLogin,
  requiredEnvironment,
  runTallyInquiryBootstrap,
  safeTallyFormUrl,
  submitTallyLoginCode,
  tallyEditorPoint,
};
