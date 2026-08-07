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
          page_websocket: "ws://127.0.0.1:9222/devtools/page/TARGETOWNED1",
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
    async runCachedAction({ candidate: selected, page: suppliedPage }) {
      assert.equal(suppliedPage, page);
      calls.push(["cache", selected.event_ref, suppliedPage.page_id]);
      return Object.freeze({ status: "cache_miss" });
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
    async saveRepairedActions(input) {
      calls.push(["cache-save", input.candidate.event_ref]);
      return Object.freeze({ status: "saved" });
    },
    async reportWake(report) {
      calls.push(["report", report.status, report.safe_reason]);
      return Object.freeze({ telegram_provider_id: "9001" });
    },
    async recordAction(action) {
      calls.push(["history", action]);
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

test("provider discovery failure continues and still reports the wake", async () => {
  const state = fixture({
    async discoverCandidates(provider) {
      state.calls.push(["discover", provider]);
      if (provider === "luma") {
        const error = new Error("provider changed");
        error.code = "CONNPASS_CALENDAR_NAVIGATION_FAILED";
        throw error;
      }
      return [];
    },
  });

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-1",
    providers: ["luma", "connpass"],
  }, state.dependencies);

  assert.deepEqual(state.calls.filter(([name]) => name === "discover").map(([, provider]) => provider), [
    "luma", "connpass",
  ]);
  assert.deepEqual(state.calls.find(([name]) => name === "report").slice(1), [
    "completed_no_effect", "connpass_calendar_navigation_failed",
  ]);
  assert.equal(state.calls.filter(([name]) => name === "close").length, 1);
  assert.equal(result.telegram_provider_id, "9001");
});

test("a failed direct action invokes at most ten agent steps on the exact same page", async () => {
  const state = fixture({
    async runAgentFallback(input) {
      assert.equal(input.page.page_id, "page-owned-1");
      assert.equal(input.pageWebsocket, "ws://127.0.0.1:9222/devtools/page/TARGETOWNED1");
      assert.equal(input.maxSteps, 10);
      assert.equal(Object.hasOwn(input, "browser"), false);
      state.calls.push(["agent", input.candidate.event_ref, input.page.page_id, input.maxSteps]);
      return Object.freeze({ status: "completed", repaired_actions: [{ purpose: "submit", method: "ax_click" }] });
    },
    async readProviderState(input) {
      assert.equal(input.page.page_id, "page-owned-1");
      if (input.phase === "pre_submit") return Object.freeze({ status: "absent" });
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
  assert.equal(state.calls.filter(([name]) => name === "cache-save").length, 1);
  assert.equal(state.calls.filter(([name]) => name === "close").length, 1);
});

test("a verified cached replay skips both direct and agent actions", async () => {
  const state = fixture({
    async runCachedAction(input) {
      state.calls.push(["cache", input.candidate.event_ref]);
      return Object.freeze({
        status: "completed",
        provider_state: { status: "registered", provider_receipt_id: "receipt-cache" },
      });
    },
    async runDirectAction() { throw new Error("direct action must not run on cache hit"); },
    async runAgentFallback() { throw new Error("agent must not run on cache hit"); },
    async completeEvidence(input) {
      assert.equal(input.providerState.provider_receipt_id, "receipt-cache");
      return Object.freeze({ status: "applied_bundle", bundle_id: "applied-bundle-cache" });
    },
  });

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-cache",
    providers: ["luma", "connpass"],
  }, state.dependencies);

  assert.equal(result.status, "applied_bundle");
  assert.equal(result.bundle_id, "applied-bundle-cache");
  assert.equal(state.calls.filter(([name]) => name === "cache").length, 1);
  assert.equal(state.calls.filter(([name]) => name === "direct").length, 0);
  assert.equal(state.calls.filter(([name]) => name === "agent").length, 0);
  assert.equal(state.calls.filter(([name]) => name === "cache-save").length, 0);
});

test("a parent readback after navigation skips every submit path when already registered", async () => {
  const state = fixture({
    async readProviderState(input) {
      assert.equal(input.page.page_id, "page-owned-1");
      state.calls.push(["readback", input.candidate.event_ref, input.page.page_id]);
      return Object.freeze({
        status: "registered",
        provider_receipt_id: "receipt-existing",
      });
    },
    async runCachedAction() { throw new Error("cache must not replay after registered readback"); },
    async runDirectAction() { throw new Error("direct Submit must not run after registered readback"); },
    async runAgentFallback() { throw new Error("agent must not run after registered readback"); },
    async completeEvidence(input) {
      assert.equal(input.providerState.provider_receipt_id, "receipt-existing");
      return Object.freeze({ status: "applied_bundle", bundle_id: "applied-bundle-existing" });
    },
  });

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-existing",
    providers: ["luma", "connpass"],
  }, state.dependencies);

  assert.equal(result.status, "applied_bundle");
  assert.equal(result.bundle_id, "applied-bundle-existing");
  assert.equal(state.calls.filter(([name]) => name === "readback").length, 1);
  assert.equal(state.calls.filter(([name]) => name === "cache").length, 0);
  assert.equal(state.calls.filter(([name]) => name === "direct").length, 0);
  assert.equal(state.calls.filter(([name]) => name === "agent").length, 0);
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

test("every recorded action contains only the safe audit fields", async () => {
  const state = fixture();

  await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-5",
    providers: ["luma", "connpass"],
  }, state.dependencies);

  const history = state.calls.filter(([name]) => name === "history").map(([, row]) => row);
  assert.ok(history.length > 0);
  for (const row of history) {
    assert.deepEqual(Object.keys(row).sort(), [
      "duration_ms", "method", "purpose", "result", "timestamp",
    ]);
    assert.match(row.purpose, /^(navigate|observe|fill|submit|readback)$/);
    assert.match(row.method, /^[a-z][a-z0-9_]{1,63}$/);
    assert.match(row.result, /^(success|failed)$/);
    assert.equal(new Date(Date.parse(row.timestamp)).toISOString(), row.timestamp);
    assert.equal(Number.isInteger(row.duration_ms) && row.duration_ms >= 0, true);
    assert.equal(JSON.stringify(row).includes("owner-token"), false);
    assert.equal(JSON.stringify(row).includes("example.test"), false);
  }
});
