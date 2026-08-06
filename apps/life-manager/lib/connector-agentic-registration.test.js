"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { runConnectorAgenticRegistration } = require("./connector-agentic-registration.js");

test("pins Terra to the parent-owned CDP target receipt", async () => {
  let invocation;
  const value = await runConnectorAgenticRegistration({
    canonicalUrl: "https://luma.com/event-a",
    tabOwnerReceipt: {
      schema_version: 1,
      endpoint: "http://127.0.0.1:9222",
      owner_token: "owner-token-123",
      generation: 1,
      target_id: "OWNED123",
      page_websocket: "ws://127.0.0.1:9222/devtools/page/OWNED123",
      baseline_target_ids: ["BASELINE"],
      canonical_url: "https://luma.com/event-a",
      observed_at: "2026-08-06T01:02:03.000Z",
    },
    profile: { full_name: "Private Person" },
    evidenceDir: "/tmp/connector-evidence",
    repoRoot: "/tmp/repo",
    runnerPath: "/tmp/runner",
  }, {
    async runAgentRunner(input) {
      invocation = input;
      return {
        summary: { selected_model: "gpt-5.6-terra" },
        value: {
          status: "registered",
          observed_url: "https://luma.com/event-a",
          form_visible: false,
          submit_control_visible: false,
          observed_marker: "You're Going",
        },
      };
    },
  });

  assert.equal(value.status, "registered");
  assert.equal(invocation.taskClass, "browser-lane-agent");
  assert.match(invocation.prompt, /targetInfo\.targetId equals receipt\.target_id/);
  assert.match(invocation.prompt, /"target_id":"OWNED123"/);
  assert.doesNotMatch(invocation.prompt, /:9223/);
});

test("refuses to start Terra without a valid parent-owned receipt", async () => {
  await assert.rejects(
    runConnectorAgenticRegistration({
      canonicalUrl: "https://luma.com/event-a",
      tabOwnerReceipt: null,
    }, { runAgentRunner: async () => { throw new Error("must not run"); } }),
    /unavailable/,
  );

  await assert.rejects(
    runConnectorAgenticRegistration({
      canonicalUrl: "https://luma.com/event-a",
      tabOwnerReceipt: {
        schema_version: 1,
        endpoint: "http://127.0.0.1:9222",
        owner_token: "owner-token-123",
        generation: 0,
        target_id: "OWNED123",
        page_websocket: "ws://127.0.0.1:9222/devtools/page/OWNED123",
        baseline_target_ids: [],
        canonical_url: "https://luma.com/event-a",
        observed_at: "2026-08-06T01:02:03.000Z",
      },
    }, { runAgentRunner: async () => { throw new Error("must not run"); } }),
    /unavailable/,
  );
});
