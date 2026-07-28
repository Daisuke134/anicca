"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const { main } = require("./observe-ugig-work.js");

const APPLICATION_ID = "5e315cfd-33fc-433b-a5f0-3cfcdc27a9a4";
const GIG_ID = "2b410cad-7cc9-44fd-b2f1-843d9eae6c24";

test("live-shaped pending application produces a truthful zero-mutation result", async () => {
  const requests = [];
  let output = "";
  const result = await main({
    apiKey: "ugig_live_test",
    deliveries: [{
      application_id: APPLICATION_ID,
      gig_id: GIG_ID,
      amount_usd: 1,
      payment_currency: "sol",
      merchant_wallet_address: "71FfqFniYoMsWZb1qFeQDb1fk2xqvajzivpsnMb44gTf",
      category: "code",
      pr_links: ["https://github.com/profullstack/aiornot.vote/pull/100"],
      description: "RSS enclosure MIME fix",
    }],
    fetchImpl: async (url, init = {}) => {
      requests.push({ url, init });
      return {
        ok: true,
        status: 200,
        async text() {
          return JSON.stringify({
            applications: [{ id: APPLICATION_ID, gig_id: GIG_ID, status: "pending" }],
          });
        },
      };
    },
    now: () => new Date("2026-07-28T09:00:00.000Z"),
    writeOutput: (text) => { output += text; },
  });

  assert.equal(result.pending, 1);
  assert.equal(result.invoice_created, 0);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, "https://ugig.net/api/applications/my");
  assert.equal(requests[0].init.headers.authorization, "Bearer ugig_live_test");
  assert.doesNotMatch(output, /ugig_live_test/);
});

test("launchd wiring is a separate five-minute loop and never stops existing loops", () => {
  const root = join(__dirname, "..");
  const boot = readFileSync(join(__dirname, "ugig-invoice-observer-boot.sh"), "utf8");
  const installer = readFileSync(join(__dirname, "install-ugig-invoice-observer-launchd.sh"), "utf8");
  const plist = readFileSync(
    join(root, "launchd", "ai.anicca.life-manager-ugig-invoice-observer.plist.template"),
    "utf8",
  );

  assert.match(boot, /observe-ugig-work\.js/);
  assert.match(boot, /UGIG_API_KEY_FILE/);
  assert.match(boot, /timeout 180/);
  assert.match(installer, /ai\.anicca\.life-manager-ugig-invoice-observer/);
  assert.doesNotMatch(installer, /bootout|unload|kickstart\s+-k/);
  assert.match(plist, /<integer>300<\/integer>/);
  assert.match(plist, /ugig-invoice-observer-boot\.sh/);
});

