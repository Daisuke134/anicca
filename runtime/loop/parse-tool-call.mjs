/**
 * parse-tool-call.mjs — Pure: parseToolCall(rawResponse) → {slot, args}|null
 *
 * REQ-001, REQ-003: Extracts at most one tool call from a model response.
 * Handles both raw OpenAI chat-completion JSON and claude --output-format json output.
 *
 * PROP-010
 */

/**
 * Parse a model response to extract the first tool call.
 *
 * Accepts:
 *   - Standard OpenAI chat-completions response: { choices: [{ message: { tool_calls: [...] } }] }
 *   - claude -p JSON output: { result: "<json string>", cost_usd: ... }
 *     where result is either an OpenAI-compatible JSON string or plain text.
 *
 * Returns null for:
 *   - Text-only responses (no tool calls)
 *   - Malformed JSON arguments
 *   - null / undefined input
 *
 * @param {object|null|undefined} rawResponse
 * @returns {{ slot: string, args: object }|null}
 */
export function parseToolCall(rawResponse) {
  if (rawResponse == null) return null;

  // Handle claude -p JSON output format: { result: "...", cost_usd: ... }
  const inner = extractInnerResponse(rawResponse);
  if (inner == null) return null;

  const toolCall = extractFirstToolCall(inner);
  if (!toolCall) return null;

  try {
    const parsed = typeof toolCall.function.arguments === 'string'
      ? JSON.parse(toolCall.function.arguments)
      : toolCall.function.arguments;

    const slot = parsed.slot ?? toolCall.function.name;

    // The run_skill schema is { slot, args } — the SKILL's args (e.g. {strategy:"hl",coin:"ETH"}) live
    // under parsed.args. The old code returned the WHOLE parsed object as args, so a downstream
    // `args.strategy` read undefined and the model's decision was lost (→ yield default). Extract the
    // nested args; fall back to parsed-minus-slot for models that flatten params at the top level.
    let args;
    if (parsed && typeof parsed.args === 'object' && parsed.args !== null) {
      args = parsed.args;
    } else if (parsed && typeof parsed === 'object') {
      const { slot: _slot, ...rest } = parsed;
      args = rest;
    } else {
      args = {};
    }
    return { slot, args };
  } catch {
    return null;
  }
}

/**
 * If the response is a claude -p output (has `result` string field),
 * try to parse the result as an OpenAI-compatible response.
 * Otherwise return the response as-is.
 */
function extractInnerResponse(response) {
  if (typeof response !== 'object' || response === null) return null;

  // claude -p JSON output: { result: "...", cost_usd: ... }
  if (typeof response.result === 'string') {
    try {
      return JSON.parse(response.result);
    } catch {
      // result is plain text, not JSON — no tool call
      return null;
    }
  }

  return response;
}

/**
 * Extract the first tool_call entry from an OpenAI-compatible response.
 */
function extractFirstToolCall(response) {
  if (!response || !Array.isArray(response.choices) || response.choices.length === 0) {
    return null;
  }
  const message = response.choices[0]?.message;
  if (!message) return null;

  const toolCalls = message.tool_calls;
  if (!Array.isArray(toolCalls) || toolCalls.length === 0) return null;

  const tc = toolCalls[0];
  if (!tc?.function?.name) return null;

  return tc;
}
