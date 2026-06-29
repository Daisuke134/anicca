// RED-first: pure earn-slot predicate + strategy mapping (REQ-1/REQ-3/REQ-4 NEW-003).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isEarnSlot, earnStrategyFor } from '../earn-slot.mjs';
test('isEarnSlot: legacy action slots are earn', () => { for (const s of ['earn','yield','hl_trade','x402_sell','token_launch']) assert.equal(isEarnSlot(s), true, s); });
test('isEarnSlot: any earn/<sub> is earn', () => { for (const s of ['earn/gig','earn/clip','earn/affiliate','earn/video','earn/audit','earn/_probe']) assert.equal(isEarnSlot(s), true, s); });
test('isEarnSlot: non-earn slots NOT earn', () => { for (const s of ['cook','report','self/issue-dev','self/spawn','economy/ubi','',undefined,null]) assert.equal(isEarnSlot(s), false, String(s)); });
test('earnStrategyFor: legacy map', () => { assert.equal(earnStrategyFor('yield'),'yield'); assert.equal(earnStrategyFor('hl_trade'),'hl'); assert.equal(earnStrategyFor('x402_sell'),'x402'); assert.equal(earnStrategyFor('token_launch'),'token'); });
test('earnStrategyFor: fat earn → null', () => assert.equal(earnStrategyFor('earn'), null));
test('earnStrategyFor: earn/<sub> → <sub>', () => { assert.equal(earnStrategyFor('earn/gig'),'gig'); assert.equal(earnStrategyFor('earn/_probe'),'_probe'); });
test('earnStrategyFor: non-earn → null', () => assert.equal(earnStrategyFor('cook'), null));
