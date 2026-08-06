"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { runMinimalConnectorWake } = require("./connector-minimal-runner.js");

function candidate(provider, slug) {
  return Object.freeze({
    provider,
    event_ref: `${provider}-event://event/${slug}`,
    canonical_url: `https://${provider}.example.test/${slug}`,
    starts_at: "2026-08-10T10:00:00.000Z",
    ends_at: "2026-08-10T11:00:00.000Z",
    price_minor: 0,
  });
}

function fixture(overrides = {}) {
  const calls = [];
  const page = Object.freeze({ page_id: "page-owned-1" });
  let nowMs = Date.parse("2026-08-07T02:00:00.000Z");
  const dependencies = {
    now: () => new Date(nowMs).toISOString(),
    browserRail: {
      async open() {
        calls.push(["open"]);
        return Object.freeze({
          session_id: "session-owned-1",
          target_id: "TARGETOWNED1",
          page,
        });
      },
      async navigate(owned, url) {
        assert.equal(owned.page, page);
        calls.push(["navigate", owned.session_id, owned.target_id, owned.page.page_id, url]);
      },
      async close(owned) {
        assert.equal(owned.page, page);
        calls.push(["close", owned.session_id, owned.target_id, owned.page.page_id]);
      },
    },
    async readCalendarGaps() {
      calls.push(["calendar"]);
      return Object.freeze([{ starts_at: "2026-08-10T09:00:00.000Z", ends_at: "2026-08-10T12:00:00.000Z" }]);
    },
    async discoverCandidates(provider) {
      calls.push(["discover", provider]);
      return provider === "luma"
        ? [candidate("luma", "one"), candidate("luma", "two")]
        : [candidate("connpass", "three")];
    },
    async runDirectAction({ candidate: selected, page: suppliedPage }) {
      assert.equal(suppliedPage, page);
      calls.push(["direct", selected.event_ref, suppliedPage.page_id]);
      return Object.freeze({ status: "failed", safe_reason: "direct_action_unavailable" });
    },
    async runAgentFallback({ candidate: selected, page: suppliedPage, maxSteps }) {
      assert.equal(suppliedPage, page);
      assert.equal(maxSteps, 10);
      calls.push(["agent", selected.event_ref, suppliedPage.page_id, maxSteps]);
      return Object.freeze({ status: "failed", safe_reason: "agent_action_unavailable" });
    },
    async readProviderState({ candidate: selected, page: suppliedPage }) {
      assert.equal(suppliedPage, page);
      calls.push(["readback", selected.event_ref, suppliedPage.page_id]);
      return Object.freeze({ status: "absent" });
    },
    async completeEvidence() {
      throw new Error("evidence must not run without registered/pending readback");
    },
    async reportWake(report) {
      calls.push(["report", report.status, report.safe_reason]);
      return Object.freeze({ telegram_provider_id: "9001" });
    },
    ...overrides,
  };
  return {
    calls,
    dependencies,
    page,
    advance(ms) { nowMs += ms; },
  };
}

test("one wake reuses one owned session, target, and page across candidates and providers", async () => {
  const state = fixture();

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-1",
    providers: ["luma", "connpass"],
  }, state.dependencies);

  assert.equal(result.status, "circuit_open");
  assert.equal(state.calls.filter(([name]) => name === "open").length, 1);
  assert.equal(state.calls.filter(([name]) => name === "close").length, 1);
  assert.deepEqual(
    state.calls.filter(([name]) => name === "navigate").map((call) => call.slice(1, 4)),
    [
      ["session-owned-1", "TARGETOWNED1", "page-owned-1"],
      ["session-owned-1", "TARGETOWNED1", "page-owned-1"],
      ["session-owned-1", "TARGETOWNED1", "page-owned-1"],
    ],
  );
  assert.deepEqual(
    state.calls.filter(([name]) => name === "discover").map(([, provider]) => provider),
    ["luma", "connpass"],
  );
});

test("a failed direct action invokes at most ten agent steps on the exact same page", async () => {
  const state = fixture({
    async runAgentFallback(input) {
      assert.equal(input.page.page_id, "page-owned-1");
      assert.equal(input.maxSteps, 10);
      assert.equal(Object.hasOwn(input, "browser"), false);
      state.calls.push(["agent", input.candidate.event_ref, input.page.page_id, input.maxSteps]);
      return Object.freeze({ status: "completed", repaired_actions: [{ purpose: "submit", method: "ax_click" }] });
    },
    async readProviderState(input) {
      assert.equal(input.page.page_id, "page-owned-1");
      return Object.freeze({ status: "registered", provider_receipt_id: "provider-receipt-1" });
    },
    async completeEvidence(input) {
      assert.equal(input.page.page_id, "page-owned-1");
      return Object.freeze({ status: "applied_bundle", bundle_id: "applied-bundle-1" });
    },
  });

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-2",
    providers: ["luma", "connpass"],
  }, state.dependencies);

  assert.deepEqual(result, Object.freeze({
    status: "applied_bundle",
    bundle_id: "applied-bundle-1",
    telegram_provider_id: "9001",
  }));
  assert.equal(state.calls.filter(([name]) => name === "navigate").length, 1);
  assert.equal(state.calls.filter(([name]) => name === "agent").length, 1);
  assert.equal(state.calls.filter(([name]) => name === "close").length, 1);
});

test("three consecutive candidate failures open the circuit before a fourth navigation", async () => {
  const state = fixture();

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-3",
    providers: ["luma", "connpass"],
    maxConsecutiveFailures: 3,
  }, state.dependencies);

  assert.equal(result.status, "circuit_open");
  assert.equal(result.safe_reason, "consecutive_failure_limit");
  assert.equal(state.calls.filter(([name]) => name === "navigate").length, 3);
  assert.equal(state.calls.filter(([name]) => name === "agent").length, 3);
  assert.deepEqual(state.calls.filter(([name]) => name === "report").at(-1), [
    "report", "circuit_open", "consecutive_failure_limit",
  ]);
});

test("the ten-minute wake deadline stops browser churn and still reports the wake", async () => {
  let state;
  state = fixture({
    async runDirectAction({ candidate: selected }) {
      state.calls.push(["direct", selected.event_ref]);
      state.advance(600_001);
      return Object.freeze({ status: "failed", safe_reason: "direct_action_timeout" });
    },
  });

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-4",
    providers: ["luma", "connpass"],
    maxWakeMs: 600_000,
  }, state.dependencies);

  assert.equal(result.status, "circuit_open");
  assert.equal(result.safe_reason, "wake_deadline");
  assert.equal(state.calls.filter(([name]) => name === "navigate").length, 1);
  assert.equal(state.calls.filter(([name]) => name === "agent").length, 0);
  assert.deepEqual(state.calls.filter(([name]) => name === "report").at(-1), [
    "report", "circuit_open", "wake_deadline",
  ]);
});
