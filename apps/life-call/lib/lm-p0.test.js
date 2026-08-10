"use strict";

const test = require("node:test");
const assert = require("node:assert");
const {
  telnyxDialBody,
  telnyxStreamingStartBody,
} = require("./call-logic.js");
const {
  setWebhook,
  answerCallbackQuery,
  parseUpdate,
  routeCallbackData,
} = require("./telegram.js");
const {
  agentSearchCandidate,
  closedAskMessage,
  handleAskCallback,
  askTick,
} = require("./ask.js");
const { makeUnipileMail } = require("./transport/mail-unipile.js");
const { mailAvailable, resetMailAvailabilityCache } = require("./mail-availability.js");

test("LM-24: both Telnyx streaming bodies target the caller leg", () => {
  assert.equal(telnyxDialBody({ connectionId: "c", to: "+1", from: "+2", streamUrl: "wss://x" }).stream_bidirectional_target_legs, "self");
  assert.equal(telnyxStreamingStartBody({ streamUrl: "wss://x" }).stream_bidirectional_target_legs, "self");
});

test("LM-30: webhook subscribes to edited live-location updates; callbacks are answered", async () => {
  const original = global.fetch;
  const calls = [];
  global.fetch = async (url, init) => {
    calls.push({ url, body: JSON.parse(init.body) });
    return { json: async () => ({ ok: true }) };
  };
  try {
    await setWebhook("t", "https://x/telegram", "s");
    await answerCallbackQuery("t", "cb-1", "Saved");
    assert.deepEqual(calls[0].body.allowed_updates, ["message", "edited_message", "callback_query"]);
    assert.match(calls[1].url, /answerCallbackQuery$/);
    assert.deepEqual(calls[1].body, { callback_query_id: "cb-1", text: "Saved" });
  } finally { global.fetch = original; }
});

test("LM-30: parseUpdate preserves message fields and parses callback_query/live location", () => {
  assert.deepEqual(parseUpdate({ message: { chat: { id: 7 }, from: { id: 8, first_name: "Dais", last_name: "Tanaka" }, text: " /start x " } }), {
    kind: "message", chatId: "7", userId: "8", text: "/start x", isStart: true,
    firstName: "Dais", lastName: "Tanaka",
  });
  assert.deepEqual(parseUpdate({ callback_query: { id: "cb", from: { id: 8 }, data: "ask:yes:e1:r1", message: { chat: { id: 7 } } } }), {
    kind: "callback", chatId: "7", userId: "8", data: "ask:yes:e1:r1", callbackQueryId: "cb",
  });
  assert.deepEqual(parseUpdate({ edited_message: {
    message_id: 41, date: 1_721_612_800, edit_date: 1_721_613_100,
    chat: { id: 7 }, from: { id: 8 },
    location: { latitude: 35.681236, longitude: 139.767125, live_period: 900 },
  } }), {
    kind: "location", chatId: "7", userId: "8", messageId: "41",
    latitude: 35.681236, longitude: 139.767125,
    observedAtMs: 1_721_613_100_000, expiresAtMs: 1_721_613_700_000,
  });
  assert.equal(parseUpdate({ message: {
    message_id: 40, date: 1_721_612_800, chat: { id: 7 }, from: { id: 8 },
    location: { latitude: 35.68, longitude: 139.76, live_period: 900 },
  } }).kind, "location", "the initial live-location message opens the gate before edits arrive");
});

test("LM-23/LM-6: callback router dispatches ask/gmail and ignores removed/unknown prefixes", async () => {
  const routed = [], logs = [];
  assert.equal(await routeCallbackData("ask:yes:e:r", { ask: async (data) => { routed.push(data); return "ok"; } }), "ok");
  assert.deepEqual(routed, ["ask:yes:e:r"]);
  assert.equal(await routeCallbackData("gmail:skip", { gmail: async (data) => { routed.push(data); return "gmail"; } }), "gmail");
  assert.deepEqual(routed, ["ask:yes:e:r", "gmail:skip"]);
  assert.deepEqual(await routeCallbackData("retired:t", {}, (line) => logs.push(line)), { ignored: true });
  assert.deepEqual(await routeCallbackData("leave:no:e", {}, (line) => logs.push(line)), { ignored: true });
  assert.ok(logs.every((line) => /unknown callback prefix/.test(line)));
});

test("LM-3: Unipile searchInbox uses the verified search query parameter", async () => {
  const original = global.fetch;
  let requested = "";
  global.fetch = async (url) => { requested = url; return { json: async () => ({ items: [{ subject: "Venue" }] }) }; };
  try {
    const items = await makeUnipileMail({ accountId: "a", token: "t", dsn: "api.example" }).searchInbox("MUIT 集会");
    assert.equal(items.length, 1);
    assert.equal(new URL(requested).searchParams.get("search"), "MUIT 集会");
  } finally { global.fetch = original; }
});

test("LM-3: search then extraction uses two Gemini calls and Gmail snippets", async () => {
  const bodies = [];
  const raw = async (body) => {
    bodies.push(body);
    if (bodies.length === 1) return { candidates: [{ content: { parts: [{ text: "Official page says Tokyo Hall. Gmail confirms it." }] } }] };
    return { candidates: [{ content: { parts: [{ functionCall: { name: "submit_candidate", args: { found: true, candidate: "Tokyo Hall", source: "gmail" } } }] } }] };
  };
  const out = await agentSearchCandidate({ summary: "MUIT 集会", description: "" }, {
    geminiKey: "k", geminiRaw: raw,
    mail: { ready: () => true, searchInbox: async () => [{ subject: "MUIT", body: "Venue: Tokyo Hall" }] },
  });
  assert.deepEqual(out, { found: true, candidate: "Tokyo Hall", source: "gmail" });
  assert.deepEqual(bodies[0].tools, [{ google_search: {} }]);
  assert.match(bodies[0].contents[0].parts[0].text, /Tokyo Hall/);
  assert.ok(bodies[1].tools[0].functionDeclarations[0].name === "submit_candidate");
  assert.equal(bodies[1].tools.some((t) => t.google_search), false);
});

test("Gmail OFF: cached provider probe rejects 401 and avoids a probe on every call", async () => {
  resetMailAvailabilityCache();
  let probes = 0;
  const opts = { token: "expired", dsn: "api.example", nowMs: 1000,
    fetchImpl: async () => { probes++; return { ok: false, status: 401 }; }, warn: () => {} };
  assert.equal(await mailAvailable({ gmail_account_id: "a" }, opts), false);
  assert.equal(await mailAvailable({ gmail_account_id: "b" }, { ...opts, nowMs: 2000 }), false);
  assert.equal(probes, 1);
});

test("Gmail OFF: search-before-ask skips inbox and goes directly to Google Search", async () => {
  let searched = 0;
  const bodies = [];
  await agentSearchCandidate({ summary: "MUIT", description: "" }, {
    geminiKey: "k", gmailAccountId: "a", unipileToken: "expired", unipileDsn: "api.example",
    mailAvailable: async () => false,
    mail: { searchInbox: async () => { searched++; return []; } },
    geminiRaw: async (body) => { bodies.push(body); return bodies.length === 1
      ? { candidates: [{ content: { parts: [{ text: "web result" }] } }] }
      : { candidates: [{ content: { parts: [{ functionCall: { name: "submit_candidate", args: { found: false, candidate: "", source: "web_search" } } }] } }] }; },
  });
  assert.equal(searched, 0);
  assert.deepEqual(bodies[0].tools, [{ google_search: {} }]);
  assert.match(bodies[0].contents[0].parts[0].text, /Gmail unavailable/);
});

test("LM-3: candidate found builds the exact closed-question buttons", () => {
  assert.deepEqual(closedAskMessage({ id: "e1", summary: "MUIT 集会", whenLabel: "金曜" }, "Tokyo Hall", "r1"), {
    text: "金曜の「MUIT 集会」は、いつものTokyo Hallですか？\n［はい］［別の場所］",
    extra: { reply_markup: { inline_keyboard: [[
      { text: "はい", callback_data: "ask:yes:e1:r1" },
      { text: "別の場所", callback_data: "ask:no:e1:r1" },
    ]] } },
  });
});

test("LM-3: yes callback writes persisted candidate; no falls back to free text", async () => {
  const patches = [], messages = [];
  const yes = await handleAskCallback("ask:yes:e1:r1", {
    lookupCandidate: async () => ({ uid: "u1", eventId: "e1", candidate: "Tokyo Hall", summary: "MUIT 集会" }),
    patch: async (...args) => patches.push(args),
    remember: async () => true,
  });
  assert.equal(yes.ok, true);
  assert.deepEqual(patches[0], ["u1", "e1", "Tokyo Hall"]);

  const no = await handleAskCallback("ask:no:e1:r1", {
    chatId: "7", telegramToken: "t", summary: "MUIT 集会",
    sendMessage: async (...args) => { messages.push(args); return { ok: true }; },
  });
  assert.equal(no.fallback, true);
  assert.equal(messages[0][2], "場所はどこですか？住所か、お店・会社の名前を送ってください。");
});

test("LM-3: no candidate is a silent null so existing open question remains", async () => {
  const out = await agentSearchCandidate({ summary: "造語イベント" }, {
    geminiKey: "k",
    geminiRaw: async (_body, _key) => ({ candidates: [{ content: { parts: [{ text: "No reliable venue." }] } }] }),
    mail: { ready: () => false, searchInbox: async () => { throw new Error("must skip"); } },
  });
  assert.deepEqual(out, { found: false, candidate: "", source: "" });
});

// life-manager#11: resolveLocation alone can't place the event ("ask" kind) but agentSearchCandidate finds a
// candidate via Gmail/web search — askTick must autofill directly (like the "filled" branch) and never send
// an ask. Asking is the failure mode, not the fallback of first resort.
test("life-manager#11: ask-kind event with a found candidate autofills, sends no ask", async () => {
  const patches = [], records = [];
  const bodies = [];
  const usageArgs = [];
  const raw = async (body, _key, usage) => {
    bodies.push(body);
    usageArgs.push(usage);
    if (bodies.length === 1) return { candidates: [{ content: { parts: [{ text: "Official page: Tokyo Hall." }] } }] };
    return { candidates: [{ content: { parts: [{ functionCall: { name: "submit_candidate", args: { found: true, candidate: "Tokyo Hall", source: "gmail" } } }] } }] };
  };
  const result = await askTick("u1", {
    composioKey: "c", supaUrl: "http://s", supaKey: "k", geminiKey: "g",
    listEvents: async () => [{ id: "e1", summary: "MUIT 集会", description: "", start: { dateTime: "2026-07-01T12:00:00Z" } }],
    askedSet: async () => new Set(),
    patchEvent: async (...args) => patches.push(args),
    recordResolution: async (...args) => records.push(args),
    recall: async () => null,
    resolve: async () => ({ kind: "ask" }),
    geminiRaw: raw,
    mail: { ready: () => true, searchInbox: async () => [{ subject: "MUIT", body: "Venue: Tokyo Hall" }] },
  });
  assert.deepEqual(result, { autofilled: 1, asked: 0, resolved: 0 });
  assert.deepEqual(patches[0], ["u1", "e1", { location: "Tokyo Hall" }, "c", undefined]);
  assert.deepEqual(records[0], ["u1", "e1", "gmail", "http://s", "k"]);
  assert.equal(usageArgs.length, 2);
  assert.strictEqual(usageArgs[0], usageArgs[1]);
  assert.deepEqual(usageArgs[0], { owner_id: "u1", financial_unit_id: "life_manager_saas", request_model: "gemini-2.5-flash", storeOptions: { supaUrl: "http://s", supaKey: "k" } });
});

test("CFO-2a2.3c1: default ask candidate records both Gemini calls", async () => {
  const original = global.fetch, geminiBodies = [], rpcBodies = [], rpcReceipts = [];
  const responses = [
    { responseId: "ask-response-1", modelVersion: "gemini-2.5-flash-001", usageMetadata: { promptTokenCount: 11, candidatesTokenCount: 5, totalTokenCount: 16 }, candidates: [{ content: { parts: [{ text: "Official page: Tokyo Hall." }] } }] },
    { responseId: "ask-response-2", modelVersion: "gemini-2.5-flash-001", usageMetadata: { promptTokenCount: 17, candidatesTokenCount: 6, totalTokenCount: 23 }, candidates: [{ content: { parts: [{ functionCall: { name: "submit_candidate", args: { found: true, candidate: "Tokyo Hall", source: "web_search" } } }] } }] },
  ];
  let geminiCalls = 0;
  global.fetch = async (url, init = {}) => {
    if (url.includes("generativelanguage.googleapis.com")) {
      geminiBodies.push(JSON.parse(init.body)); return { ok: true, status: 200, json: async () => responses[geminiCalls++] };
    }
    if (url.endsWith("/rest/v1/rpc/lm_append_cfo_model_usage_evidence")) {
      const body = JSON.parse(init.body); rpcBodies.push(body); const receipt = { public_ref: `30000000-0000-4000-8000-00000000000${rpcBodies.length}`, provider: body.p_provider, provider_request_id: body.p_provider_request_id, usage_sequence: body.p_usage_sequence, trace_id: body.p_trace_id, created_at: "2026-08-10T01:02:04.000Z" }; rpcReceipts.push(receipt); return { ok: true, status: 200, json: async () => receipt };
    }
    throw new Error(`unexpected fetch: ${url}`);
  };
  try {
    const patches = []; const result = await askTick("u1", {
      composioKey: "c", supaUrl: "https://db.example", supaKey: "service-role-secret", geminiKey: "g",
      listEvents: async () => [{ id: "e1", summary: "MUIT 集会", description: "", start: { dateTime: "2026-07-01T12:00:00Z" } }],
      askedSet: async () => new Set(), patchEvent: async (...args) => patches.push(args), recordResolution: async () => {},
      recall: async () => null, resolve: async () => ({ kind: "ask" }), mailAvailable: async () => false,
      mail: { ready: () => false, searchInbox: async () => [] },
    });
    assert.deepEqual(result, { autofilled: 1, asked: 0, resolved: 0 }); assert.deepEqual(patches[0].slice(0, 3), ["u1", "e1", { location: "Tokyo Hall" }]);
    assert.equal(geminiCalls, 2); assert.equal(rpcBodies.length, 2); assert.equal(rpcReceipts.length, 2);
    const traces = rpcBodies.map((body) => body.p_trace_id); assert.ok(traces.every((trace) => /^(?!0{32})[0-9a-f]{32}$/.test(trace))); assert.notEqual(traces[0], traces[1]);
    assert.deepEqual(rpcReceipts.map((receipt) => receipt.trace_id), traces);
    for (const body of geminiBodies) { const rawBody = JSON.stringify(body); assert.doesNotMatch(rawBody, /owner_id|financial_unit_id|supaUrl|supaKey|storeOptions/); assert.ok(!["u1", "https://db.example", "service-role-secret"].some((sentinel) => rawBody.includes(sentinel))); }
  } finally { global.fetch = original; }
});

test("CFO-2a2.3c1: default path propagates fixed store error", async () => {
  const original = global.fetch;
  const response = { responseId: "ask-response-error", modelVersion: "gemini-2.5-flash-001", usageMetadata: { promptTokenCount: 1, candidatesTokenCount: 1, totalTokenCount: 2 }, candidates: [{ content: { parts: [{ text: "research" }] } }] };
  global.fetch = async (url) => url.includes("generativelanguage.googleapis.com")
    ? { ok: true, status: 200, json: async () => response }
    : { ok: false, status: 503, json: async () => ({}) };
  try {
    await assert.rejects(() => agentSearchCandidate({ summary: "MUIT" }, {
      geminiKey: "g", providerUsage: { owner_id: "u1", financial_unit_id: "life_manager_saas", request_model: "gemini-2.5-flash", storeOptions: { supaUrl: "https://db.example", supaKey: "service-role-secret" } },
      mailAvailable: async () => false, mail: { ready: () => false, searchInbox: async () => [] },
    }), error => { assert.equal(error.message, "cfo_provider_usage_span_failed:store"); return true; });
  } finally { global.fetch = original; }
});

// life-manager#11 (control): when NO candidate is found either, the event still falls through to the ask
// path unchanged (claimAsk gates the real send, which needs Supabase — asserted here via the fast-path
// askedSet dedup instead, proving askTick does not autofill on a genuinely unresolvable event).
test("life-manager#11: ask-kind event with no candidate does not autofill", async () => {
  const patches = [];
  const result = await askTick("u1", {
    composioKey: "c", supaUrl: "http://s", supaKey: "k", geminiKey: "g",
    listEvents: async () => [{ id: "e1", summary: "造語イベント", start: { dateTime: "2026-07-01T12:00:00Z" } }],
    askedSet: async () => new Set(["e1"]), // already asked this event → claimAsk path is skipped, isolating the assertion to autofill-or-not
    patchEvent: async (...args) => patches.push(args),
    recordResolution: async () => {},
    recall: async () => null,
    resolve: async () => ({ kind: "ask" }),
    geminiRaw: async () => ({ candidates: [{ content: { parts: [{ text: "No reliable venue." }] } }] }),
    mail: { ready: () => false, searchInbox: async () => { throw new Error("must skip"); } },
  });
  assert.deepEqual(result, { autofilled: 0, asked: 0, resolved: 0 });
  assert.deepEqual(patches, []);
});
