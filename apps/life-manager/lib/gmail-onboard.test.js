"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { signedGmailConnectUrl, createHostedGmailLink } = require("./gmail-onboard.js");

test("signedGmailConnectUrl creates a life-call deep link with a server-verifiable uid signature", () => {
  const url = new URL(signedGmailConnectUrl("lm_u1", "https://life.example/", "secret"));
  assert.equal(url.origin + url.pathname, "https://life.example/gmail-connect");
  assert.equal(url.searchParams.get("uid"), "lm_u1");
  assert.ok(url.searchParams.get("sig"));
});

test("createHostedGmailLink wires the existing Unipile Gmail hosted-auth flow", async () => {
  let call;
  const url = await createHostedGmailLink("lm_u1", {
    dsn: "api.example", token: "token", notifySecret: "notify", publicBase: "https://aniccaai.com",
    nowMs: Date.parse("2026-07-18T00:00:00Z"),
    fetchImpl: async (requestUrl, opts) => { call = { requestUrl, opts }; return { ok: true, json: async () => ({ url: "https://auth.unipile.example/x" }) }; },
  });
  assert.equal(url, "https://auth.unipile.example/x");
  assert.equal(call.requestUrl, "https://api.example/api/v1/hosted/accounts/link");
  const body = JSON.parse(call.opts.body);
  assert.deepEqual(body.providers, ["GOOGLE"]);
  assert.equal(body.name, "lm_u1");
  assert.match(body.notify_url, /unipile-notify\?s=notify$/);
  assert.equal(body.success_redirect_url, "https://aniccaai.com/lm?gmail=connected");
});

test("createHostedGmailLink returns null when unavailable and never fakes success", async () => {
  assert.equal(await createHostedGmailLink("lm_u1", {}), null);
  assert.equal(await createHostedGmailLink("lm_u1", {
    dsn: "d", token: "t", notifySecret: "n", fetchImpl: async () => { throw new Error("offline"); },
  }), null);
});
