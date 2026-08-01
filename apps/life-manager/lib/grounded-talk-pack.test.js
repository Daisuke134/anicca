"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { generateGroundedTalkPack, validateGroundedTalkPack } = require("./grounded-talk-pack.js");

const INPUT = Object.freeze({
  event: {
    canonicalUrl: "https://luma.com/p9kfepcf",
    title: "Codex Meetup Tokyo #2",
    body: "Codexの実践とContributeを共有します。5分LT希望者を募集しています。",
    now: "2026-08-02T00:00:00.000Z",
  },
  facts: [
    { evidence_ref: "evidence://connector/o1b04", fact: "実Lumaイベント1件の参加登録とCalendar登録を照合した。" },
    { evidence_ref: "evidence://connector/o1b07", fact: "同じイベントのQRをTelegramへ送り、positive message IDを確認した。" },
    { evidence_ref: "evidence://connector/o1b12", fact: "一般参加とLT応募を別entityとして実runtime DBへ保存した。" },
  ],
});

function validPack() {
  return {
    title: "Codexで作る、証拠付き自律イベントConnector",
    abstract: "検索だけで終わらず、参加登録、確認、Calendar、QR、Telegramまでを証拠で結ぶ実装を紹介します。",
    application_reason: "Codexの実装事例を共有する5分LTに合い、失敗を成功と表示しない設計を具体的に示せるためです。",
    product_demo_summary: "実Luma登録からCalendarとTelegramのQR通知まで、同一イベントとして照合した流れを見せます。",
    outline: [
      { start_second: 0, end_second: 45, heading: "問題", content: "検索件数ではなく、現実に参加できる状態を作る必要がありました。", evidence_refs: ["evidence://connector/o1b04"] },
      { start_second: 45, end_second: 120, heading: "実装", content: "Codexでdurable jobと証拠境界を実装しました。", evidence_refs: ["evidence://connector/o1b04"] },
      { start_second: 120, end_second: 210, heading: "デモ", content: "登録、Calendar、QR、Telegramが同じイベントへ繋がる実測を示します。", evidence_refs: ["evidence://connector/o1b04", "evidence://connector/o1b07"] },
      { start_second: 210, end_second: 265, heading: "分離", content: "一般参加とLT応募を別entityにして誤報告を防ぎました。", evidence_refs: ["evidence://connector/o1b12"] },
      { start_second: 265, end_second: 300, heading: "学び", content: "agentの成功条件を人の行動に結び直した学びで締めます。", evidence_refs: ["evidence://connector/o1b12"] },
    ],
  };
}

test("accepts an exact 300-second pack grounded segment-by-segment in supplied evidence", () => {
  const pack = validateGroundedTalkPack(validPack(), INPUT);
  assert.deepEqual(pack, validPack());
  assert.equal(Object.isFrozen(pack), true);
  assert.equal(pack.outline.at(-1).end_second, 300);
});

test("rejects gaps, overlaps, unknown evidence, placeholders, secrets, and wealth promises", () => {
  const mutations = [
    p => { p.outline[1].start_second = 46; },
    p => { p.outline[1].start_second = 44; },
    p => { p.outline[0].evidence_refs = ["evidence://connector/invented"]; },
    p => { p.title = "TODO: title"; },
    p => { p.abstract = "contact me at person@example.com"; },
    p => { p.product_demo_summary = "誰でも必ず億万長者にします"; },
  ];
  for (const mutate of mutations) {
    const pack = structuredClone(validPack());
    mutate(pack);
    assert.throws(() => validateGroundedTalkPack(pack, INPUT), /talk pack/i);
  }
});

test("generator sends event text as untrusted data and facts as the only claim source", async () => {
  let request;
  const pack = await generateGroundedTalkPack(INPUT, {
    apiKey: "fixture-key",
    async fetchImpl(url, options) {
      request = { url, options, body: JSON.parse(options.body) };
      return { ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(validPack()) }] } }] }) };
    },
  });
  assert.deepEqual(pack, validPack());
  const prompt = request.body.contents[0].parts[0].text;
  assert.match(prompt, /untrusted/i);
  assert.match(prompt, /only claim source/i);
  assert.match(prompt, /evidence:\/\/connector\/o1b12/);
  assert.equal(request.body.generationConfig.responseMimeType, "application/json");
  assert.equal(request.body.generationConfig.temperature, 0);
});

test("model failure and invalid JSON never fall back to an invented talk", async () => {
  await assert.rejects(generateGroundedTalkPack(INPUT, { apiKey: "fixture", fetchImpl: async () => ({ ok: false, status: 503 }) }), /unavailable/i);
  await assert.rejects(generateGroundedTalkPack(INPUT, { apiKey: "fixture", fetchImpl: async () => ({ ok: true, status: 200, json: async () => ({ candidates: [{ content: { parts: [{ text: "bad" }] } }] }) }) }), /unavailable/i);
});
