"use strict";

const { createHash } = require("node:crypto");

const FIELD_PATTERNS = Object.freeze([
  ["title", /(?:talk|session|presentation|発表|登壇|演題).{0,20}(?:title|タイトル|題名)|^(?:title|タイトル|演題)$/i],
  ["abstract", /abstract|概要|要旨|発表内容|セッション説明/i],
  ["bio", /speaker.{0,10}bio|biography|プロフィール|自己紹介|登壇者紹介/i],
  ["application_reason", /application.{0,10}reason|応募理由|志望理由|登壇理由/i],
  ["product_demo_summary", /demo.{0,10}(?:summary|description)|デモ.{0,10}(?:概要|内容)|製品紹介/i],
]);
const BLOCKER_PATTERNS = Object.freeze([
  ["payment", /payment required|credit card|checkout|支払|決済|クレジットカード/i],
  ["captcha", /captcha|robot|ロボットではありません/i],
  ["identity_verification", /identity verification|本人確認|身分証|kyc/i],
]);

function unavailable() { throw new Error("talk browser provider unavailable"); }

function fieldKind(text) {
  const label = String(text == null ? "" : text).replace(/\s+/g, " ").trim().slice(0, 500);
  return FIELD_PATTERNS.find(([, pattern]) => pattern.test(label))?.[0] || null;
}

function classifyTalkFormSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)
    || typeof snapshot.visible_text !== "string" || snapshot.visible_text.length > 100_000
    || !Array.isArray(snapshot.fields) || snapshot.fields.length > 200) unavailable();
  const required = [];
  for (const field of snapshot.fields) {
    if (!field || typeof field !== "object" || Array.isArray(field) || field.required !== true) continue;
    const kind = fieldKind(`${field.label || ""} ${field.name || ""}`) || "unknown_required_field";
    if (!required.includes(kind)) required.push(kind);
  }
  const blockers = BLOCKER_PATTERNS.filter(([, pattern]) => pattern.test(snapshot.visible_text)).map(([name]) => name);
  return Object.freeze({ required_fields: Object.freeze(required), blocking_flags: Object.freeze(blockers) });
}

function snapshotTalkForm() {
  const visible = (element) => Boolean(element && element.getClientRects().length && !element.disabled);
  const fields = [...document.querySelectorAll("input, textarea, select")].filter(visible).map((element) => ({
    label: String(element.getAttribute("aria-label") || element.labels?.[0]?.innerText || element.closest("label")?.innerText || element.parentElement?.innerText || "").slice(0, 500),
    name: String(element.name || element.id || "").slice(0, 300),
    type: String(element.type || element.tagName || "").toLowerCase(),
    required: Boolean(element.required || element.getAttribute("aria-required") === "true"),
  }));
  return { visible_text: String(document.body?.innerText || "").slice(0, 100_000), fields };
}

function fillTalkForm(values) {
  const patterns = [
    ["title", /(?:talk|session|presentation|発表|登壇|演題).{0,20}(?:title|タイトル|題名)|^(?:title|タイトル|演題)$/i],
    ["abstract", /abstract|概要|要旨|発表内容|セッション説明/i],
    ["bio", /speaker.{0,10}bio|biography|プロフィール|自己紹介|登壇者紹介/i],
    ["application_reason", /application.{0,10}reason|応募理由|志望理由|登壇理由/i],
    ["product_demo_summary", /demo.{0,10}(?:summary|description)|デモ.{0,10}(?:概要|内容)|製品紹介/i],
  ];
  const controls = [...document.querySelectorAll("input, textarea")].filter((element) => element.getClientRects().length && !element.disabled);
  const filled = [];
  for (const [key, value] of Object.entries(values)) {
    const pattern = patterns.find(([name]) => name === key)?.[1];
    const matches = controls.filter((element) => pattern && pattern.test(String(element.getAttribute("aria-label") || element.labels?.[0]?.innerText || element.closest("label")?.innerText || element.parentElement?.innerText || element.name || "")));
    if (matches.length !== 1) return { filled: [] };
    matches[0].value = value;
    matches[0].dispatchEvent(new Event("input", { bubbles: true }));
    matches[0].dispatchEvent(new Event("change", { bubbles: true }));
    if (matches[0].value !== value) return { filled: [] };
    filled.push(key);
  }
  return { filled };
}

function submitTalkForm() {
  const visible = (element) => Boolean(element && element.getClientRects().length && !element.disabled);
  const controls = [...document.querySelectorAll('button[type="submit"], input[type="submit"], button')]
    .filter((element) => visible(element) && /submit|send|apply|応募|送信|申請/i.test(String(element.innerText || element.value || element.getAttribute("aria-label") || "")));
  if (controls.length !== 1) return { clicked: controls.length };
  controls[0].click();
  return { clicked: 1 };
}

function readTalkConfirmation() {
  const visible = (element) => Boolean(element && element.getClientRects().length && !element.disabled);
  const activeForm = [...document.querySelectorAll('button[type="submit"], input[type="submit"]')].some(visible);
  return { url: location.href, text: String(document.body?.innerText || "").slice(0, 20_000), active_form: activeForm };
}

function createTalkBrowserProvider() {
  return Object.freeze({
    async inspectForm({ page }) {
      if (!page || typeof page.evaluate !== "function") unavailable();
      return classifyTalkFormSnapshot(await page.evaluate(snapshotTalkForm));
    },
    async fillFields({ page, values }) {
      if (!page || typeof page.evaluate !== "function" || !values || typeof values !== "object" || Array.isArray(values)) unavailable();
      const result = await page.evaluate(fillTalkForm, values);
      if (!result || !Array.isArray(result.filled)
        || result.filled.slice().sort().join(",") !== Object.keys(values).sort().join(",")) unavailable();
    },
    async clickSubmit({ page }) {
      if (!page || typeof page.evaluate !== "function") unavailable();
      const result = await page.evaluate(submitTalkForm);
      if (!result || result.clicked !== 1) unavailable();
    },
    async readProviderState({ page }) {
      if (!page || typeof page.evaluate !== "function") unavailable();
      const result = await page.evaluate(readTalkConfirmation);
      if (!result || typeof result.url !== "string" || typeof result.text !== "string" || result.active_form !== false
        || !/(?:response has been recorded|application (?:was )?submitted|submission (?:is )?complete|回答を記録しました|送信しました|応募を受け付けました)/i.test(result.text)) {
        return Object.freeze({ status: "unavailable" });
      }
      const digest = createHash("sha256").update(`${result.url}\n${result.text}`, "utf8").digest("hex");
      return Object.freeze({ status: "provider_verified", receipt_ref: `provider-receipt://connector/talk/${digest}` });
    },
  });
}

module.exports = { classifyTalkFormSnapshot, createTalkBrowserProvider };
