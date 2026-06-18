"use strict";
const assert = require("assert");
const { isHelperBlock, buildStreamUrl } = require("../scheduler.js");

// helper-block detection: never wake for Anicca's own inserted blocks
assert.strictEqual(isHelperBlock("[Travel] [APPLIED] Stand-Up"), true, "Travel block");
assert.strictEqual(isHelperBlock("🎤 [PENDING] AI Tinkerers"), true, "PENDING marker");
assert.strictEqual(isHelperBlock("Dentist appointment"), false, "real event");
assert.strictEqual(isHelperBlock(""), false, "empty");

// streamUrl carries per-call ctx in the query (so the persistent bridge prompts correctly)
process.env.PUBLIC_WSS = "wss://life-call.up.railway.app";
const u = buildStreamUrl({ summary: "Dentist & Co", startIso: "2026-06-18T20:40:00+09:00", location: "Tokyo" }, "firm");
const parsed = new URL(u);
assert.strictEqual(parsed.protocol, "wss:", "wss");
assert.strictEqual(parsed.pathname, "/ws", "/ws path");
assert.strictEqual(parsed.searchParams.get("summary"), "Dentist & Co", "summary roundtrip (encoded &)");
assert.strictEqual(parsed.searchParams.get("dateTime"), "2026-06-18T20:40:00+09:00", "dateTime");
assert.strictEqual(parsed.searchParams.get("urgency"), "firm", "urgency");

console.log("✅ scheduler unit tests pass (helper-block skip + streamUrl ctx encoding)");
