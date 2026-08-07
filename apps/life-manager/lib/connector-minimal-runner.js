"use strict";

const PURPOSE = /^(?:navigate|observe|fill|submit|readback)$/;
const METHOD = /^[a-z][a-z0-9_]{1,63}$/;

function invalid() {
  throw new Error("Connector minimal runner invalid");
}

function exactInstant(value) {
  const instant = String(value || "");
  if (!Number.isFinite(Date.parse(instant)) || new Date(Date.parse(instant)).toISOString() !== instant) invalid();
  return instant;
}

function positiveInteger(value, fallback) {
  const candidate = value == null ? fallback : Number(value);
  if (!Number.isInteger(candidate) || candidate < 1) invalid();
  return candidate;
}

function dependencies(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid();
  const required = [
    "now", "readCalendarGaps", "discoverCandidates", "runDirectAction",
    "runCachedAction", "runAgentFallback", "readProviderState", "completeEvidence",
    "saveRepairedActions", "reportWake", "recordAction",
  ];
  for (const name of required) if (typeof input[name] !== "function") invalid();
  if (
    !input.browserRail || typeof input.browserRail !== "object"
    || typeof input.browserRail.open !== "function"
    || typeof input.browserRail.navigate !== "function"
    || typeof input.browserRail.close !== "function"
  ) invalid();
  return input;
}

function config(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) invalid();
  const ownerToken = String(input.ownerToken || "").trim();
  if (!/^[A-Za-z0-9._-]{16,200}$/.test(ownerToken)) invalid();
  if (
    !Array.isArray(input.providers) || input.providers.length < 1
    || input.providers.length > 20
    || input.providers.some((provider) => !/^[a-z][a-z0-9_-]{1,31}$/.test(String(provider)))
  ) invalid();
  return Object.freeze({
    ownerToken,
    providers: Object.freeze(input.providers.map(String)),
    maxConsecutiveFailures: positiveInteger(input.maxConsecutiveFailures, 3),
    maxWakeMs: positiveInteger(input.maxWakeMs, 600_000),
    maxAgentSteps: positiveInteger(input.maxAgentSteps, 10),
  });
}

function verifiedOwned(value) {
  const targetId = String(value && value.target_id || "");
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || !/^[A-Za-z0-9._-]{3,128}$/.test(String(value.session_id || ""))
    || !/^[A-Za-z0-9._-]{3,128}$/.test(targetId)
    || String(value.page_websocket || "") !== `ws://127.0.0.1:9222/devtools/page/${targetId}`
    || !value.page || typeof value.page !== "object"
  ) invalid();
  return value;
}

function verifiedCandidates(value, provider) {
  if (!Array.isArray(value) || value.length > 500) invalid();
  for (const candidate of value) {
    if (
      !candidate || typeof candidate !== "object" || Array.isArray(candidate)
      || candidate.provider !== provider
      || typeof candidate.canonical_url !== "string"
      || !candidate.canonical_url.startsWith("https://")
      || typeof candidate.event_ref !== "string"
    ) invalid();
  }
  return value;
}

function registered(value) {
  return Boolean(value && ["registered", "pending"].includes(value.status));
}

function safeDiscoveryReason(error) {
  const code = String(error && error.code || "");
  if (code === "PROVIDER_CANDIDATE_CONTRACT_FAILED") return "provider_candidate_contract_failed";
  return /^CONNPASS_(?:CALENDAR_NAVIGATION|CALENDAR_BINDINGS|CALENDAR_BINDING_VALIDATION|CALENDAR_ROWS_CONTRACT|DETAIL_NAVIGATION|DETAIL_READ|DETAIL_IDENTITY_MISMATCH|CANDIDATE_VALIDATION|DISCOVERY_RESULT_CONTRACT|CALENDAR_CONFLICT_CHECK)_FAILED$/.test(code)
    ? code.toLowerCase() : "provider_discovery_failed";
}

async function runMinimalConnectorWake(input = {}, injected = {}) {
  const settings = config(input);
  const deps = dependencies(injected);
  const startedAt = Date.parse(exactInstant(deps.now()));
  let owned = null;
  let consecutiveFailures = 0;
  let providerDiscoveryFailed = false;
  let discoveryFailureReason = "provider_discovery_failed";

  const elapsed = () => Date.parse(exactInstant(deps.now())) - startedAt;
  const deadlineReached = () => elapsed() >= settings.maxWakeMs;

  async function action(purpose, method, task) {
    if (!PURPOSE.test(purpose) || !METHOD.test(method)) invalid();
    const timestamp = exactInstant(deps.now());
    const actionStartedAt = Date.parse(timestamp);
    try {
      const value = await task();
      await deps.recordAction(Object.freeze({
        purpose,
        method,
        timestamp,
        result: "success",
        duration_ms: Math.max(0, Date.parse(exactInstant(deps.now())) - actionStartedAt),
      }));
      return value;
    } catch (error) {
      await deps.recordAction(Object.freeze({
        purpose,
        method,
        timestamp,
        result: "failed",
        duration_ms: Math.max(0, Date.parse(exactInstant(deps.now())) - actionStartedAt),
      }));
      throw error;
    }
  }

  async function finish(status, safeReason, extra = {}) {
    const delivery = await deps.reportWake(Object.freeze({
      status,
      safe_reason: safeReason,
      consecutive_failure_count: consecutiveFailures,
    }));
    const telegramProviderId = String(delivery && delivery.telegram_provider_id || "").trim();
    if (!telegramProviderId) invalid();
    if (status === "applied_bundle") {
      return Object.freeze({
        status,
        bundle_id: String(extra.bundle_id || ""),
        telegram_provider_id: telegramProviderId,
      });
    }
    return Object.freeze({ status, safe_reason: safeReason, telegram_provider_id: telegramProviderId });
  }

  try {
    const gaps = await action("observe", "calendar_busy", () => deps.readCalendarGaps());
    if (!Array.isArray(gaps)) invalid();
    owned = verifiedOwned(await deps.browserRail.open(Object.freeze({ ownerToken: settings.ownerToken })));

    for (const provider of settings.providers) {
      let candidates;
      try {
        const discovered = await action(
          "observe", "provider_discovery", () => deps.discoverCandidates(provider, gaps, owned.page),
        );
        try { candidates = verifiedCandidates(discovered, provider); }
        catch {
          const error = new Error("Provider candidate contract failed");
          error.code = "PROVIDER_CANDIDATE_CONTRACT_FAILED";
          throw error;
        }
      } catch (error) {
        providerDiscoveryFailed = true;
        discoveryFailureReason = safeDiscoveryReason(error);
        consecutiveFailures += 1;
        if (consecutiveFailures >= settings.maxConsecutiveFailures) {
          return finish("circuit_open", "consecutive_failure_limit");
        }
        continue;
      }
      for (const selected of candidates) {
        if (deadlineReached()) return finish("circuit_open", "wake_deadline");
        await action("navigate", "browser_rail", () => (
          deps.browserRail.navigate(owned, selected.canonical_url)
        ));

        let operation;
        let providerState = await action("readback", "provider_state", () => deps.readProviderState({
          provider,
          candidate: selected,
          page: owned.page,
          phase: "pre_submit",
        }));
        let usedFallback = false;
        if (!registered(providerState)) providerState = null;
        if (!providerState) {
        try {
          operation = await action("submit", "provider_cache", () => deps.runCachedAction({
            provider,
            candidate: selected,
            page: owned.page,
          }));
        } catch {
          operation = Object.freeze({ status: "failed", safe_reason: "cached_action_failed" });
        }
        if (operation && operation.status === "completed" && registered(operation.provider_state)) {
          providerState = operation.provider_state;
        }

        if (!providerState) {
        try {
          operation = await action("submit", "provider_direct", () => deps.runDirectAction({
            provider,
            candidate: selected,
            page: owned.page,
          }));
        } catch {
          operation = Object.freeze({ status: "failed", safe_reason: "direct_action_failed" });
        }

        if (!operation || operation.status !== "completed") {
          if (deadlineReached()) return finish("circuit_open", "wake_deadline");
          try {
            operation = await action("submit", "browser_harness", () => deps.runAgentFallback({
              provider,
              candidate: selected,
              page: owned.page,
              pageWebsocket: owned.page_websocket,
              maxSteps: settings.maxAgentSteps,
              expectedState: "registered_or_pending",
            }));
            usedFallback = operation && operation.status === "completed";
          } catch {
            operation = Object.freeze({ status: "failed", safe_reason: "agent_action_failed" });
          }
        }

        if (operation && operation.status === "completed") {
          providerState = await action("readback", "provider_state", () => deps.readProviderState({
            provider,
            candidate: selected,
            page: owned.page,
            phase: "post_submit",
          }));
        }
        }
        }

        if (registered(providerState)) {
          const repairedActions = usedFallback && operation && Array.isArray(operation.repaired_actions)
            ? operation.repaired_actions : [];
          if (repairedActions.length > 0) {
            const saved = await deps.saveRepairedActions({
              provider,
              candidate: selected,
              page: owned.page,
              providerState,
              repairedActions,
            });
            if (!saved || saved.status !== "saved") invalid();
          }
          const bundle = await deps.completeEvidence({
            provider,
            candidate: selected,
            page: owned.page,
            providerState,
            repairedActions,
          });
          if (!bundle || bundle.status !== "applied_bundle" || !String(bundle.bundle_id || "")) invalid();
          return finish("applied_bundle", "applied_bundle", bundle);
        }

        consecutiveFailures += 1;
        if (consecutiveFailures >= settings.maxConsecutiveFailures) {
          return finish("circuit_open", "consecutive_failure_limit");
        }
      }
    }
    return finish("completed_no_effect", providerDiscoveryFailed
      ? discoveryFailureReason : "providers_exhausted");
  } finally {
    if (owned) await deps.browserRail.close(owned);
  }
}

module.exports = { runMinimalConnectorWake };
