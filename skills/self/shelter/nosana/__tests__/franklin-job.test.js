// node:test — franklin-job: S12 definition builder. The secret must live ONLY in env (delivered
// confidentially), never in cmd; the definition must pass the structural validator.
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildFranklinJobDefinition, buildFranklinBootScript } from "../franklin-job.mjs";
import { validateJobDefinition } from "../job-definition.mjs";

const FAKE_SECRET = "5".repeat(88); // base58-shaped, clearly fake

test("definition is structurally valid, exposes one port, env-carries the secret", () => {
  const def = buildFranklinJobDefinition({ solanaSessionB58: FAKE_SECRET });
  const v = validateJobDefinition(def);
  assert.equal(v.valid, true, v.errors.join("; "));
  assert.equal(def.ops[0].args.env.SOLANA_SESSION, FAKE_SECRET);
  assert.equal(def.ops[0].args.expose, 8080);
  assert.equal(def.ops[0].args.image, "docker.io/library/node:20-alpine");
});

test("secret never appears in cmd — env is the only channel", () => {
  const def = buildFranklinJobDefinition({ solanaSessionB58: FAKE_SECRET });
  const cmdText = JSON.stringify(def.ops[0].args.cmd);
  assert.equal(cmdText.includes(FAKE_SECRET), false);
  assert.match(cmdText, /\$SOLANA_SESSION/); // script reads it from env at runtime
  assert.equal(typeof def.ops[0].args.cmd, "string"); // string cmd — array form died on the node (live A/B)
});

test("boot script: installs franklin, hard spend cap, keep-alive proof server", () => {
  const s = buildFranklinBootScript({ model: "openai/gpt-5-mini", maxSpendUsd: 0.02, prompt: "hello", exposePort: 8080 });
  assert.match(s, /npm i -g @blockrun\/franklin/);
  assert.match(s, /--max-spend 0\.02/);
  assert.match(s, /\.solana-session/);
  assert.match(s, /createServer/);
});

test("missing secret refused", () => {
  assert.throws(() => buildFranklinJobDefinition({}), /solanaSessionB58/);
});

test('renewer step: only present when asked, discovers itself on-chain, never leaks the secret', () => {
  const off = buildFranklinBootScript({ model: 'm', maxSpendUsd: 0.01, prompt: 'p', exposePort: 8080 });
  assert.equal(/jobs\.extend/.test(off), false, 'no renewer unless requested');

  const on = buildFranklinBootScript({ model: 'm', maxSpendUsd: 0.01, prompt: 'p', exposePort: 8080, withRenewer: true });
  assert.match(on, /@nosana\/sdk/);
  assert.match(on, /jobs\.all\(\{project:me,state:1\}\)/); // self-discovery, no injected job id
  assert.match(on, /jobs\.extend/);
  assert.match(on, /process\.env\.SOLANA_SESSION/); // key read from env at runtime
  assert.equal(on.includes('MARGIN=180'), true);
  assert.equal(on.includes('CEIL=21600'), true); // 6h unattended ceiling
});

test('definition with renew=true still keeps the secret out of cmd', () => {
  const def = buildFranklinJobDefinition({ solanaSessionB58: FAKE_SECRET, renew: true });
  assert.equal(JSON.stringify(def.ops[0].args.cmd).includes(FAKE_SECRET), false);
  assert.equal(def.ops[0].args.env.SOLANA_SESSION, FAKE_SECRET);
});

test('boot script is valid /bin/sh — the provider wraps it in sh -c (regression: "&;" broke the renewer)', async () => {
  const { execFileSync } = await import('node:child_process');
  const os = await import('node:os');
  const fs = await import('node:fs');
  const path = await import('node:path');
  for (const withRenewer of [false, true]) {
    const script = buildFranklinBootScript({ model: 'm', maxSpendUsd: 0.01, prompt: 'p', exposePort: 8080, withBaseKey: true, withRenewer });
    const f = path.join(os.tmpdir(), `boot-${withRenewer}.sh`);
    fs.writeFileSync(f, script);
    execFileSync('/bin/sh', ['-n', f]); // throws on a syntax error
  }
});

test('boot script never uses a heredoc — the "; " join silently swallows the rest of the script', () => {
  const s = buildFranklinBootScript({ model: 'm', maxSpendUsd: 0.01, prompt: 'p', exposePort: 8080, withBaseKey: true, withRenewer: true });
  assert.equal(/<<'?[A-Z_]+'?/.test(s), false, 'a heredoc in a joined one-line script loses its terminator');
});

test('the buy-house tool is delivered whole and is valid JS', async () => {
  const s = buildFranklinBootScript({ model: 'm', maxSpendUsd: 0.01, prompt: 'p', exposePort: 8080, withBaseKey: true });
  const m = s.match(/printf %s "([A-Za-z0-9+/=]+)" \| base64 -d/);
  assert.ok(m, 'tool must be embedded as base64');
  const src = Buffer.from(m[1], 'base64').toString('utf8');
  assert.match(src, /export async function buyHouse/);
  assert.match(src, /DEFAULT_MAX_SPEND_USD/);
});

test('nothing written to the world-readable proof page can carry key material', () => {
  const s = buildFranklinBootScript({ model: 'm', maxSpendUsd: 0.01, prompt: 'p', exposePort: 8080, withBaseKey: true, withRenewer: true });
  // A library that echoes its input inside an exception would otherwise publish the key to the
  // whole internet. Every append that carries dynamic text must pass a secret through a scrub.
  const lines = s.split('\n').filter((l) => l.includes('appendFileSync("/tmp/proof.txt"'));
  assert.ok(lines.length >= 1, 'expected writes to the proof file');
  for (const line of lines) {
    const dynamic = /e\.message|\+t\b|\+ *String\(t\)|r\.status/.test(line);
    if (!dynamic) continue;
    assert.match(line, /scrub\(|\[redacted\]/, `unscrubbed dynamic write: ${line.slice(0, 80)}`);
  }
});

test("the container renewer checks money before extending, not only the clock", () => {
  const script = buildFranklinBootScript({
    model: "m", maxSpendUsd: 0.02, prompt: "p", exposePort: 8080,
    withBaseKey: true, withRenewer: true, leaseSecondsHint: 600,
  });
  // The guard must sit between the ceiling/margin test and the extend call — a floor placed after
  // the spend is not a floor. This is the exact shape that let job AzUFmVa5 drain the wallet.
  const guard = script.indexOf("const bal=await money()");
  const extend = script.indexOf("sdk.jobs.extend(mine,ADD,false)");
  assert.ok(guard > 0, "renewer has no balance check");
  assert.ok(guard < extend, "the balance check must run BEFORE the extension is paid for");
  assert.match(script, /RES=0\.34/);
  assert.match(script, /nosXBVoaCTtYdLvKY6Csb4AC8JCdQKKAaWYtx2ZMoo7/);
});

test("the container signs the same heartbeat the project's own verifier accepts", () => {
  // The container used to emit {kind:"heartbeat", cycle, slot, blockhash, sig, pubkey}, which
  // verifyHeartbeatEntry rejects outright. Evidence that only an ad-hoc checker can read is
  // evidence a process wrote about itself — the exact thing heartbeats exist to rule out.
  const script = buildFranklinBootScript({
    model: "m", maxSpendUsd: 0.02, prompt: "p", exposePort: 8080,
    withBaseKey: true, withRenewer: true, leaseSecondsHint: 600,
  });
  assert.match(script, /kind:"shelter-heartbeat"/);
  assert.match(script, /jobAddress:job/);
  // Signed field order must match MESSAGE_KEYS in heartbeat.mjs exactly, or the bytes differ.
  assert.match(script, /\{blockhash:bh,cycle:c,jobAddress:job,payer:me,slot,ts\}/);
});
