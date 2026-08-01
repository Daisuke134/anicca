const { test } = require("node:test");
const assert = require("node:assert/strict");

const { makeMarketingGoHandler, makeSupabasePersist } = require("../marketing-go");

const products = {
  ai: { productId: "aniccaios", kind: "app", appId: "6755129214" },
  ho: { productId: "honne", kind: "app", appId: "6759667221" },
  ej: { productId: "ebook-ja", kind: "web", path: "/achan" },
  ee: { productId: "ebook-en", kind: "web", path: "/monk" },
};

function event(token, method = "GET") {
  return {
    httpMethod: method,
    path: `/go/${token}`,
    rawUrl: `https://aniccaai.com/go/${token}`,
  };
}

test("persists a minimal click receipt before redirecting an app campaign", async () => {
  const writes = [];
  const handler = makeMarketingGoHandler({
    products,
    providerToken: "123456",
    now: () => "2026-08-01T00:00:00.000Z",
    receiptId: () => "click-1",
    persist: async (key, value) => writes.push([key, value]),
  });
  const token = "ai_abcdefghijklmnopqrst";
  const response = await handler(event(token));
  assert.equal(response.statusCode, 302);
  assert.match(response.headers.location, /apps\.apple\.com\/app\/id6755129214/);
  assert.match(response.headers.location, new RegExp(`ct=${token}`));
  assert.equal(response.headers["x-click-receipt"], "click-1");
  assert.deepEqual(writes, [["clicks/click-1", {
    schema_version: 1,
    receipt_id: "click-1",
    campaign_token: token,
    product_id: "aniccaios",
    clicked_at: "2026-08-01T00:00:00.000Z",
  }]]);
});

test("routes ebook tokens only to their fixed product page", async () => {
  const handler = makeMarketingGoHandler({
    products,
    providerToken: "123456",
    receiptId: () => "click-2",
    persist: async () => {},
  });
  const token = "ej_abcdefghijklmnopqrst";
  const response = await handler(event(token));
  assert.equal(response.statusCode, 302);
  assert.equal(
    response.headers.location,
    `https://aniccaai.com/achan?utm_source=social&utm_medium=owned_redirect&utm_campaign=${token}`,
  );
});

test("rejects invalid tokens and non-GET methods without writing", async () => {
  let writes = 0;
  const handler = makeMarketingGoHandler({
    products,
    providerToken: "123456",
    persist: async () => { writes += 1; },
  });
  assert.equal((await handler(event("ai_bad"))).statusCode, 404);
  assert.equal((await handler(event("ai_abcdefghijklmnopqrst", "POST"))).statusCode, 405);
  assert.equal(writes, 0);
});

test("storage failure returns 503 and never emits a redirect", async () => {
  const handler = makeMarketingGoHandler({
    products,
    providerToken: "123456",
    persist: async () => { throw new Error("blob unavailable"); },
  });
  const response = await handler(event("ee_abcdefghijklmnopqrst"));
  assert.equal(response.statusCode, 503);
  assert.equal(response.headers.location, undefined);
  assert.doesNotMatch(response.body, /blob unavailable/);
});

test("receipt excludes IP, user agent, referrer, cookies, and raw query", async () => {
  let receipt;
  const handler = makeMarketingGoHandler({
    products,
    providerToken: "123456",
    receiptId: () => "click-3",
    persist: async (_key, value) => { receipt = value; },
  });
  const input = event("ho_abcdefghijklmnopqrst");
  input.headers = {
    "x-forwarded-for": "203.0.113.5",
    "user-agent": "private-agent",
    referer: "https://private.example/",
    cookie: "private-cookie",
  };
  input.rawQuery = "secret=private";
  await handler(input);
  const serialized = JSON.stringify(receipt);
  for (const privateValue of ["203.0.113.5", "private-agent", "private.example", "private-cookie", "secret"])
    assert.equal(serialized.includes(privateValue), false);
});

test("Supabase persistence writes only the receipt to the locked table", async () => {
  let request;
  const persist = makeSupabasePersist({
    url: "https://project.supabase.co",
    serviceKey: "service-secret",
    fetchImpl: async (url, options) => {
      request = { url, options };
      return { ok: true, status: 201 };
    },
  });
  const receipt = {
    schema_version: 1,
    receipt_id: "00000000-0000-4000-8000-000000000001",
    campaign_token: "ee_abcdefghijklmnopqrst",
    product_id: "ebook-en",
    clicked_at: "2026-08-01T00:00:00.000Z",
  };
  await persist("ignored", receipt);
  assert.equal(request.url, "https://project.supabase.co/rest/v1/marketing_click_receipts");
  assert.equal(request.options.method, "POST");
  assert.deepEqual(JSON.parse(request.options.body), receipt);
  assert.equal(request.options.headers.apikey, "service-secret");
  assert.equal(request.options.headers.Authorization, "Bearer service-secret");
  assert.equal(request.options.headers.Prefer, "return=minimal");
});

test("Supabase persistence fails closed without leaking its key", async () => {
  const persist = makeSupabasePersist({
    url: "https://project.supabase.co",
    serviceKey: "service-secret",
    fetchImpl: async () => ({ ok: false, status: 503 }),
  });
  await assert.rejects(
    persist("ignored", { receipt_id: "x" }),
    (error) => error.message.includes("503") && !error.message.includes("service-secret"),
  );
});
