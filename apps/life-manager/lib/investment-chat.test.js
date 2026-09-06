"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { ALPACA_SIGNUP_URL, buildInvestmentReply, telegramExtra } = require("./investment-chat.js");

test("setup_required renders the canonical signup copy and portable buttons", () => {
  const reply = buildInvestmentReply({ lifecycle: "setup_required" });
  assert.match(reply.text, /^Investment Loop\n/);
  assert.deepEqual(reply.presentation.blocks[0].buttons, [
    { label: "Alpacaで口座開設する", url: ALPACA_SIGNUP_URL },
    { label: "今はしない", action: { type: "callback", value: "invest:later" } },
  ]);
  assert.deepEqual(telegramExtra(reply), { parse_mode: undefined, reply_markup: { inline_keyboard: [[
    { text: "Alpacaで口座開設する", url: ALPACA_SIGNUP_URL },
    { text: "今はしない", callback_data: "invest:later" },
  ]] } });
});

test("in_review renders balance, decision, and natural-language reason", () => {
  const reply = buildInvestmentReply({
    lifecycle: "in_review",
    account: { equity: "99996.76", cash: "99996.76" },
    decision: { approved: false, reason: "No fresh edge." },
  });
  assert.match(reply.text, /審査中/);
  assert.match(reply.text, /資産 \$99996\.76/);
  assert.match(reply.text, /取引なし/);
  assert.match(reply.text, /No fresh edge\./);
  assert.equal(reply.presentation, undefined);
});

test("unknown lifecycle and missing balances fail closed", () => {
  const reply = buildInvestmentReply(null);
  assert.match(reply.text, /状態をまだ確認できません/);
  assert.match(reply.text, /ライブ注文は出しません/);
  assert.match(reply.text, /最新状態をまだ読み取れません/);
});

test("missing decision never becomes a trade candidate", () => {
  const reply = buildInvestmentReply({ lifecycle: "in_review", account: { equity: "1", cash: "1" } });
  assert.match(reply.text, /今回の判断は未確認/);
  assert.doesNotMatch(reply.text, /取引候補あり/);
});

test("malformed nested account values never look operational or trade-ready", () => {
  for (const value of [null, {}, [], "", "not-money", "0x10", Infinity]) {
    const reply = buildInvestmentReply({
      lifecycle: "in_review", account: { equity: value, cash: value }, decision: { approved: true },
    });
    assert.match(reply.text, /最新状態をまだ読み取れません/);
    assert.doesNotMatch(reply.text, /取引候補あり/);
  }
});

test("malformed lifecycle and decision never become live or trade-ready", () => {
  const lifecycle = buildInvestmentReply({ lifecycle: ["active"] });
  assert.match(lifecycle.text, /ライブ注文は出しません/);
  assert.doesNotMatch(lifecycle.text, /承認済み/);
  const decision = buildInvestmentReply({
    lifecycle: "in_review", account: { equity: "1", cash: "1" },
    decision: { approved: true, reason: {} },
  });
  assert.match(decision.text, /今回の判断は未確認/);
  assert.doesNotMatch(decision.text, /取引候補あり|\[object Object\]/);
  assert.doesNotMatch(buildInvestmentReply({
    lifecycle: "in_review", account: { equity: "1", cash: "1" }, decision: { approved: true },
  }).text, /取引候補あり/);
});

test("every provider lifecycle keeps live submission fail closed", () => {
  assert.match(buildInvestmentReply({ lifecycle: "active" }).text, /リスク上限を確認するまでライブ注文は出しません/);
  assert.match(buildInvestmentReply({ lifecycle: "action_required" }).text, /追加対応が必要/);
  assert.match(buildInvestmentReply({ lifecycle: "rejected" }).text, /追加対応が必要/);
});
