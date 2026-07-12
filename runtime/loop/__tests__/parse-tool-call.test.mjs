// PROP-010 — parse-tool-call.mjs unit tests
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseToolCall } from '../parse-tool-call.mjs';

// PROP-010: well-formed tool call object -> { slot, args }
// args is the SKILL's args, NOT the run_skill wrapper. {slot:'earn'} alone → args {} (no skill params).
test('PROP-010: parses well-formed run_skill tool call', () => {
  const response = {
    choices: [{
      message: {
        tool_calls: [{
          function: { name: 'run_skill', arguments: JSON.stringify({ slot: 'earn' }) }
        }]
      }
    }]
  };
  const result = parseToolCall(response);
  assert.ok(result !== null);
  assert.equal(result.slot, 'earn');
  assert.deepEqual(result.args, {}); // slot is the wrapper, not a skill arg
});

// PROP-010: nested {slot, args:{...}} → the SKILL's args are the nested object (the model's decision)
test('PROP-010: extracts nested skill args (the model decision)', () => {
  const response = {
    choices: [{ message: { tool_calls: [{
      function: { name: 'run_skill', arguments: JSON.stringify({ slot: 'earn', args: { strategy: 'hl', coin: 'ETH' } }) }
    }] } }]
  };
  const result = parseToolCall(response);
  assert.equal(result.slot, 'earn');
  assert.deepEqual(result.args, { strategy: 'hl', coin: 'ETH' });
});

// PROP-010: flattened {slot, strategy} → args is everything but slot
test('PROP-010: flattened params (slot + strategy at top level)', () => {
  const response = {
    choices: [{ message: { tool_calls: [{
      function: { name: 'run_skill', arguments: JSON.stringify({ slot: 'earn', strategy: 'x402' }) }
    }] } }]
  };
  const result = parseToolCall(response);
  assert.equal(result.slot, 'earn');
  assert.deepEqual(result.args, { strategy: 'x402' });
});

// PROP-010: text-only response (no tool call) -> null
test('PROP-010: text-only response returns null', () => {
  const response = {
    choices: [{
      message: { content: 'Hello, I am thinking.', tool_calls: undefined }
    }]
  };
  assert.equal(parseToolCall(response), null);
});

// PROP-010: empty tool_calls array -> null
test('PROP-010: empty tool_calls array returns null', () => {
  const response = {
    choices: [{ message: { tool_calls: [] } }]
  };
  assert.equal(parseToolCall(response), null);
});

// PROP-010: malformed JSON arguments -> null (not throw)
test('PROP-010: malformed JSON arguments returns null', () => {
  const response = {
    choices: [{
      message: {
        tool_calls: [{
          function: { name: 'run_skill', arguments: '{bad json' }
        }]
      }
    }]
  };
  assert.equal(parseToolCall(response), null);
});

// PROP-010: null response -> null
test('PROP-010: null response returns null', () => {
  assert.equal(parseToolCall(null), null);
});

// PROP-010: undefined response -> null
test('PROP-010: undefined response returns null', () => {
  assert.equal(parseToolCall(undefined), null);
});

// PROP-010: missing choices -> null
test('PROP-010: missing choices returns null', () => {
  assert.equal(parseToolCall({}), null);
});

// PROP-010: wrong function name still returns parsed (slot from args)
test('PROP-010: sleep tool call parsed correctly', () => {
  const response = {
    choices: [{
      message: {
        tool_calls: [{
          function: { name: 'sleep', arguments: JSON.stringify({ seconds: 60 }) }
        }]
      }
    }]
  };
  const result = parseToolCall(response);
  assert.ok(result !== null);
  assert.equal(result.slot, 'sleep');
  assert.equal(result.args.seconds, 60);
});

// PROP-010: claude -p JSON output format (result field) -> parsed
test('PROP-010: claude -p JSON output with tool_calls in result', () => {
  // claude --output-format json returns {result, cost_usd, ...}
  // If the result contains a tool_calls block, parse it
  const claudeOutput = {
    result: JSON.stringify({
      choices: [{
        message: {
          tool_calls: [{
            function: { name: 'run_skill', arguments: JSON.stringify({ slot: 'earn' }) }
          }]
        }
      }]
    }),
    cost_usd: 0.001,
  };
  // parseToolCall should handle both raw OpenAI response and claude -p output
  // When given claude -p output (has result field), extract and parse the inner response
  const result = parseToolCall(claudeOutput);
  assert.ok(result !== null);
  assert.equal(result.slot, 'earn');
});

// --- a text-mode brain answers with the bare envelope (2026-07-13) ----------------------------
// `claude -p` has no tool-call channel; it emits the envelope as TEXT, so there is no OpenAI chat
// wrapper. Reading only choices[0].message.tool_calls threw the answer away and logged `narrate` —
// the loop recorded "the brain chose to do nothing" while the brain had chosen to trade.
test('parses the bare {"tool_calls":[...]} a text-mode brain returns', () => {
  const claudeEnvelope = {
    type: 'result',
    result: JSON.stringify({
      tool_calls: [
        { function: { name: 'run_skill', arguments: '{"slot":"earn/polymarket-trade"}' } },
      ],
    }),
  };

  const call = parseToolCall(claudeEnvelope);

  assert.equal(call.slot, 'earn/polymarket-trade', 'the slot the brain actually chose');
});

test('the OpenAI-wrapped shape (proxy brain) still parses', () => {
  const openai = {
    choices: [{ message: { tool_calls: [{ function: { name: 'run_skill', arguments: '{"slot":"yield"}' } }] } }],
  };
  assert.equal(parseToolCall(openai).slot, 'yield');
});
