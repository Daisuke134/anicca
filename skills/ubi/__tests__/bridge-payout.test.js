import { test } from "node:test";
import assert from "node:assert/strict";
import { buildTransferRequest, bridgeIdempotencyKey, mapTransferStatus, submitTransfer, getTransferStatus, assertPayableAmount, API_BASE } from "../bridge-payout.mjs";

const base = { referenceId:'u1', amountUsdc:'19.87', customerId:'cust_1', externalAccountId:'ext_1', senderAddress:'0xanicca' };

test("buildTransferRequest: usdc(base)->fiat external account, on_behalf_of", () => {
  const r = buildTransferRequest(base);
  assert.equal(r.on_behalf_of,'cust_1'); assert.equal(r.amount,'19.87');
  assert.equal(r.source.currency,'usdc'); assert.equal(r.source.payment_rail,'base');
  assert.equal(r.destination.currency,'usd'); assert.equal(r.destination.external_account_id,'ext_1');
});
test("buildTransferRequest: rejects missing required + zero/over-precision amount", () => {
  assert.throws(()=>buildTransferRequest({...base,referenceId:''}),/referenceId required/);
  assert.throws(()=>buildTransferRequest({...base,customerId:''}),/customerId/);
  assert.throws(()=>buildTransferRequest({...base,externalAccountId:''}),/externalAccountId/);
  assert.throws(()=>buildTransferRequest({...base,amountUsdc:'0'}),/> 0/);
  assert.throws(()=>buildTransferRequest({...base,amountUsdc:'1.1234567'}),/6 decimal/);
});
test("bridgeIdempotencyKey: deterministic + requires referenceId", () => {
  assert.equal(bridgeIdempotencyKey('u1'),bridgeIdempotencyKey('u1'));
  assert.notEqual(bridgeIdempotencyKey('u1'),bridgeIdempotencyKey('u2'));
  assert.throws(()=>bridgeIdempotencyKey(''),/referenceId required/);
});
test("mapTransferStatus: success->paid, failure->needs_review, else pending", () => {
  assert.equal(mapTransferStatus('payment_processed'),'paid');
  assert.equal(mapTransferStatus('completed'),'paid');
  assert.equal(mapTransferStatus('returned'),'needs_review');
  assert.equal(mapTransferStatus('error'),'needs_review');
  assert.equal(mapTransferStatus('awaiting_funds'),'pending');
  assert.equal(mapTransferStatus(undefined),'pending');
});
test("submitTransfer: Idempotency-Key derives from referenceId, NOT amount (FIND-001/002)", async () => {
  let cap=null; const fetchImpl=async(u,o)=>{cap={u,o};return{ok:true,json:async()=>({id:'tr_1',state:'awaiting_funds'})};};
  const r=await submitTransfer(buildTransferRequest(base),{apiKey:'sk',fetchImpl});
  assert.equal(r.id,'tr_1'); assert.equal(cap.u,`${API_BASE}/transfers`);
  assert.equal(cap.o.headers['Api-Key'],'sk');
  assert.equal(cap.o.headers['Idempotency-Key'],'bridge-payout-u1'); // value = key(referenceId), not amount
});
test("submitTransfer: same amount+recipient, DIFFERENT referenceId -> DIFFERENT keys (no dropped repeat UBI)", async () => {
  const keys=[]; const fetchImpl=async(u,o)=>{keys.push(o.headers['Idempotency-Key']);return{ok:true,json:async()=>({id:'x'})};};
  await submitTransfer(buildTransferRequest({...base,referenceId:'period1'}),{apiKey:'sk',fetchImpl});
  await submitTransfer(buildTransferRequest({...base,referenceId:'period2'}),{apiKey:'sk',fetchImpl});
  assert.notEqual(keys[0],keys[1]);
});
test("submitTransfer: missing referenceId in body -> throws (no amount-fallback collision)", async () => {
  await assert.rejects(submitTransfer({amount:'5',on_behalf_of:'c'},{apiKey:'sk',fetchImpl:async()=>({ok:true,json:async()=>({})})}),/referenceId required/);
});
test("assertPayableAmount: rejects above ceiling (FIND-004)", () => {
  assert.throws(()=>assertPayableAmount('200000','x',100000),/exceeds max/);
  assert.doesNotThrow(()=>assertPayableAmount('50','x',100000));
});
test("mapTransferStatus: terminal failures -> needs_review (FIND-005)", () => {
  for (const s of ['reversed','charged_back','declined','rejected','reclaimed','expired']) assert.equal(mapTransferStatus(s),'needs_review');
});
test("submitTransfer: throws on non-ok with body (no false-ok); rejects bad amount", async () => {
  const f=async()=>({ok:false,status:422,text:async()=>'bad external_account'});
  await assert.rejects(submitTransfer(buildTransferRequest(base),{apiKey:'sk',fetchImpl:f}),/422: bad external_account/);
  await assert.rejects(submitTransfer({amount:'0'},{apiKey:'sk',fetchImpl:async()=>({ok:true,json:async()=>({})})}),/> 0/);
});
test("submitTransfer/getTransferStatus: require apiKey", async () => {
  await assert.rejects(submitTransfer({amount:'1'},{}),/BRIDGE_API_KEY required/);
  await assert.rejects(getTransferStatus('tr_1',{}),/BRIDGE_API_KEY required/);
});
test("getTransferStatus: maps state", async () => {
  const f=async()=>({ok:true,json:async()=>({state:'payment_processed'})});
  assert.equal((await getTransferStatus('tr_1',{apiKey:'sk',fetchImpl:f})).status,'paid');
});
