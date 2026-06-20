/**
 * share.test.mjs — buildIssue() is a pure result→{title,body,labels} transform.
 * (spec 25 O8 — the SHARE step of verify→record→share.)
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildIssue } from '../share.mjs';

test('win → title says WORKS + earned amount, body has tx', () => {
  const { title, body } = buildIssue({ kind: 'win', tool: 'earn/yield', earned_usd: 0.0003, tx: '0xabc', verdict: 'real' });
  assert.match(title, /earn: earn\/yield WORKS/);
  assert.match(title, /\$0\.0003/);
  assert.match(title, /\[win\]/);
  assert.match(body, /0xabc/);
  assert.match(body, /earn\/yield/);
});

test('slop → title says slop + verdict', () => {
  const { title } = buildIssue({ kind: 'slop', tool: 'cook/some-repo', verdict: 'gated' });
  assert.match(title, /slop: cook\/some-repo/);
  assert.match(title, /gated/);
  assert.match(title, /\[slop\]/);
});

test('help → title carries the note', () => {
  const { title } = buildIssue({ kind: 'help', tool: 'earn/swap', note: 'Base ETH=0 cannot pay gas' });
  assert.match(title, /help: earn\/swap/);
  assert.match(title, /Base ETH=0/);
});

test('default kind = finding; missing fields do not throw', () => {
  const { title, body } = buildIssue({ tool: 'x' });
  assert.match(title, /finding: x/);
  assert.ok(typeof body === 'string' && body.length > 0);
});

test('empty/garbage input is safe', () => {
  const a = buildIssue(null);
  const b = buildIssue({});
  assert.ok(a.title && b.title);
});
