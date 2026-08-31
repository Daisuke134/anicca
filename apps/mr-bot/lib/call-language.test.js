"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { langForPhone, openingTurnForLang, resolveCallLang } = require("./call-language.js");
const { buildCallPrompt } = require("./call-logic.js");

test("langForPhone maps +81 to ja", () => {
  assert.equal(langForPhone("+81 90-1234-5678"), "ja");
});

test("langForPhone maps +1 to en", () => {
  assert.equal(langForPhone("+1 (415) 555-0100"), "en");
});

test("langForPhone defaults unknown numbers to en", () => {
  assert.equal(langForPhone(undefined), "en");
  assert.equal(langForPhone("not-a-phone"), "en");
});

test("resolveCallLang prioritizes an explicit Japanese language", () => {
  assert.equal(resolveCallLang({ callLanguage: "ja", phone: "+1 415-555-0100" }), "ja");
});

test("resolveCallLang prioritizes an explicit English language", () => {
  assert.equal(resolveCallLang({ callLanguage: "en", phone: "+81 90-1234-5678" }), "en");
});

test("resolveCallLang infers Japanese from an +81 phone when language is unset", () => {
  assert.equal(resolveCallLang({ phone: "+81 90-1234-5678" }), "ja");
});

test("resolveCallLang infers English from a +1 phone when language is unset", () => {
  assert.equal(resolveCallLang({ phone: "+1 415-555-0100" }), "en");
});

test("resolveCallLang defaults to English when language and phone are absent", () => {
  assert.equal(resolveCallLang({}), "en");
});

test("resolveCallLang falls back to phone inference for an invalid language", () => {
  assert.equal(resolveCallLang({ callLanguage: "fr", phone: "+81 90-1234-5678" }), "ja");
});

test("Japanese calls receive a Japanese opening turn", () => {
  assert.equal(openingTurnForLang("ja"), "最初の一言から日本語で通話を始めてください。");
  assert.equal(openingTurnForLang("en"), "Begin the call now with your opening line.");
});

test("Japanese system instruction requires Japanese first and permits user-led switching", () => {
  const prompt = buildCallPrompt({ summary: "歯医者" }, "gentle", "ja", "太郎");
  assert.match(prompt, /lang=ja/);
  assert.match(prompt, /最初の挨拶から日本語のみ/);
  assert.match(prompt, /相手が別の言語で話しかけた場合/);
  assert.doesNotMatch(prompt, /100% 日本語/);
});
