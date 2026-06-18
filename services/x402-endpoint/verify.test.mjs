// Real-tx verification test (no mock) for the x402 payment verifier.
// Run: node verify.test.mjs
import { verifyUsdcPayment } from './verify.mjs';
const REAL_TX = '0x007a856f4f83e89cd900c21302cc61e9cccd7114e60ba66145a2dac9c2a2b07b';
const RECV = '0x36cFc9869fc3078d73713AD0cac8B8008bAA082c'; // real recipient of 0.10 USDC
let fail = 0;
const ok = (c, m) => { if (!c) { console.error('FAIL', m); fail++; } else console.log('ok', m); };

const a = await verifyUsdcPayment({ txHash: REAL_TX, expectedReceiver: RECV, minAmountBase: 100000 });
ok(a.ok && a.amountBase === 100000, 'verifies a real on-chain USDC payment');
const b = await verifyUsdcPayment({ txHash: REAL_TX, expectedReceiver: '0x0000000000000000000000000000000000000001', minAmountBase: 100000 });
ok(b.ok === false, 'rejects wrong receiver');
const c = await verifyUsdcPayment({ txHash: REAL_TX, expectedReceiver: RECV, minAmountBase: 999999999 });
ok(c.ok === false, 'rejects underpayment');
const d = await verifyUsdcPayment({ txHash: '0xdead', expectedReceiver: RECV, minAmountBase: 1 });
ok(d.ok === false, 'rejects malformed txHash');
process.exit(fail ? 1 : 0);
