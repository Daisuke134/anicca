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
  if (Array.isArray(toolCalls) && toolCalls.length > 0) {
    const tc = toolCalls[0];
    if (tc?.function?.name) return tc;
  }

  // SCAVENGE (copied from BlockRunAI/Franklin src/agent/llm.ts isRoleplayedJsonToolCallText +
  // repair/scavenge.ts): free models like glm-4.7 often emit the tool call as TEXT content instead of
  // the tool_calls field — e.g. {"type":"function","name":"run_skill","parameters":{...}} or
  // {"name":"run_skill","arguments":{...}}. Recover it so the model's decision is not lost.
  return scavengeRoleplayedToolCall(message.content);
}

function scavengeRoleplayedToolCall(content) {
  if (typeof content !== 'string') return null;
  // free models (glm-4.7 etc) emit the tool call as TEXT, in several shapes:
  //   1. bare JSON: {"name":"run_skill","arguments":{...}}
  //   2. XML-wrapped: <tool_call>\n{"name":...}\n</tool_call>  (glm-4.7's actual output)
  //   3. JSON inside surrounding prose / markdown fences
  // Collect candidate JSON objects and return the first that names a tool.
  for (const candidate of jsonObjectCandidates(content)) {
    const parsed = parseMaybeTruncated(candidate);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) continue;
    const name = typeof parsed.name === 'string' ? parsed.name
      : (typeof parsed.function === 'string' ? parsed.function : null);
    if (!name) continue;
    // the call's arguments may be under `parameters` or `arguments`
    const callArgs = parsed.parameters ?? parsed.arguments ?? {};
    return { function: { name, arguments: callArgs } };
  }
  return null;
}

/**
 * Parse a JSON object, repairing the common free-model defect of a TRUNCATED tail: the model
 * emits e.g. {"name":"run_skill","arguments":{"slot":"hl_trade","args":{...}}  — missing the final
 * closing brace(s) (glm-4.7 verified 2026-07-04). Try as-is; on failure, close any open string and
 * append the missing } to balance, then re-parse. Returns the object or null.
 */
function parseMaybeTruncated(candidate) {
  try { return JSON.parse(candidate); } catch { /* fall through to repair */ }
  let inStr = false, esc = false, depth = 0;
  for (const ch of candidate) {
    if (inStr) {
      if (esc) esc = false;
      else if (ch === '\\') esc = true;
      else if (ch === '"') inStr = false;
    } else if (ch === '"') inStr = true;
    else if (ch === '{') depth++;
    else if (ch === '}') depth--;
  }
  if (depth <= 0) return null;               // not a missing-tail case
  let repaired = candidate;
  if (inStr) repaired += '"';                // close a dangling string
  repaired += '}'.repeat(depth);             // balance the braces
  try { return JSON.parse(repaired); } catch { return null; }
}

/**
 * Yield candidate JSON-object substrings from free-form model text, most-specific first:
 * whatever is inside <tool_call>…</tool_call> tags, then every brace-balanced {...} span.
 */
function* jsonObjectCandidates(text) {
  const stripFences = (s) => s.replace(/```(?:json)?/gi, '').trim();
  // 1. XML-style tool_call wrappers
  const tagRe = /<tool_call>([\s\S]*?)<\/tool_call>/gi;
  let m;
  while ((m = tagRe.exec(text)) !== null) {
    const inner = stripFences(m[1]);
    if (inner.startsWith('{')) yield inner;
  }
  // 2. every brace-balanced object span in the raw text (handles prose around the JSON)
  for (let i = 0; i < text.length; i++) {
    if (text[i] !== '{') continue;
    let depth = 0, inStr = false, esc = false;
    for (let j = i; j < text.length; j++) {
      const ch = text[j];
      if (inStr) {
        if (esc) esc = false;
        else if (ch === '\\') esc = true;
        else if (ch === '"') inStr = false;
      } else if (ch === '"') inStr = true;
      else if (ch === '{') depth++;
      else if (ch === '}') {
        depth--;
        if (depth === 0) { yield text.slice(i, j + 1); i = j; break; }
      }
    }
  }
  // 3. fallback: from the first '{' to end-of-text — a TRUNCATED bare object (no closing brace,
  //    not in a tag) that step 2 never balanced. parseMaybeTruncated repairs it.
  const first = text.indexOf('{');
  if (first !== -1) yield stripFences(text.slice(first));
}
