"use strict";

// scripts/browser-matrix-tally-bootstrap.js — BROWSER-MATRIX-1 §0.4.6a controlled inquiry asset.
//
// One-time fixture setup, NOT a routine action path (§0.4.6a As-Is/To-Be "provider fixture"): it
// creates the agent-owned Tally responder that the resident production browser loop will later
// submit an inquiry to. It runs in the deployed Railway container so the local/Mac browser side
// effect stays 0 (§0.4.6a MUST 6), reaches Steel only over Railway private networking (the base URL
// lives in lib/steel-cdp-client.js and is never taken from a public env), and emits ONLY the public
// form URL — never a code, the mail body, the password, cookies, or an editor/admin URL (§0.4.6a
// MUST 5).
//
// ─── MEASURED, NOT ASSUMED (live through Railway-private Steel, 2026-07-30) ──────────────────────
// Every page fact below was read off the real provider before it was written here. The previous
// revision guessed (`/signin`, a "/" slash-menu, `/new`) and died live at SUBMIT_EMAIL.
//
//   https://tally.so/signin              → 404, zero inputs. The URL does not exist.
//   https://tally.so/signup              → "Sign up - Tally"; ONE `#email` input; buttons
//                                          "Continue with Google"(button), "Continue with
//                                          Apple"(button), "Continue"(type=submit).
//   signup + Continue                    → the SAME page grows `#code` (maxLength 6) and the text
//                                          "We sent a 6-digit verification code to your inbox".
//                                          The page looks identical whether or not the account
//                                          already exists — only the MAILBOX can tell them apart.
//   mail, new account                    → from tally.so, "Confirm your email address", 6 digits.
//   mail, account already exists         → from tally.so, "You already have a Tally account",
//                                          NO code, offers login / password reset.
//   signup + valid code                  → navigates to https://tally.so/complete-profile with
//                                          `#firstName`, `#lastName`, `#password` + "Continue".
//   https://tally.so/login               → `#email` + `#password` + "Continue"(type=submit),
//                                          plus a "Reset" link to /forgot-password.
//   https://tally.so/forgot-password     → `#email` + "Send"(type=submit).
//   forgot-password + Send               → navigates to /forgot-password/reset carrying `#code`,
//                                          `#password` AND `#confirmPassword` on ONE page with a
//                                          "Reset"(type=submit) — so the code and the new password
//                                          are submitted together, after the mail has been read.
//   authenticated                        → https://tally.so/dashboard, "Dashboard - Tally", body
//                                          carries "New form" / "My workspace" / "Workspaces".
//   https://tally.so/forms/create        → redirects to /forms/<id>/edit; the first visible
//                                          [contenteditable] is the "Form title" block.
//   block insertion                      → typing "/" does NOT open the block menu under CDP
//                                          (Input.insertText fires no keydown; the block literally
//                                          became the text "/Short answer"). The real control is
//                                          the per-block `[aria-label="Open block selection modal"]`
//                                          affordance, whose panel carries a search input
//                                          ("Find questions, input fields and layout options…").
//                                          Filtering marks the first row with a `selected` class and
//                                          Enter inserts it; a synthetic .click() on the row does
//                                          nothing.
//   publish                              → "Publish" navigates to /forms/<id>/share, where an input
//                                          holds https://tally.so/r/<id> — the /r/ shape is real.
//
// ─── IDENTITY ───────────────────────────────────────────────────────────────────────────────────
// The Tally account is the AgentMail address (LM_AGENTMAIL_INBOX_ID), because that is the only
// mailbox this container can actually READ. LM_AGENT_BROWSER_EMAIL is a gmail plus-address with no
// reachable inbox here, so it is deliberately NOT the account identity and is not required.
// The password is derived from LM_BROWSER_SESSION_KEY, never stored and never printed, so a rerun
// on a fresh container reproduces it without a secret store.
//
// Structure mirrors scripts/browser-auth-luma-bootstrap.js so both providers share one proven
// shape: injectable boundaries, fixed failure stages, a tenant-bound encrypted auth context via
// lib/browser-auth-session-store.js, and a release in `finally` on every path — the OSS Steel build
// has exactly ONE session slot, so a leaked session blocks every browser job for every user.

const { createHmac } = require("node:crypto");

const TALLY_ORIGIN = "https://tally.so";
const TALLY_SIGNUP_URL = "https://tally.so/signup";
const TALLY_LOGIN_URL = "https://tally.so/login";
const TALLY_FORGOT_PASSWORD_URL = "https://tally.so/forgot-password";
const TALLY_CREATE_FORM_URL = "https://tally.so/forms/create";
const AGENTMAIL_API = "https://api.agentmail.to/v0";
const REQUIRED_ENV = Object.freeze([
  "BROWSER_MATRIX_TENANT_UID",
  "LM_AGENT_BROWSER_NAME",
  "LM_AGENTMAIL_API_KEY",
  "LM_AGENTMAIL_INBOX_ID",
  "LM_BROWSER_SESSION_KEY",
  "LM_FEEDBACK_DATABASE_URL",
]);
// Measured on the real /dashboard, lowercased.
const AUTH_MARKERS = new Map([
  ["new form", "new_form"],
  ["my workspace", "my_workspace"],
  ["workspaces", "workspaces"],
]);
// The controlled inquiry contract: exactly three fields, no personal data beyond what a public
// responder form always asks for. `block` is the verbatim label of the Tally block-panel row.
const INQUIRY_FORM = Object.freeze({
  title: "Life Manager inquiry",
  fields: Object.freeze([
    Object.freeze({ label: "name", kind: "text", block: "Short answer" }),
    Object.freeze({ label: "email", kind: "email", block: "Email" }),
    Object.freeze({ label: "message", kind: "long_text", block: "Long answer" }),
  ]),
});
const MAIL_TIMEOUT_MS = 120_000;
const MAIL_INTERVAL_MS = 3_000;
const MAIL_MAX_ATTEMPTS = 60;
const BOOTSTRAP_FAILURE_CODES = new Set([
  "CONFIG",
  "OPEN_STEEL",
  "SUBMIT_EMAIL",
  "POLL_EMAIL",
  "SUBMIT_CODE",
  "COMPLETE_PROFILE",
  "LOGIN",
  "RESET_PASSWORD",
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

// ─── Derived credential ─────────────────────────────────────────────────────────────────────────

// The account password is a pure function of (tenant session key, account address). It is never
// written to disk, never logged, and never returned — a rerun derives the same value, and a
// different tenant key or a different address derives a different one. The literal affixes satisfy
// Tally's complexity rule regardless of what base64url happens to emit (upper, lower, digit,
// symbol), which is what the live reset accepted.
function derivedTallyPassword(sessionKey, accountEmail) {
  const key = required(sessionKey);
  const email = required(accountEmail);
  if (!key || !email) {
    throw new TallyBootstrapError("Tally inquiry asset configuration unavailable", "CONFIG");
  }
  const digest = createHmac("sha256", key).update(`tally.so:${email}`).digest("base64url");
  return `Lm-${digest.slice(0, 28)}9!`;
}

// "Life Manager" → { firstName: "Life", lastName: "Manager" }. /complete-profile demands both, so a
// single-word display name repeats itself rather than submitting an empty field.
function agentProfileName(value) {
  const parts = required(value).split(/\s+/).filter(Boolean);
  if (!parts.length) {
    throw new TallyBootstrapError(
      "Tally inquiry asset configuration unavailable: missing LM_AGENT_BROWSER_NAME",
      "CONFIG",
    );
  }
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") || parts[0] };
}

function safeTallyLoginCode(value) {
  const code = required(value);
  if (!/^\d{6}$/.test(code)) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  return code;
}

// The ONLY URL this script is allowed to emit: a published public responder link. Editor/admin
// paths (/forms/<id>/edit, /forms/<id>/share) and any query/fragment token are rejected, not
// sanitised into silence. Measured live: https://tally.so/r/<id>.
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
    || !/^\/r\/[A-Za-z0-9_-]{1,64}$/.test(url.pathname)
    || url.search
    || url.hash
  ) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  return `${url.origin}${url.pathname}`;
}

// Non-throwing so the login branch can PROBE authentication and fall through to a password reset,
// while the final gate still fails closed.
function tallyAuthState(value) {
  if (!value || value.confirmed !== true) return null;
  const marker = AUTH_MARKERS.get(String(value.marker || "").replaceAll("_", " ").toLowerCase());
  if (!marker) return null;
  let current;
  try {
    current = new URL(String(value.currentUrl || ""));
  } catch {
    return null;
  }
  if (
    value.origin !== TALLY_ORIGIN
    || current.origin !== TALLY_ORIGIN
    || /(?:^|\/)(?:login|log-in|signin|sign-in|signup|sign-up|forgot-password|complete-profile)(?:\/|$)/i
      .test(current.pathname)
  ) {
    return null;
  }
  return { origin: TALLY_ORIGIN, marker };
}

function confirmedTallyAuth(value) {
  const state = tallyAuthState(value);
  if (!state) throw new TallyBootstrapError("Tally inquiry asset unavailable");
  return state;
}

async function runTallyInquiryBootstrap({ env = process.env, deps } = {}) {
  requiredEnvironment(env);
  const uid = required(env.BROWSER_MATRIX_TENANT_UID);
  const accountEmail = required(env.LM_AGENTMAIL_INBOX_ID);
  if (!/^[^@\s]+@[^@\s]+$/.test(accountEmail)) {
    throw new TallyBootstrapError(
      "Tally inquiry asset configuration unavailable: missing LM_AGENTMAIL_INBOX_ID",
      "CONFIG",
    );
  }
  const profile = agentProfileName(env.LM_AGENT_BROWSER_NAME);
  const password = derivedTallyPassword(env.LM_BROWSER_SESSION_KEY, accountEmail);
  if (
    !deps
    || typeof deps.now !== "function"
    || typeof deps.openBrowser !== "function"
    || typeof deps.readTallyMail !== "function"
    || typeof deps.saveContext !== "function"
  ) {
    throw new TallyBootstrapError("Tally inquiry asset configuration unavailable", "CONFIG");
  }

  let browser;
  let released = false;
  let stage = "OPEN_STEEL";
  try {
    browser = await deps.openBrowser();
    if (
      !browser
      || !required(browser.sessionId)
      || typeof browser.submitSignupEmail !== "function"
      || typeof browser.submitVerificationCode !== "function"
      || typeof browser.completeProfile !== "function"
      || typeof browser.submitLogin !== "function"
      || typeof browser.requestPasswordReset !== "function"
      || typeof browser.submitPasswordReset !== "function"
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
    const signupAt = deps.now();
    await browser.submitSignupEmail(accountEmail);

    stage = "POLL_EMAIL";
    // The signup page reads identically for a new and an existing account; the mail is the only
    // place the two differ, so the branch is decided here and nowhere else.
    const mail = await deps.readTallyMail({ afterMs: signupAt });
    const kind = mail && mail.kind;

    if (kind === "code") {
      stage = "SUBMIT_CODE";
      await browser.submitVerificationCode(safeTallyLoginCode(mail.code));
      stage = "COMPLETE_PROFILE";
      await browser.completeProfile({ ...profile, password });
    } else if (kind === "account_exists") {
      stage = "LOGIN";
      await browser.submitLogin({ email: accountEmail, password });
      if (!tallyAuthState(await browser.inspectAuthenticated())) {
        // The account predates this key (or the password was rotated): take ownership through the
        // reset flow, which lands on the same derived password.
        stage = "RESET_PASSWORD";
        const resetAt = deps.now();
        await browser.requestPasswordReset(accountEmail);
        const resetMail = await deps.readTallyMail({ afterMs: resetAt });
        if (!resetMail || resetMail.kind !== "code") {
          throw new TallyBootstrapError("Tally inquiry asset unavailable", "RESET_PASSWORD");
        }
        await browser.submitPasswordReset({
          code: safeTallyLoginCode(resetMail.code),
          password,
        });
      }
    } else {
      throw new TallyBootstrapError("Tally inquiry asset unavailable", "POLL_EMAIL");
    }

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

// ─── AgentMail: read a 6-digit code (or "this account exists") and NOTHING else ─────────────────

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

// Measured subjects: "Confirm your email address" (carries the code — the same subject is used for
// signup AND for the reset code) and "You already have a Tally account" (carries no code).
function classifyTallyMail(message) {
  if (!/tally/i.test(String(message && message.from || ""))) return null;
  const bodies = [
    message && message.text,
    message && message.extracted_text,
    message && message.preview,
    message && message.html,
    message && message.extracted_html,
  ];
  const haystack = [message && message.subject, ...bodies].map((part) => String(part || "")).join(" ");
  if (/already\s+have\s+a\s+tally\s+account/i.test(haystack)) return { kind: "account_exists" };
  for (const body of bodies) {
    const code = sixDigitCode(body);
    if (code) return { kind: "code", code };
  }
  return null;
}

function timestampMs(message) {
  const value = Date.parse(String(message && (message.timestamp || message.created_at) || ""));
  return Number.isFinite(value) ? value : 0;
}

// Bounded on BOTH axes: a wall-clock deadline and a hard attempt cap, so an unmoving clock cannot
// turn this into an unbounded loop. Nothing from a mail is ever logged or returned but the verdict.
async function pollTallyMail({
  afterMs,
  apiKey,
  inbox,
  fetchImpl,
  now,
  sleep,
}) {
  const deadline = now() + MAIL_TIMEOUT_MS;
  for (let attempt = 0; attempt < MAIL_MAX_ATTEMPTS; attempt += 1) {
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
        const verdict = classifyTallyMail({
          ...detail,
          from: detail && detail.from ? detail.from : message.from,
          subject: message.subject || (detail && detail.subject),
          preview: message.preview,
        });
        if (verdict) return verdict;
      }
    }
    await sleep(MAIL_INTERVAL_MS);
  }
  throw new TallyBootstrapError("Tally inquiry asset unavailable");
}

// ─── Page steps: small, injectable, measured-id based ───────────────────────────────────────────

// Tally's auth pages carry ONE <form>, but nothing here depends on it: the fields are located by
// their measured ids and the control by `button[type="submit"]`, falling back to an exact
// accessible-name match. "Continue with Google" / "Continue with Apple" are rejected explicitly and
// can never be clicked, because an OAuth hop would hand the account to a provider this container
// cannot log into.
function fillAndSubmitExpression(pairs, names) {
  return `(async () => {
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    if (!descriptor || typeof descriptor.set !== "function") return false;
    for (const [selector, value] of ${JSON.stringify(pairs)}) {
      const input = document.querySelector(selector);
      if (!input) return false;
      descriptor.set.call(input, value);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    const label = (element) =>
      String(element.innerText || element.getAttribute("aria-label") || "").replace(/\\s+/g, " ").trim();
    const buttons = Array.from(document.querySelectorAll("button, [role=button]"));
    const named = new RegExp("^(?:" + ${JSON.stringify(names.join("|"))} + ")$", "i");
    const submit = buttons.find((button) =>
      String(button.getAttribute("type") || "").toLowerCase() === "submit" && !/google|apple/i.test(label(button)))
      || buttons.find((button) => named.test(label(button)) && !/google|apple/i.test(label(button)));
    if (!submit) return false;
    if (/google|apple/i.test(label(submit))) return false;
    submit.click();
    return true;
  })()`;
}

async function pageAction(page, expression) {
  if (!page || typeof page.evaluate !== "function") {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  if (await page.evaluate(expression) !== true) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  return true;
}

function submitTallySignupEmail(page, email) {
  return pageAction(page, fillAndSubmitExpression([["#email", String(email)]], ["continue"]));
}

function submitTallyVerificationCode(page, code) {
  return pageAction(page, fillAndSubmitExpression([["#code", String(code)]], ["continue"]));
}

function completeTallyProfile(page, { firstName, lastName, password }) {
  return pageAction(page, fillAndSubmitExpression([
    ["#firstName", String(firstName)],
    ["#lastName", String(lastName)],
    ["#password", String(password)],
  ], ["continue"]));
}

function submitTallyLogin(page, { email, password }) {
  return pageAction(page, fillAndSubmitExpression([
    ["#email", String(email)],
    ["#password", String(password)],
  ], ["continue", "log in", "login"]));
}

function requestTallyPasswordReset(page, email) {
  return pageAction(page, fillAndSubmitExpression([["#email", String(email)]], ["send"]));
}

// /forgot-password/reset takes the code AND the new password on one page, so this runs only after
// the reset mail has been read.
function submitTallyPasswordReset(page, { code, password }) {
  return pageAction(page, fillAndSubmitExpression([
    ["#code", String(code)],
    ["#password", String(password)],
    ["#confirmPassword", String(password)],
  ], ["reset"]));
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
    const marker = ["new form", "my workspace", "workspaces"].find((text) => body.includes(text)) || null;
    const inputs = Array.from(document.querySelectorAll("input")).filter(visible);
    const authInput = inputs.some((input) => {
      const type = String(input.type || "").toLowerCase();
      const id = String(input.id || "").toLowerCase();
      return type === "password" || type === "email" || id === "code" || id === "email";
    });
    const authAction = Array.from(document.querySelectorAll("button, a[href], [role=button]"))
      .filter(visible)
      .some((element) => {
        const label = String(element.innerText || element.getAttribute("aria-label") || "")
          .replace(/\\s+/g, " ").trim();
        const href = String(element.getAttribute("href") || "");
        return /^(?:sign\\s*up|sign\\s*in|log\\s*in|login|continue\\s+with\\s+(?:google|apple))$/i.test(label)
          || /(?:^|\\/)(?:login|signup|signin|sign-in|forgot-password)(?:[/?#]|$)/i.test(href);
      });
    return {
      currentUrl: location.href,
      origin: location.origin,
      marker,
      confirmed: location.origin === "https://tally.so" && Boolean(marker) && !authInput && !authAction,
    };
  })()`;
}

// ─── Editor: measured affordances, trusted input ────────────────────────────────────────────────

// The editor is a rich SPA, so text goes in through trusted CDP input at a point the PAGE reported —
// never through a hand-written selector string that can drift from the element it describes.
function editorBlockPointExpression(position) {
  return `(() => {
    const blocks = Array.from(document.querySelectorAll('[contenteditable="true"]')).filter((element) => {
      const rect = element.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
    if (!blocks.length) return null;
    const target = ${position === "last" ? "blocks[blocks.length - 1]" : "blocks[0]"};
    const rect = target.getBoundingClientRect();
    return {
      x: Math.round(rect.left + Math.min(rect.width / 2, 40)),
      y: Math.round(rect.top + rect.height / 2),
    };
  })()`;
}

async function tallyEditorPoint(page, position = "first") {
  const point = await page.evaluate(editorBlockPointExpression(position));
  if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  return { x: Number(point.x), y: Number(point.y) };
}

// The affordance is per-block and only the one belonging to the block we just focused may be used,
// so the nearest one to that block's y is chosen rather than "the first in the DOM".
function openBlockModalExpression(y) {
  return `(() => {
    const controls = Array.from(document.querySelectorAll('[aria-label="Open block selection modal"]'));
    if (!controls.length) return false;
    let best = null;
    let bestDistance = Infinity;
    for (const control of controls) {
      const rect = control.getBoundingClientRect();
      const distance = Math.abs(rect.top + rect.height / 2 - ${Number(y)});
      if (distance < bestDistance) { bestDistance = distance; best = control; }
    }
    if (!best) return false;
    best.click();
    return true;
  })()`;
}

function filterBlockModalExpression(blockName) {
  return `(async () => {
    const search = Array.from(document.querySelectorAll("input"))
      .find((input) => /find questions/i.test(String(input.placeholder || "")));
    if (!search) return false;
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    if (!descriptor || typeof descriptor.set !== "function") return false;
    descriptor.set.call(search, ${JSON.stringify(String(blockName))});
    search.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 600));
    return true;
  })()`;
}

// The filtered panel marks its keyboard-highlighted row with a `selected` class, and Enter inserts
// exactly that row. Reading the highlight back BEFORE pressing Enter is what stops a drifted filter
// from silently inserting the wrong block type.
function highlightedBlockExpression() {
  return `(() => {
    const rows = Array.from(document.querySelectorAll('[class~="selected"]'))
      .map((element) => String(element.innerText || "").replace(/\\s+/g, " ").trim())
      .filter((text) => text && text.length <= 40);
    return rows.length ? rows[0] : null;
  })()`;
}

async function insertTallyFieldBlock(page, field, sleep) {
  await page.pressKey({ key: "Enter", code: "Enter" });
  await sleep(1_500);
  const block = await tallyEditorPoint(page, "last");
  await page.clickAt(block);
  await sleep(800);
  if (await page.evaluate(openBlockModalExpression(block.y)) !== true) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  await sleep(1_800);
  if (await page.evaluate(filterBlockModalExpression(field.block)) !== true) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  await sleep(1_200);
  const highlighted = String(await page.evaluate(highlightedBlockExpression()) || "").trim();
  if (highlighted.toLowerCase() !== String(field.block).toLowerCase()) {
    throw new TallyBootstrapError("Tally inquiry asset unavailable");
  }
  await page.pressKey({ key: "Enter", code: "Enter" });
  await sleep(2_000);
  await page.insertText(String(field.label));
  await sleep(1_000);
  return true;
}

async function createTallyInquiryForm(page, form, sleep) {
  await page.navigate(TALLY_CREATE_FORM_URL);
  await sleep(9_000);
  await page.clickAt(await tallyEditorPoint(page, "first"));
  await sleep(1_000);
  await page.insertText(String(form.title));
  await sleep(1_000);
  for (const field of form.fields) {
    await insertTallyFieldBlock(page, field, sleep);
  }
  return true;
}

async function publishTallyForm(page) {
  const clicked = await page.evaluate(`(() => {
    const visible = (element) => {
      const rect = element.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    };
    const button = Array.from(document.querySelectorAll('button, [role=button]'))
      .filter(visible)
      .find((element) =>
        /^publish$/i.test(String(element.innerText || element.getAttribute("aria-label") || "")
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
          async submitSignupEmail(email) {
            await page.navigate(TALLY_SIGNUP_URL);
            await sleep(4_000);
            await submitTallySignupEmail(page, email);
            await sleep(6_000);
          },
          async submitVerificationCode(code) {
            await submitTallyVerificationCode(page, code);
            await sleep(8_000);
          },
          async completeProfile(profile) {
            await completeTallyProfile(page, profile);
            await sleep(9_000);
          },
          async submitLogin(credentials) {
            await page.navigate(TALLY_LOGIN_URL);
            await sleep(4_000);
            await submitTallyLogin(page, credentials);
            await sleep(9_000);
          },
          async requestPasswordReset(email) {
            await page.navigate(TALLY_FORGOT_PASSWORD_URL);
            await sleep(4_000);
            await requestTallyPasswordReset(page, email);
            await sleep(6_000);
          },
          async submitPasswordReset(input) {
            await submitTallyPasswordReset(page, input);
            await sleep(9_000);
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
            await sleep(9_000);
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
    async readTallyMail({ afterMs }) {
      return pollTallyMail({ afterMs, apiKey, inbox, fetchImpl, now, sleep });
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
  TALLY_CREATE_FORM_URL,
  TALLY_FORGOT_PASSWORD_URL,
  TALLY_LOGIN_URL,
  TALLY_ORIGIN,
  TALLY_SIGNUP_URL,
  agentProfileName,
  authenticatedTallySnapshotExpression,
  classifyTallyMail,
  completeTallyProfile,
  createTallyInquiryForm,
  derivedTallyPassword,
  filterBlockModalExpression,
  highlightedBlockExpression,
  insertTallyFieldBlock,
  makeProductionDeps,
  openBlockModalExpression,
  pollTallyMail,
  publishTallyForm,
  readTallyPublicFormUrl,
  requestTallyPasswordReset,
  requiredEnvironment,
  runTallyInquiryBootstrap,
  safeTallyFormUrl,
  submitTallyLogin,
  submitTallyPasswordReset,
  submitTallySignupEmail,
  submitTallyVerificationCode,
  tallyEditorPoint,
};
