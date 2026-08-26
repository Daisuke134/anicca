"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createConnpassActionTelegram } = require("./connector-connpass-action-telegram.js");

function candidate(overrides = {}) {
  return {
    provider: "connpass",
    event_ref: "connpass-event://event/901",
    canonical_url: "https://tokyo-ai.connpass.com/event/901/",
    title: "Tokyo AI Builders LT",
    participation_slot_status: "available",
    lightning_talk_status: "unknown",
    participant_limit: 100,
    accepted_count: 20,
    waiting_count: 0,
    application_deadline_at: null,
    priority_class: "ai",
    preference_reason: "AI buildersとの接点に合います。",
    ...overrides,
  };
}

test("connpass action boundary sends normalized candidate fields and persists a positive provider receipt", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connpass-action-telegram-"));
  const sent = [];
  try {
    const reporter = createConnpassActionTelegram({
      stateDir, wakeId: "wake-connpass-1", telegramTarget: "private-target",
      now: () => new Date("2026-08-27T01:00:00.000Z"),
      send: async (message, options) => { sent.push({ message, options }); return { messageId: "7711" }; },
    });
    const result = await reporter.report({ candidates: [candidate()] });
    assert.equal(result.telegram_provider_id, "7711");
    assert.match(sent[0].message, /参加枠: available/);
    assert.match(sent[0].message, /LT: unknown/);
    assert.match(sent[0].message, /補欠: 0人/);
    assert.match(sent[0].message, /締切: provider未提供/);
    assert.match(sent[0].message, /https:\/\/tokyo-ai\.connpass\.com\/event\/901\//);
    assert.match(sent[0].message, /自動申込: 0件/);
    assert.match(sent[0].message, /理由: AI buildersとの接点/);
    const rows = fs.readFileSync(path.join(stateDir, "connpass-action-boundary-deliveries.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].telegram_provider_id, "7711");
    assert.doesNotMatch(JSON.stringify(rows), /private-target|api.?key|cookie|password/i);
    const reused = await reporter.report({ candidates: [candidate()] });
    assert.equal(reused.completion_disposition, "reused");
    assert.equal(sent.length, 1);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("missing provider message ID and malformed candidate never write a receipt", async () => {
  for (const candidates of [[candidate()], [candidate({ canonical_url: "https://evil.example/event/901/" })]]) {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connpass-action-reject-"));
    try {
      const reporter = createConnpassActionTelegram({
        stateDir, wakeId: "wake-connpass-reject", telegramTarget: "private-target",
        now: () => new Date("2026-08-27T01:00:00.000Z"), send: async () => ({}),
      });
      await assert.rejects(reporter.report({ candidates }));
      assert.equal(fs.existsSync(path.join(stateDir, "connpass-action-boundary-deliveries.jsonl")), false);
    } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
  }
});

test("public crypto token language is allowed while credential token language is rejected", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connpass-action-crypto-"));
  try {
    const messages = [];
    const reporter = createConnpassActionTelegram({
      stateDir, wakeId: "wake-connpass-crypto", telegramTarget: "private-target",
      now: () => new Date("2026-08-27T01:00:00.000Z"),
      send: async (message) => { messages.push(message); return { messageId: "7722" }; },
    });
    const result = await reporter.report({ candidates: [candidate({
      title: "API Key and Secret Management",
      preference_reason: "Passwordless auth, cookie security, and access tokens are public event topics.",
    })] });
    assert.equal(result.telegram_provider_id, "7722");
    assert.match(messages[0], /Secret Management/);

    await assert.rejects(reporter.report({ candidates: [candidate({
      event_ref: "connpass-event://event/902",
      canonical_url: "https://tokyo-ai.connpass.com/event/902/",
      preference_reason: `access_${"tok"}${"en="}${"0123456789abcdef"}`,
    })] }));
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("action boundary truncates a valid ranked title only for Telegram display", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connpass-action-title-"));
  try {
    let delivered = "";
    const reporter = createConnpassActionTelegram({
      stateDir, wakeId: "wake-connpass-title", telegramTarget: "private-target",
      now: () => new Date("2026-08-27T01:00:00.000Z"),
      send: async (message) => { delivered = message; return { messageId: "7733" }; },
    });
    const result = await reporter.report({ candidates: [candidate({ title: "t".repeat(200) })] });
    assert.equal(result.telegram_provider_id, "7733");
    assert.match(delivered, new RegExp(`1\\. ${"t".repeat(160)}\\n`));
    assert.doesNotMatch(delivered, new RegExp("t".repeat(161)));
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});
