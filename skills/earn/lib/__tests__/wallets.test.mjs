import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseWalletManifest,
  loadWalletManifest,
  walletsForVenue,
  addressForVenue,
} from '../wallets.mjs';

const MANIFEST = {
  instance: 'claude-p',
  wallets: [
    { id: 'base-main', chain: 'base', venue: 'evm', address: '0x810f', label: 'main' },
    { id: 'polymarket', chain: 'polygon', venue: 'polymarket', address: '0x904B', label: 'PM deposit' },
    { id: 'hl', chain: 'hyperliquid', venue: 'hyperliquid', address: '0x810f', label: 'HL margin' },
  ],
};

test('a skill asks which of MY wallets can spend at MY venue', () => {
  const m = parseWalletManifest(MANIFEST);
  assert.equal(addressForVenue(m, 'polymarket'), '0x904B');
  assert.equal(addressForVenue(m, 'hyperliquid'), '0x810f');
  assert.equal(addressForVenue(m, 'solana'), null, 'a venue this instance has no wallet for');
  assert.equal(walletsForVenue(m, 'polymarket').length, 1);
});

test('a private key pasted into the manifest is dropped, never propagated', () => {
  const m = parseWalletManifest({
    wallets: [
      { id: 'leak', chain: 'base', address: '0xbad', privateKey: '0xdeadbeef' },
      { id: 'ok', chain: 'base', venue: 'evm', address: '0xgood' },
    ],
  });
  assert.equal(m.wallets.length, 1);
  assert.equal(m.wallets[0].address, '0xgood');
  assert.ok(!JSON.stringify(m).includes('deadbeef'), 'no key material may survive parsing');
});

test('one malformed row never blinds the instance to the wallets it CAN read', () => {
  const m = parseWalletManifest({
    wallets: [
      { id: 'junk' }, // no chain, no address
      { chain: 'moonbase-alpha', address: '0x1' }, // chain we cannot read a balance from
      { id: 'good', chain: 'polygon', venue: 'polymarket', address: '0x904B' },
    ],
  });
  assert.deepEqual(m.wallets.map((w) => w.id), ['good']);
});

test('a missing or unreadable manifest yields an empty list, never throws', () => {
  assert.deepEqual(loadWalletManifest('/nonexistent/home'), { instance: null, wallets: [] });
  assert.deepEqual(
    loadWalletManifest('/x', () => 'not json at all'),
    { instance: null, wallets: [] },
  );
  assert.deepEqual(loadWalletManifest(''), { instance: null, wallets: [] });
});

test('venue defaults to the chain when omitted', () => {
  const m = parseWalletManifest({ wallets: [{ id: 's', chain: 'solana', address: '8Fpq' }] });
  assert.equal(addressForVenue(m, 'solana'), '8Fpq');
});
