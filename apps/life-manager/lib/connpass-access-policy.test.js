"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  createConnpassAccessPolicy,
} = require("./connpass-access-policy.js");

const REQUEST = {
  trigger: "scheduled_cache",
  prefecture: "tokyo",
  keywords: ["AI", "生成AI", "LLM", "Web3"],
  retentionDays: 30,
  minIntervalMs: 5_000,
};

test("API key未発行中はrequestを作らずdisabledにする", () => {
  const policy = createConnpassAccessPolicy({ apiKeyRef: "" });

  assert.deepEqual(policy.planEventDiscovery(REQUEST), {
    status: "disabled",
    reason: "api_key_unavailable",
  });
});

test("scheduled self cache用のofficial v2 GETだけをreference-onlyで作る", () => {
  const policy = createConnpassAccessPolicy({
    apiKeyRef: "secret://connpass/api-key",
  });
  const result = policy.planEventDiscovery(REQUEST);

  assert.equal(result.status, "ready");
  assert.equal(result.method, "GET");
  assert.equal(result.origin, "https://connpass.com");
  assert.equal(result.path, "/api/v2/events/");
  assert.equal(result.query.prefecture, "tokyo");
  assert.equal(result.query.count, "100");
  assert.equal(result.header.name, "X-API-Key");
  assert.equal(result.header.value_ref, "secret://connpass/api-key");
  assert.equal(JSON.stringify(result).includes("CPa"), false);
});

test("user trigger、Tokyo外、5秒未満、長期保存、壊れたsecret refを拒否する", () => {
  const policy = createConnpassAccessPolicy({ apiKeyRef: "secret://connpass/api-key" });

  for (const patch of [
    { trigger: "user_search" },
    { prefecture: "online" },
    { minIntervalMs: 4_999 },
    { retentionDays: 31 },
    { keywords: [] },
  ]) {
    assert.throws(
      () => policy.planEventDiscovery({ ...REQUEST, ...patch }),
      /connpass access policy violation/,
    );
  }
  assert.throws(
    () => createConnpassAccessPolicy({ apiKeyRef: "plaintext-key" }),
    /connpass access policy violation/,
  );
});

test("policyはbrowser、scrape、RSVP operationを公開しない", () => {
  const policy = createConnpassAccessPolicy({ apiKeyRef: "secret://connpass/api-key" });

  assert.deepEqual(Object.keys(policy), ["planEventDiscovery"]);
});
