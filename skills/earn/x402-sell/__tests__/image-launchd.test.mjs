import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

test('franklin1 image boot pins its identity, local port, public origin, and additive funnel path', () => {
  const boot = fs.readFileSync(path.join(ROOT, 'image-franklin1-boot.sh'), 'utf8');

  assert.match(boot, /\. \/Users\/anicca\/\.openclaw\/\.env/);
  assert.ok(boot.includes('export ANICCA_HOME="$HOME/.blockrun"'));
  assert.match(boot, /unset BLOCKRUN_WALLET_KEY/);
  assert.ok(boot.includes('export X402_PAYTO="0x3EcCAD24794ca298D25378E9902A251322ea8749"'));
  assert.ok(boot.includes('export X402_IMAGE_PORT="8093"'));
  assert.ok(boot.includes('export X402_IMAGE_PUBLIC_URL="https://aniccanomac-mini-1.tail7a0ba4.ts.net"'));
  assert.ok(boot.includes('tailscale funnel --bg --https=443 --set-path=/image http://127.0.0.1:8093/image'));
  assert.match(boot, /exec \/usr\/bin\/env node "\$DIR\/image-server\.mjs"/);
});

test('franklin1 image plist is a persistent per-instance service', () => {
  const label = 'ai.anicca.image-franklin1';
  const plist = fs.readFileSync(path.join(ROOT, 'launchd', `${label}.plist`), 'utf8');

  assert.ok(plist.includes(`<string>${label}</string>`));
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/image-franklin1-boot.sh</string>'));
  assert.match(plist, /<key>KeepAlive<\/key><true\/>/);
  assert.match(plist, /<key>RunAtLoad<\/key><true\/>/);
  assert.match(plist, /<key>ThrottleInterval<\/key><integer>15<\/integer>/);
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/logs/image-franklin1.out.log</string>'));
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/logs/image-franklin1.err.log</string>'));
});

test('franklin2 image boot pins its identity, local port, public origin, and additive funnel path', () => {
  const boot = fs.readFileSync(path.join(ROOT, 'image-franklin2-boot.sh'), 'utf8');

  assert.match(boot, /\. \/Users\/anicca\/\.openclaw\/\.env/);
  assert.ok(boot.includes('export ANICCA_HOME="$HOME/.franklin2-home/.blockrun"'));
  assert.match(boot, /unset BLOCKRUN_WALLET_KEY/);
  assert.ok(boot.includes('export X402_PAYTO="0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9"'));
  assert.ok(boot.includes('export X402_IMAGE_PORT="8094"'));
  assert.ok(boot.includes('export X402_IMAGE_PUBLIC_URL="https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000"'));
  assert.ok(boot.includes('tailscale funnel --bg --https=10000 --set-path=/image http://127.0.0.1:8094/image'));
  assert.match(boot, /exec \/usr\/bin\/env node "\$DIR\/image-server\.mjs"/);
});

test('franklin2 image plist is a persistent per-instance service', () => {
  const label = 'ai.anicca.image-franklin2';
  const plist = fs.readFileSync(path.join(ROOT, 'launchd', `${label}.plist`), 'utf8');

  assert.ok(plist.includes(`<string>${label}</string>`));
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/image-franklin2-boot.sh</string>'));
  assert.match(plist, /<key>KeepAlive<\/key><true\/>/);
  assert.match(plist, /<key>RunAtLoad<\/key><true\/>/);
  assert.match(plist, /<key>ThrottleInterval<\/key><integer>15<\/integer>/);
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/logs/image-franklin2.out.log</string>'));
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/logs/image-franklin2.err.log</string>'));
});

test('claude-p image boot pins its identity, local port, public origin, and additive funnel path', () => {
  const boot = fs.readFileSync(path.join(ROOT, 'image-claude-p-boot.sh'), 'utf8');

  assert.match(boot, /\. \/Users\/anicca\/\.openclaw\/\.env/);
  assert.ok(boot.includes('export ANICCA_HOME="$HOME/.anicca-founder"'));
  assert.match(boot, /unset BLOCKRUN_WALLET_KEY/);
  assert.ok(boot.includes('export X402_PAYTO="0x810F6D61F7606dEEE2657d3083E150a222Bc29C5"'));
  assert.ok(boot.includes('export X402_IMAGE_PORT="8095"'));
  assert.ok(boot.includes('export X402_IMAGE_PUBLIC_URL="https://aniccanomac-mini-1.tail7a0ba4.ts.net:8443"'));
  assert.ok(boot.includes('tailscale funnel --bg --https=8443 --set-path=/image http://127.0.0.1:8095/image'));
  assert.match(boot, /exec \/usr\/bin\/env node "\$DIR\/image-server\.mjs"/);
});

test('claude-p image plist is a persistent per-instance service', () => {
  const label = 'ai.anicca.image-claude-p';
  const plist = fs.readFileSync(path.join(ROOT, 'launchd', `${label}.plist`), 'utf8');

  assert.ok(plist.includes(`<string>${label}</string>`));
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/image-claude-p-boot.sh</string>'));
  assert.match(plist, /<key>KeepAlive<\/key><true\/>/);
  assert.match(plist, /<key>RunAtLoad<\/key><true\/>/);
  assert.match(plist, /<key>ThrottleInterval<\/key><integer>15<\/integer>/);
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/logs/image-claude-p.out.log</string>'));
  assert.ok(plist.includes('<string>/Users/anicca/anicca/skills/earn/x402-sell/logs/image-claude-p.err.log</string>'));
});
