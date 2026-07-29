"use strict";

const LUMA_ORIGIN = "https://luma.com";
const LUMA_LOGIN_URL = "https://luma.com/signin";
const AGENTMAIL_API = "https://api.agentmail.to/v0";
const AUTH_MARKERS = new Map([
  ["create event", "create_event"],
  ["my events", "my_events"],
  ["manage events", "manage_events"],
]);

class LumaBootstrapError extends Error {}

function required(value) {
  return String(value || "").trim();
}

function safeLumaMagicLink(value) {
  let url;
  try {
    url = new URL(String(value || ""));
  } catch {
    throw new LumaBootstrapError("Luma authentication unavailable");
  }
  const host = url.hostname.toLowerCase();
  const lumaHost = host === "luma.com" || host.endsWith(".luma.com") || host === "lu.ma";
  const authShape = /(?:auth|login|sign[-_]?in|magic|verify|token|code)/i.test(
    `${url.pathname}${url.search}`,
  );
  if (
    url.protocol !== "https:"
    || url.username
    || url.password
    || !lumaHost
    || !authShape
  ) {
    throw new LumaBootstrapError("Luma authentication unavailable");
  }
  return url.toString();
}

function safeLumaAuthChallenge(value) {
  const raw = String(value || "");
  if (/^luma-code:\d{6}$/.test(raw)) return raw;
  return safeLumaMagicLink(raw);
}

function confirmedLumaAuth(value) {
  if (!value || value.confirmed !== true || !AUTH_MARKERS.has(
    String(value.marker || "").replaceAll("_", " ").toLowerCase(),
  )) {
    throw new LumaBootstrapError("Luma authentication unavailable");
  }
  let current;
  try {
    current = new URL(String(value.currentUrl || ""));
  } catch {
    throw new LumaBootstrapError("Luma authentication unavailable");
  }
  if (
    value.origin !== LUMA_ORIGIN
    || current.origin !== LUMA_ORIGIN
    || /(?:^|\/)(?:login|log-in|signin|sign-in)(?:\/|$)/i.test(current.pathname)
  ) {
    throw new LumaBootstrapError("Luma authentication unavailable");
  }
  return {
    origin: LUMA_ORIGIN,
    currentUrl: current.toString(),
    marker: AUTH_MARKERS.get(String(value.marker).replaceAll("_", " ").toLowerCase()),
  };
}

async function runLumaBootstrap({ env = process.env, deps } = {}) {
  const uid = required(env && env.BROWSER_AUTH_TENANT_A_UID);
  const email = required(env && env.LM_AGENTMAIL_INBOX_ID);
  if (
    !uid
    || !/^[^@\s]+@[^@\s]+$/.test(email)
    || !deps
    || typeof deps.openBrowser !== "function"
  ) {
    throw new LumaBootstrapError("Luma bootstrap configuration unavailable");
  }
  if (
    typeof deps.now !== "function"
    || typeof deps.readMagicLink !== "function"
    || typeof deps.saveContext !== "function"
  ) {
    throw new LumaBootstrapError("Luma bootstrap configuration unavailable");
  }

  const afterMs = deps.now();
  let browser;
  let sessionId;
  let released = false;
  try {
    browser = await deps.openBrowser();
    if (
      !browser
      || !required(browser.sessionId)
      || typeof browser.requestMagicLink !== "function"
      || typeof browser.openMagicLink !== "function"
      || typeof browser.inspectAuthenticated !== "function"
      || typeof browser.exportContext !== "function"
      || typeof browser.release !== "function"
    ) {
      throw new LumaBootstrapError("Luma bootstrap configuration unavailable");
    }
    sessionId = required(browser.sessionId);
    await browser.requestMagicLink(email);
    const challenge = safeLumaAuthChallenge(await deps.readMagicLink({ afterMs }));
    await browser.openMagicLink(challenge);
    const auth = confirmedLumaAuth(await browser.inspectAuthenticated());
    const context = await browser.exportContext();
    const saved = await deps.saveContext({
      uid,
      origin: LUMA_ORIGIN,
      principalKind: "agent_owned",
      context,
    });
    released = await browser.release() === true;
    browser = null;
    if (
      !released
      || !saved
      || !/^[a-f0-9]{64}$/.test(String(saved.context_sha256 || ""))
      || !Number.isSafeInteger(saved.key_version)
      || saved.key_version < 1
    ) {
      throw new LumaBootstrapError("Luma authentication unavailable");
    }
    return Object.freeze({
      origin: auth.origin,
      current_url: auth.currentUrl,
      authenticated: true,
      marker: auth.marker,
      session_id: sessionId,
      context_sha256: saved.context_sha256,
      key_version: saved.key_version,
      released,
    });
  } catch (error) {
    if (error instanceof LumaBootstrapError) throw error;
    throw new LumaBootstrapError("Luma authentication unavailable");
  } finally {
    if (browser && typeof browser.release === "function") {
      try { await browser.release(); } catch { /* the safe generic failure above remains authoritative */ }
    }
  }
}

function decodeHtmlUrl(value) {
  return String(value || "")
    .replaceAll("&amp;", "&")
    .replaceAll("&#x2F;", "/")
    .replaceAll("&#47;", "/")
    .replace(/[).,;]+$/, "");
}

function extractMagicLink(message) {
  const source = [
    message && message.html,
    message && message.text,
    message && message.extracted_html,
    message && message.extracted_text,
  ].filter(Boolean).join("\n");
  const links = source.match(/https:\/\/[^\s"'<>]+/gi) || [];
  for (const raw of links) {
    try {
      return safeLumaMagicLink(decodeHtmlUrl(raw));
    } catch {
      // A mail can contain tracking and unsubscribe links. Only a direct Luma auth URL is accepted.
    }
  }
  return null;
}

function extractLumaCode(message) {
  const source = [
    message && message.from,
    message && message.subject,
    message && message.preview,
    message && message.html,
    message && message.text,
    message && message.extracted_html,
    message && message.extracted_text,
  ].filter(Boolean).join("\n");
  if (!/(?:luma|lu\.ma)/i.test(source)) return null;
  const match = source.match(/(?:^|\D)(\d{6})(?:\D|$)/);
  return match ? match[1] : null;
}

function timestampMs(message) {
  const value = Date.parse(String(message && (message.timestamp || message.created_at) || ""));
  return Number.isFinite(value) ? value : 0;
}

function authenticatedSnapshotExpression() {
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
    const marker = ["create event", "my events", "manage events"].find((text) => body.includes(text)) || null;
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
        return /^(?:sign\\s*in|log\\s*in|login|email\\s+me\\s+(?:a\\s+)?link|send\\s+(?:magic\\s+)?link)$/i.test(label)
          || /(?:^|\\/)(?:login|signin|sign-in)(?:[/?#]|$)/i.test(href);
      });
    return {
      currentUrl: location.href,
      origin: location.origin,
      marker,
      confirmed: location.origin === "https://luma.com" && Boolean(marker) && !authInput && !authAction,
    };
  })()`;
}

async function requestLumaEmailLogin(page, email) {
  if (!page || typeof page.evaluate !== "function") {
    throw new LumaBootstrapError("Luma authentication unavailable");
  }
  const submitted = await page.evaluate(`(async () => {
    const input = document.querySelector('input[type="email"]');
    const submit = document.querySelector('button[type="submit"]');
    if (!input || !submit) return false;
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    if (!descriptor || typeof descriptor.set !== "function") return false;
    descriptor.set.call(input, ${JSON.stringify(email)});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 250));
    submit.click();
    return true;
  })()`);
  if (submitted !== true) throw new LumaBootstrapError("Luma authentication unavailable");
  return true;
}

async function submitLumaCode(page, code) {
  const completed = await page.evaluate(`(async () => {
    const first = document.querySelector('input[autocomplete="one-time-code"]');
    if (!first) return false;
    const scope = first.closest('form') || first.parentElement?.parentElement || document;
    const inputs = Array.from(scope.querySelectorAll('input')).filter((input) =>
      input === first || input.maxLength === 1 || input.inputMode === "numeric");
    if (inputs.length < 6) return false;
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    if (!descriptor || typeof descriptor.set !== "function") return false;
    const digits = ${JSON.stringify(code)}.split("");
    for (let index = 0; index < 6; index += 1) {
      descriptor.set.call(inputs[index], digits[index]);
      inputs[index].dispatchEvent(new Event("input", { bubbles: true }));
      inputs[index].dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return true;
  })()`);
  if (completed !== true) throw new LumaBootstrapError("Luma authentication unavailable");
}

async function completeLumaName(page, name) {
  return page.evaluate(`(async () => {
    const input = document.querySelector(
      'input[name="name"], input[type="name"], input[placeholder="Your Name"]'
    );
    if (!input) return false;
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    if (!descriptor || typeof descriptor.set !== "function") return false;
    descriptor.set.call(input, ${JSON.stringify(name)});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 250));
    const form = input.closest("form");
    const submit = form?.querySelector('button[type="submit"]')
      || document.querySelector('button[type="submit"]');
    if (!submit) return false;
    submit.click();
    return true;
  })()`);
}

function makeProductionDeps(env = process.env, boundaries = {}) {
  const { makeSteelCdpClient } = require("../lib/steel-cdp-client.js");
  const { connectCdp: defaultConnectCdp } = require("../lib/cdp-connection.js");
  const { upsertBrowserAuthSession } = require("../lib/browser-auth-session-store.js");
  const steel = boundaries.steel || makeSteelCdpClient();
  const connectCdp = boundaries.connectCdp || defaultConnectCdp;
  const fetchImpl = boundaries.fetchImpl || globalThis.fetch;
  const sleep = boundaries.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const agentMailKey = required(env.LM_AGENTMAIL_API_KEY);
  const inbox = required(env.LM_AGENTMAIL_INBOX_ID);
  const agentName = required(env.LM_AGENT_BROWSER_NAME);
  if (!agentMailKey || !inbox || !agentName) {
    throw new LumaBootstrapError("Luma bootstrap configuration unavailable");
  }

  return {
    now: () => Date.now(),
    async openBrowser() {
      const session = await steel.createRawSession({ blockAds: true });
      let page;
      try {
        page = await connectCdp(session.websocketUrl, { timeoutMs: 30_000 });
        return {
          sessionId: String(session.id),
          async requestMagicLink(email) {
            await page.navigate(LUMA_LOGIN_URL);
            await requestLumaEmailLogin(page, email);
            await sleep(2_000);
          },
          async openMagicLink(challenge) {
            if (/^luma-code:\d{6}$/.test(challenge)) {
              await submitLumaCode(page, challenge.slice("luma-code:".length));
              await sleep(3_000);
              if (await completeLumaName(page, agentName)) await sleep(3_000);
              return;
            }
            await page.navigate(challenge);
            await sleep(3_000);
          },
          async inspectAuthenticated() {
            return page.evaluate(authenticatedSnapshotExpression());
          },
          async exportContext() {
            return steel.getSessionContext(String(session.id));
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
    async readMagicLink({ afterMs }) {
      const deadline = Date.now() + 120_000;
      while (Date.now() < deadline) {
        const listResponse = await fetchImpl(
          `${AGENTMAIL_API}/inboxes/${encodeURIComponent(inbox)}/messages?limit=20`,
          { headers: { Authorization: `Bearer ${agentMailKey}` } },
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
              { headers: { Authorization: `Bearer ${agentMailKey}` } },
            );
            if (!detailResponse || !detailResponse.ok) continue;
            const detail = await detailResponse.json().catch(() => ({}));
            const link = extractMagicLink(detail);
            if (link) return link;
            const code = extractLumaCode({
              ...detail,
              from: message.from,
              subject: message.subject,
              preview: message.preview,
            });
            if (code) return `luma-code:${code}`;
          }
        }
        await sleep(3_000);
      }
      throw new LumaBootstrapError("Luma authentication unavailable");
    },
    async saveContext(input) {
      return upsertBrowserAuthSession(input);
    },
  };
}

async function resolveBootstrapEnv({ env = process.env, query } = {}) {
  const suppliedUid = required(env && env.BROWSER_AUTH_TENANT_A_UID);
  if (suppliedUid) return { ...env, BROWSER_AUTH_TENANT_A_UID: suppliedUid };
  if (typeof query !== "function") {
    throw new LumaBootstrapError("Luma bootstrap configuration unavailable");
  }
  const result = await query(`
    SELECT DISTINCT uid
    FROM public.lm_browser_auth_sessions
    WHERE origin = $1
      AND principal_kind = 'agent_owned'
    ORDER BY uid
    LIMIT 2
  `, [LUMA_ORIGIN]);
  const rows = result && Array.isArray(result.rows) ? result.rows : [];
  if (rows.length !== 1 || !required(rows[0] && rows[0].uid)) {
    throw new LumaBootstrapError("Luma bootstrap configuration unavailable");
  }
  return { ...env, BROWSER_AUTH_TENANT_A_UID: required(rows[0].uid) };
}

async function main() {
  let pool;
  try {
    let env = process.env;
    if (!required(env.BROWSER_AUTH_TENANT_A_UID)) {
      const { Pool } = require("pg");
      pool = new Pool({
        connectionString: required(env.LM_FEEDBACK_DATABASE_URL),
        max: 1,
      });
      env = await resolveBootstrapEnv({
        env,
        query: pool.query.bind(pool),
      });
    }
    const deps = makeProductionDeps(env);
    const result = await runLumaBootstrap({ env, deps });
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch {
    process.stderr.write("Luma authentication unavailable\n");
    process.exitCode = 1;
  } finally {
    if (pool) {
      try { await pool.end(); } catch {}
    }
  }
}

if (require.main === module) main();

module.exports = {
  extractLumaCode,
  extractMagicLink,
  makeProductionDeps,
  requestLumaEmailLogin,
  resolveBootstrapEnv,
  runLumaBootstrap,
  safeLumaMagicLink,
};
