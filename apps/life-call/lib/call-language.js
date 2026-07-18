"use strict";

function langForPhone(phone) {
  return String(phone || "").replace(/[^\d+]/g, "").startsWith("+81") ? "ja" : "en";
}

function openingTurnForLang(lang) {
  return lang === "ja"
    ? "最初の一言から日本語で通話を始めてください。"
    : "Begin the call now with your opening line.";
}

module.exports = { langForPhone, openingTurnForLang };
