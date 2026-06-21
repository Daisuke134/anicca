import { test } from "node:test";
import assert from "node:assert/strict";
import { normalizeRecipients, monthlyToFlowRate, planDistribution } from "../gda-distribute.mjs";

const A="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const M1="0x1111111111111111111111111111111111111111";
const M2="0x2222222222222222222222222222222222222222";
const POOL="0x6DA13Bde224A05a288748d857b9e7DDEffd1dE08";

test("normalizeRecipients: dedupe (case) + drop invalid", () => {
  const r=normalizeRecipients([M1, M1.toUpperCase(), M2, "0xbad", "", null]);
  assert.equal(r.length, 2);
});
test("monthlyToFlowRate: >0 bigint; rejects <=0 / tiny", () => {
  assert.ok(monthlyToFlowRate(100) > 0n);
  assert.throws(()=>monthlyToFlowRate(0), /must be/);
  assert.throws(()=>monthlyToFlowRate(0.0000001), /per-second/);
});
test("planDistribution: existing pool -> updateMemberUnits per member + distributeFlow", () => {
  const p=planDistribution({ token:A, admin:POOL, pool:POOL, recipients:[M1,M2], flowRatePerSec:1000n });
  assert.equal(p.memberCount, 2);
  const kinds=p.calls.map(c=>c.kind);
  assert.deepEqual(kinds, ["updateMemberUnits","updateMemberUnits","distributeFlow"]);
  assert.ok(p.calls.every(c=>c.data.startsWith("0x")));
});
test("planDistribution: no valid recipients -> refuses (no empty-pool stream)", () => {
  assert.throws(()=>planDistribution({ token:A, admin:POOL, pool:POOL, recipients:["0xbad"], flowRatePerSec:1000n }), /no valid recipient/);
});
test("planDistribution: createPool prepends createPool call", () => {
  const p=planDistribution({ token:A, admin:POOL, pool:POOL, recipients:[M1], flowRatePerSec:1000n, createPool:true });
  assert.equal(p.calls[0].kind, "createPool");
});
test("planDistribution: flowRate 0/absent -> members set, no distribute", () => {
  const p=planDistribution({ token:A, admin:POOL, pool:POOL, recipients:[M1,M2] });
  assert.deepEqual(p.calls.map(c=>c.kind), ["updateMemberUnits","updateMemberUnits"]);
});
