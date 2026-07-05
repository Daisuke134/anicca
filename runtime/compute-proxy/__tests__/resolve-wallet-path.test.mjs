// resolve-wallet-path.test.mjs — exercises the REAL shipped bash logic (#26 EQUALIZE, R4).
//
// This does NOT hand-write the resolution in JS (that was FIND-002: a test that can't catch the
// bug). It sources runtime/compute-proxy/resolve-wallet-path.sh in a child bash with a controlled
// HOME + ANICCA_HOME + real on-disk files, and asserts the path the shipped code actually returns.
// The headline case (FIND-001) is: a fresh spawn on a machine that ALREADY has a legacy wallet
// must get its OWN path, never inherit the legacy key.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HELPER = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'resolve-wallet-path.sh');

// Run the shipped helper with a controlled env; return the resolved wallet path (trimmed).
function resolve({ home, aniccaHome }) {
  const env = { HOME: home };
  if (aniccaHome !== undefined) env.ANICCA_HOME = aniccaHome;
  const out = execFileSync('bash', ['-c', `. "${HELPER}"; resolve_wallet_path`], { env, encoding: 'utf8' });
  return out.trim();
}

// Make a throwaway HOME dir; optionally drop a legacy wallet file at $HOME/.automaton/wallet.json.
function mkHome({ legacy = false, perHome = null } = {}) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'eqwp-'));
  if (legacy) {
    fs.mkdirSync(path.join(home, '.automaton'), { recursive: true });
    fs.writeFileSync(path.join(home, '.automaton', 'wallet.json'), JSON.stringify({ privateKey: '0xdead' }));
  }
  if (perHome) {
    fs.mkdirSync(path.join(perHome, '.automaton'), { recursive: true });
    fs.writeFileSync(path.join(perHome, '.automaton', 'wallet.json'), JSON.stringify({ privateKey: '0xbeef' }));
  }
  return home;
}

test('FIND-001 regression: fresh spawn (distinct ANICCA_HOME) NEVER inherits the legacy wallet', () => {
  const home = mkHome({ legacy: true }); // machine already has a running instance's legacy wallet
  const spawn = fs.mkdtempSync(path.join(os.tmpdir(), 'eqspawn-'));
  const got = resolve({ home, aniccaHome: spawn });
  assert.equal(got, path.join(spawn, '.automaton', 'wallet.json'));
  assert.notEqual(got, path.join(home, '.automaton', 'wallet.json'));
});

test('default-home instance keeps its legacy wallet (automaton preserved, zero identity change)', () => {
  const home = mkHome({ legacy: true });
  const got = resolve({ home, aniccaHome: path.join(home, '.anicca') }); // effective == $HOME/.anicca
  assert.equal(got, path.join(home, '.automaton', 'wallet.json')); // legacy retained
});

test('default-home instance with UNSET ANICCA_HOME also keeps legacy', () => {
  const home = mkHome({ legacy: true });
  const got = resolve({ home }); // ANICCA_HOME unset -> effective defaults to $HOME/.anicca
  assert.equal(got, path.join(home, '.automaton', 'wallet.json'));
});

test('per-home wallet already present -> used as-is (never the legacy)', () => {
  const home = mkHome({ legacy: true });
  const spawn = fs.mkdtempSync(path.join(os.tmpdir(), 'eqspawn-'));
  fs.mkdirSync(path.join(spawn, '.automaton'), { recursive: true });
  fs.writeFileSync(path.join(spawn, '.automaton', 'wallet.json'), JSON.stringify({ privateKey: '0xbeef' }));
  const got = resolve({ home, aniccaHome: spawn });
  assert.equal(got, path.join(spawn, '.automaton', 'wallet.json'));
});

test('no legacy anywhere, non-default home -> its own path (for a fresh generation)', () => {
  const home = mkHome({ legacy: false });
  const spawn = fs.mkdtempSync(path.join(os.tmpdir(), 'eqspawn-'));
  const got = resolve({ home, aniccaHome: spawn });
  assert.equal(got, path.join(spawn, '.automaton', 'wallet.json'));
});

test('default-home instance where per-home wallet exists -> per-home wins over legacy', () => {
  const home = mkHome({ legacy: true });
  const perHome = path.join(home, '.anicca');
  fs.mkdirSync(path.join(perHome, '.automaton'), { recursive: true });
  fs.writeFileSync(path.join(perHome, '.automaton', 'wallet.json'), JSON.stringify({ privateKey: '0xbeef' }));
  const got = resolve({ home, aniccaHome: perHome });
  assert.equal(got, path.join(perHome, '.automaton', 'wallet.json'));
});
