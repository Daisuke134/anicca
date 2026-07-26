// INC-3: the prod webhook was found empty (inbound dead while outbound looked healthy), and the
// re-registration then failed on a truncated secret (INC-1's class). The permanent fix registers
// the webhook from the runtime itself at boot: the secret Telegram echoes and the secret the
// server compares are the same process.env value by construction — neither can drift.
// Run: node --test lib/webhook-selfheal.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { selfHealWebhook } = require("./webhook-selfheal.js");

const ENV = {
  LM_TELEGRAM_BOT_TOKEN: "42:token",
  LM_TELEGRAM_WEBHOOK_SECRET: "s".repeat(64),
  LM_PUBLIC_URL: "https://life-call-production.up.railway.app",
};

function fakeFetch(replies) {
  const calls = [];
  return {
    calls,
    fetch: async (url, init) => {
      calls.push({ url: String(url), init });
      const reply = replies.shift() || { ok: true, result: {} };
      return { ok: true, json: async () => reply };
    },
  };
}

test("registers url + full runtime secret + U4 allowed_updates when webhook is absent", async () => {
  const f = fakeFetch([
    { ok: true, result: { url: "" } },                    // getWebhookInfo: empty
    { ok: true, result: true, description: "Webhook was set" }, // setWebhook
  ]);
  const out = await selfHealWebhook(ENV, { fetchImpl: f.fetch });
  assert.equal(out.healed, true);
  const set = f.calls.find((c) => c.url.includes("/setWebhook"));
  assert.ok(set, "setWebhook was called");
  const body = String(set.init.body);
  assert.ok(body.includes(encodeURIComponent("https://life-call-production.up.railway.app/telegram")), "webhook path is /telegram");
  assert.ok(body.includes("s".repeat(64)), "the FULL runtime secret is sent, never a truncation");
  for (const kind of ["message", "edited_message", "callback_query"]) {
    assert.ok(body.includes(kind), `allowed_updates carries ${kind} (U4)`);
  }
});

test("does nothing when the registration already matches", async () => {
  const f = fakeFetch([
    { ok: true, result: { url: "https://life-call-production.up.railway.app/telegram", allowed_updates: ["message", "edited_message", "callback_query"] } },
  ]);
  const out = await selfHealWebhook(ENV, { fetchImpl: f.fetch });
  assert.equal(out.healed, false);
  assert.equal(out.reason, "already-registered");
  assert.ok(!f.calls.some((c) => c.url.includes("/setWebhook")), "no redundant setWebhook");
});

test("re-registers when the url points somewhere else", async () => {
  const f = fakeFetch([
    { ok: true, result: { url: "https://old-host.example/telegram" } },
    { ok: true, result: true },
  ]);
  const out = await selfHealWebhook(ENV, { fetchImpl: f.fetch });
  assert.equal(out.healed, true);
});

test("fails closed loudly when token or secret is missing — never registers a blank secret", async () => {
  const f = fakeFetch([]);
  const out = await selfHealWebhook({ ...ENV, LM_TELEGRAM_WEBHOOK_SECRET: "" }, { fetchImpl: f.fetch });
  assert.equal(out.healed, false);
  assert.match(out.reason, /secret/i);
  assert.equal(f.calls.length, 0, "no Telegram call without a secret");
});

test("a Telegram error is reported, not swallowed as success", async () => {
  const f = fakeFetch([
    { ok: true, result: { url: "" } },
    { ok: false, description: "Unauthorized" },
  ]);
  const out = await selfHealWebhook(ENV, { fetchImpl: f.fetch });
  assert.equal(out.healed, false);
  assert.match(out.reason, /Unauthorized/);
});
