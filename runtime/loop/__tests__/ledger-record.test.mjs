// PROP-007 — ledger-record.mjs unit tests
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatRecord } from '../ledger-record.mjs';

// PROP-007: formatRecord produces valid JSON that round-trips
test('PROP-007: formatRecord returns valid JSON string with newline', () => {
  const fields = { ts: 1000, wake_id: 'abc', kind: 'wake', sleep_s: 120 };
  const result = formatRecord(fields);
  assert.ok(typeof result === 'string', 'must be a string');
  assert.ok(result.endsWith('\n'), 'must end with newline');
  const parsed = JSON.parse(result.trim());
  assert.deepEqual(parsed, fields);
});

// PROP-007: round-trips through JSON.parse
test('PROP-007: formatRecord output round-trips JSON.parse without error', () => {
  const fields = { ts: 1234567890, wake_id: '01HZ', kind: 'narrate', sleep_s: 60, profitable: false };
  const result = formatRecord(fields);
  const parsed = JSON.parse(result);
  assert.equal(parsed.kind, 'narrate');
  assert.equal(parsed.profitable, false);
});

// PROP-007: required fields ts, wake_id, kind, sleep_s must be present
test('PROP-007: required fields ts, wake_id, kind, sleep_s present in output', () => {
  const fields = { ts: 999, wake_id: 'W1', kind: 'shutdown', sleep_s: 0 };
  const parsed = JSON.parse(formatRecord(fields));
  assert.ok('ts' in parsed);
  assert.ok('wake_id' in parsed);
  assert.ok('kind' in parsed);
  assert.ok('sleep_s' in parsed);
});

// PROP-007: extra fields are preserved
test('PROP-007: extra fields are preserved in JSON output', () => {
  const fields = { ts: 1, wake_id: 'x', kind: 'wake', sleep_s: 0, profitable: true, model: 'gpt-4o-mini' };
  const parsed = JSON.parse(formatRecord(fields));
  assert.equal(parsed.profitable, true);
  assert.equal(parsed.model, 'gpt-4o-mini');
});

// PROP-007: formatRecord does not throw on empty string fields
test('PROP-007: handles empty string fields without throwing', () => {
  const fields = { ts: 0, wake_id: '', kind: 'wake_error', sleep_s: 60, error: '' };
  assert.doesNotThrow(() => formatRecord(fields));
});
