// node:test — RED (Phase 2a, feature gig-reality-verify, fresh-adversary FIND-001 fix).
// REQ-006 (specs/behavioral-spec.md): a DETERMINISTIC, reproducible navigation helper committed in
// this repo (no freeform LLM-improvised navigation, no dangling cross-repo path reference).
// scripts/cdp_nav_snapshot.py does not exist yet -> RED.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const NAV_HELPER = path.join(DIR, 'scripts', 'cdp_nav_snapshot.py');
const SNAPSHOT = path.join(DIR, 'scripts', 'cdp_snapshot.py');

test('scripts/cdp_nav_snapshot.py exists', () => {
  assert.ok(fs.existsSync(NAV_HELPER), 'scripts/cdp_nav_snapshot.py missing');
});

test('cdp_nav_snapshot.py: python syntax is valid (py_compile)', () => {
  assert.ok(fs.existsSync(NAV_HELPER), 'scripts/cdp_nav_snapshot.py missing');
  execFileSync('python3', ['-m', 'py_compile', NAV_HELPER]);
});

test('cdp_nav_snapshot.py: performs a real CDP Page.navigate call', () => {
  const src = fs.readFileSync(NAV_HELPER, 'utf8');
  assert.ok(/Page\.navigate/.test(src), 'no Page.navigate CDP call found');
});

test('cdp_nav_snapshot.py: waits for the page to finish loading (loadEventFired or readyState poll)', () => {
  const src = fs.readFileSync(NAV_HELPER, 'utf8');
  assert.ok(/Page\.loadEventFired/.test(src) || /readyState/.test(src), 'no load-wait (loadEventFired/readyState) found');
});

test('cdp_nav_snapshot.py: captures rendered DOM evidence for hidden targets', () => {
  const src = fs.readFileSync(NAV_HELPER, 'utf8');
  assert.ok(/document\.body\.innerText/.test(src), 'no rendered DOM evidence capture found');
});

test('cdp_nav_snapshot.py: appends a trajectory row (parity with cdp_snapshot.py)', () => {
  const src = fs.readFileSync(NAV_HELPER, 'utf8');
  assert.ok(src.includes('trajectory.jsonl'), 'does not write trajectory.jsonl');
});

test('cdp_nav_snapshot.py: navigate()/get_tab() logic is copied IN, not referenced out-of-repo', () => {
  const src = fs.readFileSync(NAV_HELPER, 'utf8');
  assert.ok(!/~\/gig\/cdp_lib48\.py/.test(src), 'must not reference the out-of-repo ~/gig/cdp_lib48.py path');
  assert.ok(/def get_tab/.test(src), 'get_tab() logic must be defined IN this file (copied in)');
});

test('cdp_snapshot.py: no longer references the dangling out-of-repo cdp_lib48.py path', () => {
  const src = fs.readFileSync(SNAPSHOT, 'utf8');
  assert.ok(!/cdp_lib48/.test(src), 'cdp_snapshot.py must not reference the out-of-repo cdp_lib48 module (dangling cross-repo comment)');
});
