"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  generateEventTalkProposal,
  validateEventTalkProposal,
} = require("./event-talk-proposal.js");

const SOURCE = Object.freeze({
  event: {
    title: "AI Agent Night",
    audience: "AIプロダクトを作るエンジニア",
    talk_format: "5分LT",
    duration_seconds: 300,
    requirements: "動くプロダクトのデモを含めること。",
  },
  facts: [
    {
      id: "registry_16",
      claim: "Life Managerの正本registryには16個のagent roleがある。",
      evidence_ref: "docs/evidence/agent-registry/2026-08-01-agent-registry-verification.md",
    },
    {
      id: "real_registration",
      claim: "Life Managerは実イベントEngineer BARへ1回だけ登録し、予定と往復移動をCalendarへ保存した。",
      evidence_ref: "docs/evidence/outbound/2026-08-01-o1b04-live-luma-registration.json",
    },
    {
      id: "ticket_delivery",
      claim: "同じ登録の公式QRを確認メールへ結び、Telegramへ1回配信した。",
      evidence_ref: "docs/evidence/outbound/2026-08-01-o1b07-live-telegram-ticket-delivery.json",
    },
  ],
});

function proposal(overrides = {}) {
  return {
    talk_title: "16のagentを束ね、イベント参加を最後まで終わらせるLife Manager",
    application_reason: "単なる構想ではなく、実イベント登録からCalendar、公式QRのTelegram配信まで動く流れを5分で実演できるためです。",
    outline: [
      { start_second: 0, end_second: 30, heading: "課題", demo_action: "散らばる生活タスクを一つのchatへ集めます。", evidence_ids: ["registry_16"] },
      { start_second: 30, end_second: 90, heading: "司令塔", demo_action: "16のagent roleを持つ正本registryを見せます。", evidence_ids: ["registry_16"] },
      { start_second: 90, end_second: 180, heading: "実行", demo_action: "Engineer BARを選び、重複せず登録した実測結果を見せます。", evidence_ids: ["real_registration"] },
      { start_second: 180, end_second: 240, heading: "生活へ接続", demo_action: "イベントと往復移動がCalendarへ入った結果を見せます。", evidence_ids: ["real_registration"] },
      { start_second: 240, end_second: 300, heading: "完了", demo_action: "確認メールに結び付いた公式QRがTelegramへ届くところまで見せます。", evidence_ids: ["ticket_delivery"] },
    ],
    ...overrides,
  };
}

test("実測factへ追跡できる連続300秒のproposalだけを受理する", () => {
  const actual = validateEventTalkProposal(proposal(), SOURCE);
  assert.deepEqual(actual, proposal());
  assert.equal(Object.isFrozen(actual), true);
  assert.equal(Object.isFrozen(actual.outline), true);
});

test("時間の隙間・未知evidence・未検証の数値・placeholderを拒否する", () => {
  assert.throws(() => validateEventTalkProposal(proposal({
    outline: proposal().outline.map((step, index) => index === 1 ? { ...step, start_second: 31 } : step),
  }), SOURCE), /timeline/i);
  assert.throws(() => validateEventTalkProposal(proposal({
    outline: proposal().outline.map((step, index) => index === 0 ? { ...step, evidence_ids: ["invented"] } : step),
  }), SOURCE), /evidence/i);
  assert.throws(() => validateEventTalkProposal(proposal({
    application_reason: "100人の利用者がいるので応募します。",
  }), SOURCE), /number/i);
  assert.throws(() => validateEventTalkProposal(proposal({ talk_title: "TODO: タイトル" }), SOURCE), /title/i);
});

test("余分なfieldと危険なevidence pathを拒否する", () => {
  assert.throws(() => validateEventTalkProposal({ ...proposal(), score: 1 }, SOURCE), /schema/i);
  assert.throws(() => validateEventTalkProposal(proposal(), {
    ...SOURCE,
    facts: [{ ...SOURCE.facts[0], evidence_ref: "../../secret.env" }, ...SOURCE.facts.slice(1)],
  }), /source evidence/i);
});

test("Geminiへイベントとfactsをuntrusted dataとして渡しstructured outputを検証する", async () => {
  let request;
  const actual = await generateEventTalkProposal(SOURCE, {
    apiKey: "fixture-key",
    fetchImpl: async (url, options) => {
      request = { url, options, body: JSON.parse(options.body) };
      return {
        ok: true,
        json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(proposal()) }] } }] }),
      };
    },
  });
  assert.deepEqual(actual, proposal());
  assert.match(request.url, /gemini-2\.5-flash:generateContent/);
  assert.equal(request.options.headers["x-goog-api-key"], "fixture-key");
  const prompt = request.body.contents[0].parts[0].text;
  assert.match(prompt, /untrusted data/i);
  assert.match(prompt, /registry_16/);
  assert.match(prompt, /0.*300/s);
  assert.equal(request.body.generationConfig.responseMimeType, "application/json");
});

test("API failureやinvalid JSONをfallbackで成功扱いしない", async () => {
  await assert.rejects(generateEventTalkProposal(SOURCE, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({ ok: false, status: 503 }),
  }), /failed/i);
  await assert.rejects(generateEventTalkProposal(SOURCE, {
    apiKey: "fixture-key",
    fetchImpl: async () => ({ ok: true, json: async () => ({ candidates: [{ content: { parts: [{ text: "no" }] } }] }) }),
  }), /invalid JSON/i);
});
