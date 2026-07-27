"use strict";

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const { main, parseArgs, publicResult } = require("./run-financial-reports.js");

test("--uid is mandatory and force is bounded to one known report mode", () => {
  assert.deepEqual(parseArgs(["--uid", "u1"]), { uid: "u1", force: null });
  assert.deepEqual(parseArgs(["--uid", "u1", "--force", "daily"]), { uid: "u1", force: "daily" });
  assert.deepEqual(parseArgs(["--uid", "u1", "--force", "all"]), { uid: "u1", force: "all" });
  assert.throws(() => parseArgs([]), /--uid/i);
  assert.throws(() => parseArgs(["--uid", "u1", "--force", "monthly"]), /--force/i);
});

test("CLI checks daily and weekly through the real runtime seam and prints only bounded receipts", async () => {
  const calls = [];
  const output = [];
  const results = await main(["--uid", "u1", "--force", "daily"], {
    BASE_RPC_URL: "https://base.example",
    LM_FINANCIAL_REPORT_RESERVE_USDC_ATOMIC: "46000000",
  }, {
    nowMs: Date.parse("2026-08-02T11:05:00Z"),
    runReport: async (request, runtimeDeps) => {
      calls.push({ request, runtimeDeps });
      return request.kind === "daily"
        ? {
          status: "sent",
          report_kind: "daily",
          period_key: "2026-08-02",
          telegram_message_id: 77,
          snapshot_hash: "a".repeat(64),
          snapshot: { wallet_address: "must-not-print" },
        }
        : { status: "skipped", reason: "not_due", report_kind: "weekly" };
    },
    readBalance: async () => "0",
    stdout: { write: (text) => output.push(text) },
  });

  assert.equal(calls.length, 2);
  assert.equal(calls[0].request.force, true);
  assert.equal(calls[1].request.force, false);
  assert.equal(calls[0].request.reserveAtomic, "46000000");
  assert.equal(await calls[0].runtimeDeps.readBalance("0xwallet"), "0");
  assert.deepEqual(JSON.parse(output.join("")), results.map(publicResult));
  assert.doesNotMatch(output.join(""), /wallet_address|must-not-print|token|supabase|u1/i);
});

test("one report failure is bounded and does not prevent the other due check", async () => {
  const output = [];
  const results = await main(["--uid", "u1"], {}, {
    runReport: async (request) => {
      if (request.kind === "daily") throw new Error("secret provider detail");
      return { status: "duplicate", report_kind: "weekly", period_key: "2026-W31" };
    },
    readBalance: async () => "0",
    stdout: { write: (text) => output.push(text) },
  });

  assert.equal(results[0].status, "failed");
  assert.equal(results[0].reason, "report_failed");
  assert.equal(results[1].status, "duplicate");
  assert.doesNotMatch(output.join(""), /secret provider detail/);
});

test("launchd report wiring is bounded, five-minute, and prints only safe status lines", () => {
  const boot = readFileSync(join(__dirname, "financial-report-boot.sh"), "utf8");
  const installer = readFileSync(join(__dirname, "install-financial-report-launchd.sh"), "utf8");
  const plist = readFileSync(join(
    __dirname,
    "..",
    "launchd",
    "ai.anicca.life-manager-financial-report.plist.template",
  ), "utf8");

  assert.match(boot, /\/opt\/homebrew\/bin\/timeout 240 \/opt\/homebrew\/bin\/node/);
  assert.doesNotMatch(boot, /(?:^|[;&|]\s*)timeout\s/);
  assert.match(boot, /\.openclaw\/\.env/);
  assert.match(plist, /<string>\/bin\/bash<\/string>/);
  assert.match(plist, /<key>StartInterval<\/key>\s*<integer>300<\/integer>/);
  assert.match(plist, /life-manager-financial-report\.out\.log/);
  assert.match(installer, /plutil -lint/);
  assert.match(installer, /launchctl bootstrap/);
  assert.match(installer, /launchctl enable/);
  assert.match(installer, /launchctl print[^|]+\|\s*\/usr\/bin\/grep/);
  assert.doesNotMatch(installer, /launchctl print "\$DOMAIN\/\$LABEL"\s*$/m);
});
