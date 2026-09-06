"use strict";

const GEMINI_25_FLASH_INPUT_PER_M = 0.30;
const GEMINI_25_FLASH_OUTPUT_PER_M = 2.50;
const SEARCH_GROUNDING_PER_PROMPT = 0.035;

function count(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

function geminiUsageEvents(response, context = {}) {
  const usage = response && response.usageMetadata || {};
  const input = count(usage.promptTokenCount);
  const output = count(usage.candidatesTokenCount);
  const total = count(usage.totalTokenCount) ?? (input != null && output != null ? input + output : 0);
  const rawEstimated = input == null || output == null
    ? 0 : input / 1_000_000 * GEMINI_25_FLASH_INPUT_PER_M
      + output / 1_000_000 * GEMINI_25_FLASH_OUTPUT_PER_M;
  const estimated = Number(rawEstimated.toFixed(12));
  const success = Boolean(response && Array.isArray(response.candidates) && response.candidates.length);
  const common = { tenantId: context.tenantId || "unknown", feature: context.feature || "unknown" };
  const events = [{
    ...common, provider: "gemini", outcome: success ? "success" : "failure",
    failureClass: success ? null : (context.failureClass || "empty_response"),
    providerUnits: total, providerUnit: "tokens", estimatedCostUsd: estimated,
    meta: { model: context.model || "gemini-2.5-flash", input_tokens: input,
      output_tokens: output, estimate_status: input == null || output == null ? "unavailable" : "estimated" },
  }];
  if (context.grounded) events.push({
    ...common, provider: "google_search_grounding", outcome: success ? "success" : "failure",
    failureClass: success ? null : (context.failureClass || "empty_response"),
    providerUnits: 1, providerUnit: "grounded_prompt", estimatedCostUsd: SEARCH_GROUNDING_PER_PROMPT,
    meta: { model: context.model || "gemini-2.5-flash", pricing_basis: "list_price_after_free_rpd" },
  });
  return events;
}

module.exports = { geminiUsageEvents };
