"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { agentSearchCandidate } = require("./ask.js");

test("candidate research meters tenant-scoped Gemini and Search grounding separately", async () => {
  const usage = [];
  const responses = [
    { usageMetadata: { promptTokenCount: 100, candidatesTokenCount: 20, totalTokenCount: 120 },
      candidates: [{ content: { parts: [{ text: "venue evidence" }] } }] },
    { usageMetadata: { promptTokenCount: 50, candidatesTokenCount: 10, totalTokenCount: 60 },
      candidates: [{ content: { parts: [{ functionCall: { name: "submit_candidate",
        args: { found: true, candidate: "Tokyo Station", source: "web_search" } } }] } }] },
  ];
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => responses.shift() });
  try {
    const result = await agentSearchCandidate({ summary: "meeting", description: "" }, {
      uid: "tenant-1", geminiKey: "test-key", mailAvailable: async () => false,
      recordUsageEvent: async (event) => { usage.push(event); return true; },
    });
    assert.equal(result.found, true);
  } finally {
    globalThis.fetch = oldFetch;
  }
  assert.deepEqual(usage.map((event) => [event.tenantId, event.provider, event.feature]), [
    ["tenant-1", "gemini", "ask_candidate_search"],
    ["tenant-1", "google_search_grounding", "ask_candidate_search"],
    ["tenant-1", "gemini", "ask_candidate_extract"],
  ]);
});
