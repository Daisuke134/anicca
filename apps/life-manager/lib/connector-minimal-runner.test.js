"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { runMinimalConnectorWake } = require("./connector-minimal-runner.js");
const { createMinimalEvidenceChain } = require("./connector-minimal-evidence.js");
const { createMinimalProductionOperations } = require("./connector-minimal-operations.js");

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

function assertDurableWakeReport(stateDir, telegramProviderId) {
  const files = ["wake-reports.jsonl", "wake-report-deliveries.jsonl"].map((name) => path.join(stateDir, name));
  const rows = files.map((file) => { assert.equal(fs.statSync(file).mode & 0o777, 0o600); return fs.readFileSync(file, "utf8").trim().split("\n").map(JSON.parse); });
  assert.equal(rows[0].length, 1); assert.equal(rows[1].length, 1); assert.equal(rows[1][0].telegram_provider_id, telegramProviderId);
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
  const navigations = state.calls.filter(([name]) => name === "navigate");
  assert.deepEqual(navigations.map((call) => call.slice(1, 4)), [
    ["session-owned-1", "TARGETOWNED1", "page-owned-1"],
    ["session-owned-1", "TARGETOWNED1", "page-owned-1"],
    ["session-owned-1", "TARGETOWNED1", "page-owned-1"],
    ["session-owned-1", "TARGETOWNED1", "page-owned-1"],
  ]);
  assert.equal(navigations.filter((call) => call[4] === "about:blank").length, 1);
  assert.notEqual(navigations[0][4], "about:blank");
  assert.notEqual(navigations.at(-1)[4], "about:blank");
  const firstDiscovery = state.calls.findIndex(([name]) => name === "discover");
  const secondDiscovery = state.calls.findIndex(([name, provider]) => name === "discover" && provider === "connpass");
  const reset = state.calls.findIndex(([name, , , , url]) => name === "navigate" && url === "about:blank");
  assert.ok(firstDiscovery < reset && reset < secondDiscovery);
  assert.deepEqual(state.calls.slice(reset + 1, secondDiscovery).map(([name]) => name), ["history"]);
  assert.deepEqual(
    state.calls.filter(([name]) => name === "discover").map(([, provider]) => provider),
    ["luma", "connpass"],
  );
});

test("a failed provider reset records failure, skips discovery, and closes the owned page", async () => {
  let state = fixture({
    async discoverCandidates(provider) {
      state.calls.push(["discover", provider]);
      return [];
    },
  });
  const originalNavigate = state.dependencies.browserRail.navigate;
  state.dependencies.browserRail.navigate = async (owned, url) => {
    if (url === "about:blank") {
      state.calls.push(["navigate", owned.session_id, owned.target_id, owned.page.page_id, url]);
      throw new Error("provider reset failed");
    }
    return originalNavigate(owned, url);
  };

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-reset",
    providers: ["luma", "connpass"],
  }, state.dependencies);

  assert.deepEqual(state.calls.filter(([name]) => name === "discover").map(([, provider]) => provider), ["luma"]);
  assert.equal(result.status, "completed_no_effect");
  assert.equal(result.safe_reason, "provider_discovery_failed");
  assert.ok(state.calls.some(([name, row]) => (
    name === "history" && row.purpose === "navigate" && row.method === "browser_rail" && row.result === "failed"
  )));
  assert.deepEqual(state.calls.find(([name]) => name === "report").slice(1), [
    "completed_no_effect", "provider_discovery_failed",
  ]);
  assert.deepEqual(state.calls.filter(([name]) => name === "close"), [[
    "close", "session-owned-1", "TARGETOWNED1", "page-owned-1",
  ]]);
});

test("provider discovery failure continues and still reports the wake", async () => {
  const state = fixture({
    async discoverCandidates(provider) {
      state.calls.push(["discover", provider]);
      if (provider === "luma") {
        const error = new Error("provider changed");
        error.code = "CONNPASS_DETAIL_START_INVALID_FAILED";
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
    "completed_no_effect", "connpass_detail_start_invalid_failed",
  ]);
  assert.equal(state.calls.filter(([name]) => name === "close").length, 1);
  assert.equal(result.telegram_provider_id, "9001");
});

test("malformed provider candidates report the parent contract boundary", async () => {
  const state = fixture({
    async discoverCandidates(provider) {
      state.calls.push(["discover", provider]);
      return provider === "luma" ? [{ provider: "luma" }] : [];
    },
  });
  await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-1",
    providers: ["luma", "connpass"],
  }, state.dependencies);
  assert.deepEqual(state.calls.find(([name]) => name === "report").slice(1), [
    "completed_no_effect", "provider_candidate_contract_failed",
  ]);
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
      return Object.freeze({ status: "applied_bundle", bundle_id: "applied-bundle-1", completion_disposition: "created" });
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
      return Object.freeze({ status: "applied_bundle", bundle_id: "applied-bundle-cache", completion_disposition: "created" });
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
      return Object.freeze({ status: "applied_bundle", bundle_id: "applied-bundle-existing", completion_disposition: "created" });
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
  assert.deepEqual(state.calls.filter(([name]) => name === "navigate").map(([, , , , url]) => url), [
    "https://luma.example.test/one",
  ]);
});

function connpassRecoveryFixture(failure = null, preRegistered = false) {
  const canonicalUrl = "https://tokyo-builders.connpass.com/event/400028/";
  const joinUrl = "https://tokyo-builders.connpass.com/event/400028/join";
  const selected = Object.freeze({ provider: "connpass", event_ref: "connpass-event://event/400028", canonical_url: canonicalUrl, starts_at: "2026-08-12T10:00:00.000Z", ends_at: "2026-08-12T11:00:00.000Z" });
  let currentUrl = ""; let navigationCount = 0; let state;
  state = fixture({
    async discoverCandidates() { return [selected]; },
    async runCachedAction() { state.calls.push(["cache"]); return Object.freeze({ status: "cache_miss" }); },
    async runDirectAction() { state.calls.push(["direct"]); currentUrl = joinUrl; return Object.freeze({ status: "completed" }); },
    async runAgentFallback() { throw new Error("Connpass recovery must not invoke Harness"); },
    async readProviderState({ phase }) {
      state.calls.push(["readback", phase, currentUrl]);
      if (phase === "pre_submit") return Object.freeze({ status: preRegistered ? "registered" : "absent" });
      if (phase === "canonical_recovery" && failure === "readback") throw new Error("canonical readback unavailable");
      return Object.freeze({ status: phase === "canonical_recovery" && failure === "status" ? "absent" : "registered" });
    },
    async completeEvidence() { state.calls.push(["evidence", currentUrl]); if (currentUrl !== canonicalUrl) throw new Error("evidence requires canonical Connpass URL"); return Object.freeze({ status: "applied_bundle", bundle_id: "applied-bundle-connpass", completion_disposition: "created" }); },
  });
  const originalNavigate = state.dependencies.browserRail.navigate;
  state.dependencies.browserRail.navigate = async (owned, url) => { currentUrl = url; navigationCount += 1; if (navigationCount === 2 && failure === "navigation") throw new Error("canonical navigation unavailable"); return originalNavigate(owned, url); };
  return { state, canonicalUrl, joinUrl };
}

test("Connpass canonical recovery rereads the same page before evidence without duplicate Submit", async () => {
  const { state, canonicalUrl, joinUrl } = connpassRecoveryFixture();
  const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-connpass-recovery", providers: ["connpass"] }, state.dependencies);
  assert.deepEqual(result, { status: "applied_bundle", bundle_id: "applied-bundle-connpass", telegram_provider_id: "9001" });
  assert.deepEqual(state.calls.filter(([name]) => name === "navigate").map(([, , , , url]) => url), [canonicalUrl, canonicalUrl]);
  assert.deepEqual(state.calls.filter(([name]) => name === "readback").map(([, phase, url]) => [phase, url]), [["pre_submit", canonicalUrl], ["post_submit", joinUrl], ["canonical_recovery", canonicalUrl]]);
  for (const [name, count] of [["cache", 1], ["direct", 1], ["agent", 0], ["evidence", 1], ["close", 1]]) assert.equal(state.calls.filter(([entry]) => entry === name).length, count, name);
});

test("Connpass canonical recovery failures stop before evidence and Submit retry", async () => {
  for (const failure of ["status", "readback", "navigation"]) {
    const { state } = connpassRecoveryFixture(failure);
    const result = await runMinimalConnectorWake({ ownerToken: `owner-token-connector-recovery-${failure}`, providers: ["connpass"] }, state.dependencies);
    assert.deepEqual(result, { status: "circuit_open", safe_reason: "evidence_completion_failed", telegram_provider_id: "9001" }, failure);
    for (const [name, count] of [["cache", 1], ["direct", 1], ["agent", 0], ["evidence", 0], ["close", 1]]) assert.equal(state.calls.filter(([entry]) => entry === name).length, count, `${failure}:${name}`);
  }
});

test("Connpass pre-submit registered skips canonical recovery and every Submit path", async () => {
  const { state, canonicalUrl } = connpassRecoveryFixture(null, true);
  const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-connpass-existing", providers: ["connpass"] }, state.dependencies);
  assert.deepEqual(result, { status: "applied_bundle", bundle_id: "applied-bundle-connpass", telegram_provider_id: "9001" });
  assert.deepEqual(state.calls.filter(([name]) => name === "navigate").map(([, , , , url]) => url), [canonicalUrl]);
  assert.deepEqual(state.calls.filter(([name]) => name === "readback").map(([, phase]) => phase), ["pre_submit"]);
  for (const [name, count] of [["cache", 0], ["direct", 0], ["agent", 0], ["evidence", 1], ["close", 1]]) assert.equal(state.calls.filter(([entry]) => entry === name).length, count, name);
});

test("three consecutive candidate failures open the circuit before a fourth navigation", async () => {
  const state = fixture();

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-minimal-3",
    providers: ["luma", "connpass"],
    maxConsecutiveFailures: 3,
  }, state.dependencies);

  assert.equal(result.status, "circuit_open");
  assert.equal(result.safe_reason, "direct_action_unavailable");
  assert.equal(state.calls.filter(([name]) => name === "navigate").length, 4);
  assert.equal(state.calls.filter(([name, , , , url]) => name === "navigate" && url === "about:blank").length, 1);
  assert.equal(state.calls.filter(([name, , , , url]) => name === "navigate" && url !== "about:blank").length, 3);
  assert.equal(state.calls.filter(([name]) => name === "agent").length, 3);
  assert.deepEqual(state.calls.filter(([name]) => name === "report").at(-1), [
    "report", "circuit_open", "direct_action_unavailable",
  ]);
});

test("ambiguous agent effect stops the candidate sequence after one attempt", async () => {
  const state = fixture({
    async runAgentFallback({ candidate: selected, page: suppliedPage }) {
      assert.equal(suppliedPage.page_id, "page-owned-1");
      state.calls.push(["agent", selected.event_ref, suppliedPage.page_id]);
      return Object.freeze({ status: "failed", safe_reason: "effect_unknown" });
    },
  });
  state.dependencies.reportWake = async (report) => {
    state.calls.push(["report", report.status, report.safe_reason, report.consecutive_failure_count]);
    return Object.freeze({ telegram_provider_id: "9001" });
  };
  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-ambiguous",
    providers: ["luma"],
  }, state.dependencies);

  assert.deepEqual(result, Object.freeze({
    status: "circuit_open",
    safe_reason: "effect_unknown",
    telegram_provider_id: "9001",
  }));
  assert.deepEqual(state.calls.filter(([name]) => name === "discover").map(([, provider]) => provider), ["luma"]);
  assert.equal(state.calls.filter(([name]) => name === "agent").length, 1);
  assert.equal(state.calls.filter(([name, , , , url]) => name === "navigate" && url !== "about:blank").length, 1);
  assert.equal(state.calls.some(([name, eventRef]) => name === "agent" && eventRef.endsWith("/two")), false);
  assert.deepEqual(state.calls.filter(([name]) => name === "report").at(-1), [
    "report", "circuit_open", "effect_unknown", 1,
  ]);
});

test("ordinary agent action failure still uses the bounded three-candidate circuit", async () => {
  const state = fixture({
    async runAgentFallback({ candidate: selected, page: suppliedPage }) {
      assert.equal(suppliedPage.page_id, "page-owned-1");
      state.calls.push(["agent", selected.event_ref, suppliedPage.page_id]);
      return Object.freeze({ status: "failed", safe_reason: "agent_action_failed" });
    },
  });
  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-ordinary-agent-failure",
    providers: ["luma", "connpass"],
    maxConsecutiveFailures: 3,
  }, state.dependencies);

  assert.equal(result.status, "circuit_open");
  assert.equal(result.safe_reason, "direct_action_unavailable");
  assert.equal(state.calls.filter(([name]) => name === "agent").length, 3);
  assert.equal(state.calls.filter(([name, , , , url]) => name === "navigate" && url !== "about:blank").length, 3);
  assert.deepEqual(state.calls.filter(([name]) => name === "report").at(-1), [
    "report", "circuit_open", "direct_action_unavailable",
  ]);
});

test("valid direct safe reason survives failed fallback and opens the circuit with that exact reason", async () => {
  const state = fixture({
    async runDirectAction() { return Object.freeze({ status: "failed", safe_reason: "peatix_unknown_required_field" }); },
    async runAgentFallback() { return Object.freeze({ status: "failed", safe_reason: "agent_action_failed" }); },
  });
  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-safe-reason", providers: ["luma", "connpass"], maxConsecutiveFailures: 3,
  }, state.dependencies);
  assert.equal(result.safe_reason, "peatix_unknown_required_field");
  assert.deepEqual(state.calls.filter(([name]) => name === "report").at(-1), [
    "report", "circuit_open", "peatix_unknown_required_field",
  ]);
});

test("malformed direct safe reason becomes generic and does not reach the circuit report", async () => {
  const state = fixture({
    async runDirectAction() { return Object.freeze({ status: "failed", safe_reason: "https://peatix.com/event/private" }); },
    async runAgentFallback() { return Object.freeze({ status: "failed", safe_reason: "agent_action_failed" }); },
  });
  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-safe-generic", providers: ["luma", "connpass"], maxConsecutiveFailures: 3,
  }, state.dependencies);
  assert.equal(result.safe_reason, "direct_action_unverified");
  assert.doesNotMatch(result.safe_reason, /peatix\.com|private/);
});

test("discovery circuit reports the exact bounded provider stage", async () => {
  const state = fixture({
    async discoverCandidates(provider) {
      state.calls.push(["discover", provider]);
      const error = Object.assign(new Error("provider changed"), { code: "CONNPASS_DETAIL_START_INVALID_FAILED" });
      throw error;
    },
  });
  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-discovery-reason", providers: ["connpass"], maxConsecutiveFailures: 1,
  }, state.dependencies);
  assert.equal(result.safe_reason, "connpass_detail_start_invalid_failed");
  assert.deepEqual(state.calls.find(([name]) => name === "report").slice(1), [
    "circuit_open", "connpass_detail_start_invalid_failed",
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

test("calendar observation crossing the deadline does not create a browser target", async () => {
  let state;
  state = fixture({ async readCalendarGaps() { state.calls.push(["calendar"]); state.advance(600_001); return []; } });
  const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-calendar-deadline", providers: ["luma"], maxWakeMs: 600_000 }, state.dependencies);

  assert.deepEqual(result, { status: "circuit_open", safe_reason: "wake_deadline", telegram_provider_id: "9001" });
  assert.equal(state.calls.filter(([name]) => name === "open").length, 0); assert.equal(state.calls.filter(([name]) => name === "discover").length, 0);
});

test("browser target opening that crosses the deadline starts no provider action", async () => {
  let state;
  state = fixture();
  const originalOpen = state.dependencies.browserRail.open;
  state.dependencies.browserRail.open = async (...args) => { const owned = await originalOpen(...args); state.advance(600_001); return owned; };
  const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-open-deadline", providers: ["luma"], maxWakeMs: 600_000 }, state.dependencies);

  assert.deepEqual(result, { status: "circuit_open", safe_reason: "wake_deadline", telegram_provider_id: "9001" });
  assert.equal(state.calls.filter(([name]) => name === "open").length, 1); assert.equal(state.calls.filter(([name]) => name === "discover").length, 0); assert.equal(state.calls.filter(([name]) => name === "close").length, 1);
});

test("provider discovery crossing the deadline stops before candidate handling or the next provider", async () => {
  let state;
  state = fixture({ async discoverCandidates(provider) { state.calls.push(["discover", provider]); state.advance(600_001); return []; } });
  const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-discovery-deadline", providers: ["luma", "connpass"], maxWakeMs: 600_000 }, state.dependencies);

  assert.deepEqual(result, { status: "circuit_open", safe_reason: "wake_deadline", telegram_provider_id: "9001" });
  assert.deepEqual(state.calls.filter(([name]) => name === "discover").map(([, provider]) => provider), ["luma"]);
  assert.equal(state.calls.filter(([name, , , , url]) => name === "navigate" && url === "about:blank").length, 0);
});

test("candidate navigation crossing the deadline stops before provider readback or action", async () => {
  let state;
  state = fixture();
  const originalNavigate = state.dependencies.browserRail.navigate;
  state.dependencies.browserRail.navigate = async (owned, url) => { await originalNavigate(owned, url); if (url !== "about:blank") state.advance(600_001); };
  const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-candidate-deadline", providers: ["luma"], maxWakeMs: 600_000 }, state.dependencies);

  assert.deepEqual(result, { status: "circuit_open", safe_reason: "wake_deadline", telegram_provider_id: "9001" });
  assert.equal(state.calls.filter(([name]) => name === "readback").length, 0); assert.equal(state.calls.filter(([name]) => ["cache", "direct", "agent"].includes(name)).length, 0);
});

test("deadline-crossing uncaught boundary errors report once and clean up owned pages", async (t) => {
  const cases = [
    ["calendar", (state) => { state.dependencies.readCalendarGaps = async () => { state.advance(600_001); throw new Error("calendar raw"); }; }, 0],
    ["open", (state) => { const open = state.dependencies.browserRail.open; state.dependencies.browserRail.open = async (...args) => { await open(...args); state.advance(600_001); throw new Error("open raw"); }; }, 0],
    ["candidate-navigation", (state) => { const navigate = state.dependencies.browserRail.navigate; state.dependencies.browserRail.navigate = async (owned, url) => { if (url !== "about:blank") { state.advance(600_001); throw new Error("navigate raw"); } return navigate(owned, url); }; }, 1],
    ["pre-readback", (state) => { state.dependencies.readProviderState = async ({ phase }) => { if (phase === "pre_submit") { state.advance(600_001); throw new Error("pre-readback raw"); } return { status: "absent" }; }; }, 1],
    ["post-readback", (state) => { state.dependencies.runDirectAction = async () => ({ status: "completed" }); state.dependencies.readProviderState = async ({ phase }) => { if (phase === "pre_submit") return { status: "absent" }; state.advance(600_001); throw new Error("post-readback raw"); }; }, 1],
    ["save-repaired-actions", (state) => { state.dependencies.runDirectAction = async () => ({ status: "failed", safe_reason: "direct_action_failed" }); state.dependencies.runAgentFallback = async () => ({ status: "completed", repaired_actions: [{ purpose: "submit", method: "ax_click" }] }); state.dependencies.readProviderState = async ({ phase }) => ({ status: phase === "pre_submit" ? "absent" : "registered" }); state.dependencies.saveRepairedActions = async () => { state.advance(600_001); throw new Error("save raw"); }; }, 1],
  ];
  for (const [name, configure, closeCount] of cases) {
    await t.test(name, async () => {
      const state = fixture(); configure(state);
      const result = await runMinimalConnectorWake({ ownerToken: `owner-token-connector-throw-${name}`, providers: ["luma"], maxWakeMs: 600_000 }, state.dependencies);
      assert.deepEqual(result, { status: "circuit_open", safe_reason: "wake_deadline", telegram_provider_id: "9001" });
      assert.equal(state.calls.filter(([entry]) => entry === "report").length, 1);
      assert.equal(state.calls.filter(([entry]) => entry === "close").length, closeCount);
    });
  }
});

test("an uncaught boundary error before the deadline remains the original rejection without reporting", async () => {
  const raw = new Error("raw before deadline");
  const state = fixture({ async readCalendarGaps() { throw raw; } });
  await assert.rejects(
    runMinimalConnectorWake({ ownerToken: "owner-token-connector-raw-before-deadline", providers: ["luma"] }, state.dependencies),
    (error) => error === raw,
  );
  assert.equal(state.calls.filter(([entry]) => entry === "report").length, 0);
  assert.equal(state.calls.filter(([entry]) => entry === "close").length, 0);
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

test("registered parent pre-readback composes real evidence recovery with zero submit paths", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-runner-evidence-"));
  const png = Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), Buffer.alloc(6_000, 4)]);
  const candidate = { provider: "peatix", event_ref: "peatix-event://event/5075819", canonical_url: "https://peatix.com/event/5075819", title: "Runner Public Event", starts_at: "2026-08-10T10:00:00.000Z", ends_at: "2026-08-10T11:00:00.000Z", venue_name: "Tokyo", ticket_id: "public-ticket" };
  const receipt = { id: "google-runner-evidence", htmlLink: "https://www.google.com/calendar/event?eid=runner-evidence" }; let event = null; let calendarCreates = 0; let crashReadback = true; let evidenceRecords = 0; let messageCalls = 0; let photoCalls = 0; let cacheCalls = 0; let directCalls = 0; let harnessCalls = 0; let lastBundle = null; const registered = new Set();
  const calendar = { async findConnectorEvents() { if (!event) return []; if (crashReadback) { crashReadback = false; throw new Error("Calendar readback crash"); } return [event]; }, async createConnectorEvent() { calendarCreates += 1; event = receipt; return receipt; } };
  const artifactSha = createHash("sha256").update(png).digest("hex"); const evidenceStore = { async record(input) { evidenceRecords += 1; const id = createHash("sha256").update(`${input.tenantId}\n${input.eventRef}\n${input.observedAt}\n${artifactSha}`).digest("hex"); return { external_receipt_ref: `provider-receipt://peatix/${id}`, artifact_ref: `object://sha256/${artifactSha}` }; }, async readExternalReceipt(tenant, ref) { return { kind: "provider_response", provider_id: String(ref).split("/").at(-1) }; }, async readArtifact() { return png; } };
  const page = { async goto() {}, url() { return "about:blank"; }, async evaluate() { return true; }, async screenshot() { return png; } };
  const wake = (times, sendMessage, sendPhoto) => runMinimalConnectorWake({ ownerToken: "owner-token-runner-evidence", providers: ["peatix"] }, {
    now: () => "2026-08-07T02:00:00.000Z", browserRail: { async open() { return { session_id: "session-runner-evidence", target_id: "TARGETRUNNEREVIDENCE", page_websocket: "ws://127.0.0.1:9222/devtools/page/TARGETRUNNEREVIDENCE", page }; }, async navigate() {}, async close() {} },
    async readCalendarGaps() { return []; }, async discoverCandidates() { return [candidate]; }, async readProviderState() { registered.add(candidate.event_ref); return { status: "registered" }; },
    async runCachedAction() { cacheCalls += 1; throw new Error("cache must not run"); }, async runDirectAction() { directCalls += 1; throw new Error("direct must not run"); }, async runAgentFallback() { harnessCalls += 1; throw new Error("Harness must not run"); },
    async completeEvidence(input) { let index = 0; const chain = createMinimalEvidenceChain({ stateDir, tenantId: "dais-local", calendar, calendarId: "primary", telegramTarget: "private-target", peatixEvidenceStore: evidenceStore, now: () => new Date(times[Math.min(index++, times.length - 1)]), sendMessage, sendPhoto }); lastBundle = await chain.completeEvidence(input); return lastBundle; },
    async saveRepairedActions() { return { status: "saved" }; }, async reportWake() { return { telegram_provider_id: "9001" }; }, async recordAction() {},
  });
  try {
    const first = await wake(["2026-08-07T08:30:00.000Z", "2026-08-07T08:31:00.000Z"], async () => ({ messageId: 9401 }), async () => ({ messageId: 9402 }));
    assert.deepEqual(first, { status: "circuit_open", safe_reason: "evidence_completion_failed", telegram_provider_id: "9001" });
    const second = await wake(["2026-08-07T08:31:00.000Z"], async () => { messageCalls += 1; return { messageId: 9401 }; }, async () => { photoCalls += 1; throw new Error("photo interruption"); });
    assert.deepEqual(second, { status: "circuit_open", safe_reason: "evidence_completion_failed", telegram_provider_id: "9001" });
    const result = await wake(["2026-08-07T08:32:00.000Z"], async () => { messageCalls += 1; return { messageId: 9401 }; }, async () => { photoCalls += 1; return { messageId: 9402 }; });
    assert.equal(result.status, "applied_bundle"); assert.equal(lastBundle.created_at, "2026-08-07T08:30:00.000Z"); assert.deepEqual([registered.size, evidenceRecords, calendarCreates, messageCalls, photoCalls, cacheCalls, directCalls, harnessCalls, fs.readdirSync(path.join(stateDir, "applied-bundles")).length], [1, 1, 1, 1, 2, 0, 0, 0, 1]);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("reused evidence skips Submit and continues the same owned page to a later candidate", async () => {
  let state;
  state = fixture({
    async discoverCandidates(provider) { state.calls.push(["discover", provider]); return [candidate("luma", "reused"), candidate("luma", "new")]; },
    async readProviderState({ candidate: selected, page: suppliedPage }) { assert.equal(suppliedPage, state.page); state.calls.push(["readback", selected.event_ref, suppliedPage.page_id]); return Object.freeze({ status: "registered", provider_receipt_id: `receipt-${selected.event_ref}` }); },
    async runCachedAction() { throw new Error("cache must not run for a registered candidate"); },
    async runDirectAction() { throw new Error("direct must not run for a registered candidate"); },
    async runAgentFallback() { throw new Error("Harness must not run for a registered candidate"); },
    async completeEvidence({ candidate: selected }) { state.calls.push(["evidence", selected.event_ref]); const newCandidate = selected.event_ref.endsWith("/new"); return Object.freeze({ status: "applied_bundle", bundle_id: `applied-bundle-${newCandidate ? "new" : "reused"}`, completion_disposition: newCandidate ? "created" : "reused" }); },
  });
  const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-13b-reuse", providers: ["luma"] }, state.dependencies);
  assert.deepEqual(result, { status: "applied_bundle", bundle_id: "applied-bundle-new", telegram_provider_id: "9001" });
  assert.equal(state.calls.filter(([name]) => name === "cache" || name === "direct" || name === "agent").length, 0);
  assert.deepEqual(state.calls.filter(([name]) => name === "evidence").map(([, eventRef]) => eventRef), ["luma-event://event/reused", "luma-event://event/new"]);
  const navigations = state.calls.filter(([name]) => name === "navigate");
  assert.deepEqual(navigations.map((call) => call.slice(1, 4)), [["session-owned-1", "TARGETOWNED1", "page-owned-1"], ["session-owned-1", "TARGETOWNED1", "page-owned-1"]]);
  assert.deepEqual(navigations.map(([, , , , url]) => url), ["https://luma.example.test/reused", "https://luma.example.test/new"]);
  assert.equal(state.calls.filter(([name]) => name === "report").length, 1);
});

test("evidence completion error becomes one bounded terminal report without retry or Submit", async () => {
  let evidenceCalls = 0;
  const state = fixture({
    async discoverCandidates() { return [candidate("luma", "evidence-error")]; },
    async readProviderState() {
      return Object.freeze({ status: "registered", provider_receipt_id: "existing-receipt" });
    },
    async runCachedAction() { throw new Error("cache must not run"); },
    async runDirectAction() { throw new Error("direct must not run"); },
    async runAgentFallback() { throw new Error("Harness must not run"); },
    async completeEvidence() {
      evidenceCalls += 1;
      throw new Error("raw evidence failure should stay out of the report");
    },
    async reportWake(report) {
      state.calls.push(["report", report.status, report.safe_reason, report.consecutive_failure_count]);
      return Object.freeze({ telegram_provider_id: "9015" });
    },
  });

  const result = await runMinimalConnectorWake({
    ownerToken: "owner-token-connector-13c-error",
    providers: ["luma"],
    maxConsecutiveFailures: 3,
  }, state.dependencies);

  assert.deepEqual(result, {
    status: "circuit_open",
    safe_reason: "evidence_completion_failed",
    telegram_provider_id: "9015",
  });
  assert.equal(evidenceCalls, 1);
  assert.equal(state.calls.filter(([name]) => ["cache", "direct", "agent"].includes(name)).length, 0);
  assert.deepEqual(state.calls.filter(([name]) => name === "report"), [[
    "report", "circuit_open", "evidence_completion_failed", 1,
  ]]);
  assert.equal(state.calls.filter(([name]) => name === "close").length, 1);
  assert.doesNotMatch(JSON.stringify(state.calls), /raw evidence failure/);
});

test("malformed evidence result or disposition reports once and cleans up without Submit", async () => {
  const cases = [
    ["result-null", null, "evidence_result_invalid"],
    ["result-array", [], "evidence_result_invalid"],
    ["result-string", "bundle", "evidence_result_invalid"],
    ["missing", { status: "applied_bundle", bundle_id: "bundle" }, "evidence_disposition_invalid"],
    ["unknown", { status: "applied_bundle", bundle_id: "bundle", completion_disposition: "unknown" }, "evidence_disposition_invalid"],
    ["non-string", { status: "applied_bundle", bundle_id: "bundle", completion_disposition: new String("reused") }, "evidence_disposition_invalid"],
    ["status", { status: "completed_no_effect", bundle_id: "bundle", completion_disposition: "reused" }, "evidence_disposition_invalid"],
    ["bundle-id", { status: "applied_bundle", bundle_id: "", completion_disposition: "reused" }, "evidence_disposition_invalid"],
  ];
  for (const [name, evidenceResult, safeReason] of cases) {
    let state = fixture({
      async discoverCandidates() { return [candidate("luma", `invalid-${name}`)]; },
      async readProviderState() { return Object.freeze({ status: "registered", provider_receipt_id: "existing-receipt" }); },
      async runCachedAction() { throw new Error("cache must not run"); }, async runDirectAction() { throw new Error("direct must not run"); },
      async runAgentFallback() { throw new Error("Harness must not run"); },
      async completeEvidence() { return evidenceResult; },
      async reportWake(report) {
        state.calls.push(["report", report.status, report.safe_reason, report.consecutive_failure_count]);
        return Object.freeze({ telegram_provider_id: "9014" });
      },
    });
    const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-13b-invalid", providers: ["luma"] }, state.dependencies);
    assert.deepEqual(result, { status: "circuit_open", safe_reason: safeReason, telegram_provider_id: "9014" });
    assert.deepEqual(state.calls.filter(([entry]) => entry === "report"), [["report", "circuit_open", safeReason, 0]]); assert.equal(state.calls.filter(([entry]) => ["cache", "direct", "agent"].includes(entry)).length, 0); assert.equal(state.calls.filter(([entry]) => entry === "close").length, 1);
  }
});

test("evidence completion error uses real production operations for one durable positive report", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-runner-13b-invalid-operations-"));
  const sent = [];
  const operations = createMinimalProductionOperations({
    stateDir, wakeId: "wake-connector-13c-error-operations", telegramTarget: "private-target",
    now: () => new Date("2026-08-11T08:30:00.000Z"),
    async sendMessage(message, options) { sent.push({ message, options }); return { messageId: 7315 }; },
  });
  let state = fixture({
    async readCalendarGaps() { return []; },
    async discoverCandidates() { return [candidate("luma", "evidence-error-operations")]; },
    async readProviderState() { return Object.freeze({ status: "registered", provider_receipt_id: "existing-receipt" }); },
    async runCachedAction() { throw new Error("cache must not run"); }, async runDirectAction() { throw new Error("direct must not run"); },
    async runAgentFallback() { throw new Error("Harness must not run"); },
    async completeEvidence() { throw new Error("private raw evidence operation failure"); },
    recordAction: operations.recordAction, reportWake: operations.reportWake,
  });
  try {
    const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-13c-ops", providers: ["luma"] }, state.dependencies);
    assert.deepEqual(result, { status: "circuit_open", safe_reason: "evidence_completion_failed", telegram_provider_id: "7315" });
    assertDurableWakeReport(stateDir, "7315");
    assert.equal(sent.length, 1);
    assert.equal(sent[0].message.includes("private raw evidence operation failure"), false);
    assert.equal(fs.readFileSync(path.join(stateDir, "wake-reports.jsonl"), "utf8").includes("private raw evidence operation failure"), false);
    assert.equal(JSON.parse(fs.readFileSync(path.join(stateDir, "wake-reports.jsonl"), "utf8")).consecutive_failure_count, 1);
    assert.equal(state.calls.filter(([name]) => name === "close").length, 1);
    assert.equal(state.calls.filter(([name]) => ["cache", "direct", "agent"].includes(name)).length, 0);
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});

test("real runner production operations persist one positive wake delivery and dedupe duplicates", async () => {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-runner-13b-operations-"));
  const sent = [];
  const operations = createMinimalProductionOperations({
    stateDir,
    wakeId: "wake-connector-13b-operations",
    telegramTarget: "private-target",
    now: () => new Date("2026-08-11T08:30:00.000Z"),
    async sendMessage(message, options) { sent.push({ message, options }); return { messageId: 7311 }; },
  });
  let state = fixture({
    async readCalendarGaps() { return []; },
    async discoverCandidates() { return [candidate("luma", "reused"), candidate("luma", "reused-later")]; },
    async readProviderState() { return Object.freeze({ status: "registered", provider_receipt_id: "existing-receipt" }); },
    async runCachedAction() { throw new Error("cache must not run"); },
    async runDirectAction() { throw new Error("direct must not run"); },
    async runAgentFallback() { throw new Error("Harness must not run"); },
    async completeEvidence() { return Object.freeze({ status: "applied_bundle", bundle_id: "reused-bundle", completion_disposition: "reused" }); },
    recordAction: operations.recordAction,
    reportWake: operations.reportWake,
  });
  try {
    const result = await runMinimalConnectorWake({ ownerToken: "owner-token-connector-13b-ops", providers: ["luma"] }, state.dependencies);
    assert.deepEqual(result, { status: "completed_no_effect", safe_reason: "existing_bundles_reused", telegram_provider_id: "7311" });
    const duplicate = await operations.reportWake({ status: "completed_no_effect", safe_reason: "existing_bundles_reused", consecutive_failure_count: 0 });
    assert.deepEqual(duplicate, { telegram_provider_id: "7311" });
    assert.equal(sent.length, 1);
    assertDurableWakeReport(stateDir, "7311");
  } finally { fs.rmSync(stateDir, { recursive: true, force: true }); }
});
