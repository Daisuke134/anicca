// node:test — lending-verify.mjs (Phase 2a RED, anicca-agent-lending REQ-106/REQ-108, resolves
// FIND-007/FIND-105/FIND-202/FIND-301).
// RED phase: this file is written BEFORE ../lending-verify.mjs exists, so every import below is the
// first failing assertion (module not found). GREEN = Phase 2b implements ../lending-verify.mjs to
// make all of this pass.
//
// verifyRepayment/reconcileProvisionalDisbursement are EFFECTFUL — they talk to an EVM JSON-RPC
// endpoint (getTransactionReceipt / eth_getBlockByNumber("finalized") / eth_getLogs), reusing
// record-earn.mjs's own already-hardened TRANSFER_TOPIC-match + exact-zero-padded-address-equality +
// finalized-block-only pattern (lines 56, 65-72, 82-88 of
// __REPO_ROOT__/skills/self/founder-loop/record-earn.mjs), NOT escrow.mjs (which contains no Transfer-log
// parsing at all). Rather than mocking a module, these tests spin up a tiny REAL local HTTP JSON-RPC
// server (node:http) and pass its URL as `rpcUrl` — the SAME "real fetch/HTTP round-trip, just
// pointed at localhost instead of mainnet.base.org" style already used to test record-earn.mjs's own
// seams. This is genuine Tier-2 integration coverage (real module wiring, real network round-trip),
// not a Tier-1 pure-function test — no live chain spend required (Tier 3, PROP-108a, is separate and
// covered once GREEN lands, live).
import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { verifyRepayment, reconcileProvisionalDisbursement } from "../lending-verify.mjs";

const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const LENDER = "0xLENDER00000000000000000000000000000001";
const BORROWER = "0xBORROWER0000000000000000000000000000002";

function padTopicExact(addr) {
  return "0x" + "0".repeat(24) + addr.slice(2).toLowerCase();
}
// A SUFFIX match but NOT an exact zero-padded match — reproduces the FIND-704 bug class this feature's
// own `to`-side check LITERALLY reuses the fix for, and the `from`-side check EXTENDS (FIND-105): the
// leading bytes are non-zero, so exact-equality correctly rejects it even though the trailing 20 bytes
// (the address itself) still match.
function padTopicSuffixOnly(addr) {
  return "0x" + "1".repeat(24) + addr.slice(2).toLowerCase();
}
function transferLog({ from, to, valueBase, transactionHash }) {
  return {
    address: USDC,
    topics: [TRANSFER_TOPIC, padTopicExact(from), padTopicExact(to)],
    data: "0x" + BigInt(valueBase).toString(16).padStart(64, "0"),
    ...(transactionHash ? { transactionHash } : {}),
  };
}

// Minimal local JSON-RPC mock server — responds to eth_getTransactionReceipt / eth_getBlockByNumber /
// eth_getLogs per a caller-supplied handler map keyed by method name. A method with no handler
// responds with a JSON-RPC error, exercising the "reconciliation lookup itself throws" failure mode
// (PROP-106l) without any module-level mocking.
function startMockRpc(handlers) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let body = "";
      req.on("data", (c) => (body += c));
      req.on("end", () => {
        const { method, params, id } = JSON.parse(body || "{}");
        const handler = handlers[method];
        res.setHeader("Content-Type", "application/json");
        if (!handler) {
          res.end(JSON.stringify({ jsonrpc: "2.0", id, error: { code: -32601, message: `no mock handler for ${method}` } }));
          return;
        }
        res.end(JSON.stringify({ jsonrpc: "2.0", id, result: handler(params) }));
      });
    });
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ url: `http://127.0.0.1:${port}`, close: () => new Promise((r) => server.close(r)) });
    });
  });
}

// ===========================================================================
// REQ-108 — verifyRepayment
// ===========================================================================

test("PROP-108b: verifyRepayment credits a valid, finalized, correctly-attributed repayment transaction", async () => {
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [transferLog({ from: BORROWER, to: LENDER, valueBase: 22000 })] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    const result = await verifyRepayment({ txHash: "0xaaaa", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: [] });
    assert.equal(result.rejected, false);
    assert.equal(result.credited, 0.022);
  } finally {
    await rpc.close();
  }
});

test("PROP-108b/FIND-704: verifyRepayment REJECTS a Transfer whose `to` topic is a suffix match but NOT an exact zero-padded match (the exact bug class already fixed once in record-earn.mjs)", async () => {
  const badLog = { address: USDC, topics: [TRANSFER_TOPIC, padTopicExact(BORROWER), padTopicSuffixOnly(LENDER)], data: "0x" + BigInt(22000).toString(16).padStart(64, "0") };
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [badLog] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    const result = await verifyRepayment({ txHash: "0xbbbb", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: [] });
    assert.equal(result.credited, 0);
    assert.equal(result.rejected, true);
  } finally {
    await rpc.close();
  }
});

test("PROP-108b/FIND-105: verifyRepayment REJECTS a Transfer whose `from` topic is a suffix match but NOT an exact zero-padded match — proving the from-side EXTENSION is genuinely exact-equality, not the unchecked substring record-earn.mjs itself uses for that field", async () => {
  const badLog = { address: USDC, topics: [TRANSFER_TOPIC, padTopicSuffixOnly(BORROWER), padTopicExact(LENDER)], data: "0x" + BigInt(22000).toString(16).padStart(64, "0") };
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [badLog] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    const result = await verifyRepayment({ txHash: "0xcccc", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: [] });
    assert.equal(result.credited, 0);
    assert.equal(result.rejected, true);
  } finally {
    await rpc.close();
  }
});

test("PROP-108a (finalized-block discipline): a receipt whose block is AFTER the current finalized block is rejected — never trusts an un-finalized read for this money invariant", async () => {
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x65", logs: [transferLog({ from: BORROWER, to: LENDER, valueBase: 22000 })] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }), // finalized is BEHIND the tx's own block -- not yet finalized
  });
  try {
    const result = await verifyRepayment({ txHash: "0xdddd", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: [] });
    assert.equal(result.credited, 0);
    assert.equal(result.rejected, true);
  } finally {
    await rpc.close();
  }
});

test("PROP-108b: a reverted transaction (status != success) is rejected, credits 0", async () => {
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x0", blockNumber: "0x64", logs: [] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    const result = await verifyRepayment({ txHash: "0xeeee", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: [] });
    assert.equal(result.credited, 0);
    assert.equal(result.rejected, true);
  } finally {
    await rpc.close();
  }
});

test("PROP-108e: verifyRepayment rejects a txHash already recorded as credited ANYWHERE in loans.jsonl — same-loan replay (resolves FIND-202)", async () => {
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [transferLog({ from: BORROWER, to: LENDER, valueBase: 22000 })] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    const alreadyCreditedRows = [{ loan_id: "loan_L1_1", status: "active", repaid_usd: 0.022, tx_hash: "0xALREADYUSED" }];
    const result = await verifyRepayment({ txHash: "0xALREADYUSED", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: alreadyCreditedRows });
    assert.equal(result.credited, 0, "a real, valid, finalized, correctly-attributed txHash is STILL rejected once already credited anywhere in the ledger");
    assert.equal(result.rejected, true);
  } finally {
    await rpc.close();
  }
});

test("PROP-108e: verifyRepayment rejects a txHash already credited toward a DIFFERENT loan_id — cross-loan replay (resolves FIND-202)", async () => {
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [transferLog({ from: BORROWER, to: LENDER, valueBase: 22000 })] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    // this txHash was already credited toward loan A -- resubmitting it as proof for loan B (a DIFFERENT
    // loan_id) must be rejected identically to the same-loan case, even though the underlying tx is real.
    const crossLoanRows = [{ loan_id: "loan_L1_A", status: "repaid", repaid_usd: 0.022, tx_hash: "0xCROSSLOANREUSE" }];
    const result = await verifyRepayment({ txHash: "0xCROSSLOANREUSE", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: crossLoanRows });
    assert.equal(result.credited, 0);
    assert.equal(result.rejected, true);
  } finally {
    await rpc.close();
  }
});

test("FIND-301 fix (critical, impl-review iteration-4): verifyRepayment's alreadyCredited guard rejects a txHash that matches an already-recorded row's tx_hash in a DIFFERENT case -- tx_hash reaches loans.jsonl from two uncoordinated sources (the facilitator-format disbursement route vs. this module's own eth_getLogs-derived extractTxHash) with no shared, code-enforced casing contract, so a mere casing difference must never let the replay guard silently fail to match", async () => {
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [transferLog({ from: BORROWER, to: LENDER, valueBase: 22000 })] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    // Recorded lowercase (the SAME casing normalizeTxHash's storage-side fix would produce); the caller
    // submits the SAME logical hash in a DIFFERENT case -- the SAME real transaction, casing differs only.
    const alreadyCreditedRows = [{ loan_id: "loan_L1_1", status: "active", repaid_usd: 0.022, tx_hash: "0xcasingmismatchtx00000000000000000000000000000000000000000001" }];
    const result = await verifyRepayment({
      txHash: "0xCASINGMISMATCHTX00000000000000000000000000000000000000000001",
      expectedFrom: BORROWER,
      expectedTo: LENDER,
      rpcUrl: rpc.url,
      loanRows: alreadyCreditedRows,
    });
    assert.equal(result.credited, 0, "a casing-only difference must never let an already-credited tx_hash be counted again");
    assert.equal(result.rejected, true);
  } finally {
    await rpc.close();
  }
});

test("PROP-108f: verifyRepayment fails closed (credits 0, rejected:true) rather than throwing when a structurally-matching Transfer log's own `data` field is malformed/non-hex (resolves FIND-901)", async () => {
  const badDataLog = {
    address: USDC,
    topics: [TRANSFER_TOPIC, padTopicExact(BORROWER), padTopicExact(LENDER)],
    data: "not-valid-hex-data",
  };
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [badDataLog] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    await assert.doesNotReject(async () => {
      const result = await verifyRepayment({ txHash: "0xbaddata", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: [] });
      assert.equal(result.credited, 0);
      assert.equal(result.rejected, true);
    });
  } finally {
    await rpc.close();
  }
});

test("PROP-108f: verifyRepayment fails closed (credits 0, rejected:true) rather than throwing when the receipt's own blockNumber field is malformed/non-hex (resolves FIND-901)", async () => {
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "not-hex", logs: [transferLog({ from: BORROWER, to: LENDER, valueBase: 22000 })] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    await assert.doesNotReject(async () => {
      const result = await verifyRepayment({ txHash: "0xbadblock", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: [] });
      assert.equal(result.credited, 0);
      assert.equal(result.rejected, true);
    });
  } finally {
    await rpc.close();
  }
});

test("verifyRepayment credits a genuinely NEW, never-before-seen txHash normally (positive control for the replay-rejection tests above)", async () => {
  const rpc = await startMockRpc({
    eth_getTransactionReceipt: () => ({ status: "0x1", blockNumber: "0x64", logs: [transferLog({ from: BORROWER, to: LENDER, valueBase: 11000 })] }),
    eth_getBlockByNumber: () => ({ number: "0x64" }),
  });
  try {
    const otherLoanRows = [{ loan_id: "loan_L1_A", status: "repaid", repaid_usd: 0.022, tx_hash: "0xSOMEOTHERTX" }];
    const result = await verifyRepayment({ txHash: "0xBRANDNEWTX", expectedFrom: BORROWER, expectedTo: LENDER, rpcUrl: rpc.url, loanRows: otherLoanRows });
    assert.equal(result.rejected, false);
    assert.equal(result.credited, 0.011);
  } finally {
    await rpc.close();
  }
});

// ===========================================================================
// REQ-106 — reconcileProvisionalDisbursement (crash / in-process-exception recovery)
// ===========================================================================

test("PROP-106g/PROP-106h: reconcileProvisionalDisbursement finds a crashed/uncertain attempt's own real transfer and reports it, WITHOUT ever disbursing a second time", async () => {
  const loanRow = {
    loan_id: "loan_L1_1",
    lender_id: "L1",
    borrower_id: "b1",
    lender_wallet: LENDER,
    borrower_wallet: BORROWER,
    principal_usd: 0.02,
    provisioned_ms: Date.now() - 5000,
  };
  const rpc = await startMockRpc({ eth_getLogs: () => [transferLog({ from: LENDER, to: BORROWER, valueBase: 20000 })] });
  try {
    const result = await reconcileProvisionalDisbursement({ loanRow, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" });
    assert.equal(result.found, true);
    assert.ok(result.txHash, "the discovered real txHash must be reported so the caller can append the recovering 'active' row");
  } finally {
    await rpc.close();
  }
});

test("FIND-101 fix (critical, impl-review iteration-2): reconcileProvisionalDisbursement REJECTS a Transfer between the correct lender/borrower wallets whose decoded VALUE does not equal loanRow.principal_usd -- an unrelated transfer between the same two wallets (e.g. a different payment, or a prior loan's repayment) must never be mistaken for THIS loan's own disbursement", async () => {
  const loanRow = {
    loan_id: "loan_L1_5",
    lender_id: "L1",
    borrower_id: "b1",
    lender_wallet: LENDER,
    borrower_wallet: BORROWER,
    principal_usd: 0.02, // expects exactly 20000 base units
  };
  // Address+from+to topics all match -- ONLY the value differs (5000, not the expected 20000).
  const rpc = await startMockRpc({ eth_getLogs: () => [transferLog({ from: LENDER, to: BORROWER, valueBase: 5000 })] });
  try {
    const result = await reconcileProvisionalDisbursement({ loanRow, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" });
    assert.equal(result.found, false, "an unrelated-value transfer between the same two wallets must NOT be treated as this loan's own disbursement");
  } finally {
    await rpc.close();
  }
});

test("FIND-101 fix (critical, impl-review iteration-2): reconcileProvisionalDisbursement picks the EXACT-value transfer and ignores a same-wallet-pair unrelated-value transfer when BOTH appear in the same window", async () => {
  const loanRow = {
    loan_id: "loan_L1_6",
    lender_id: "L1",
    borrower_id: "b1",
    lender_wallet: LENDER,
    borrower_wallet: BORROWER,
    principal_usd: 0.02,
  };
  const rpc = await startMockRpc({
    eth_getLogs: () => [
      transferLog({ from: LENDER, to: BORROWER, valueBase: 5000 }), // unrelated -- must be skipped
      transferLog({ from: LENDER, to: BORROWER, valueBase: 20000 }), // THIS loan's own principal -- must be matched
    ],
  });
  try {
    const result = await reconcileProvisionalDisbursement({ loanRow, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" });
    assert.equal(result.found, true);
    assert.ok(result.txHash);
  } finally {
    await rpc.close();
  }
});

test("FIND-201 fix (critical, impl-review iteration-3): reconcileProvisionalDisbursement REJECTS a wallet-pair+exact-value-matching Transfer whose tx_hash is ALREADY recorded against a DIFFERENT loan_id in loanRows -- the same struggling borrower's next stuck-row cycle (identical wallet pair, identical flat cold-start cap) must never have loan_B's reconcile silently claim loan_A's own genuine, already-credited disbursement", async () => {
  const loanRowB = {
    loan_id: "loan_Franklin_2",
    lender_id: "L1",
    borrower_id: "franklin2",
    lender_wallet: LENDER,
    borrower_wallet: BORROWER,
    principal_usd: 0.02,
  };
  // loan_Franklin_1 already recorded this EXACT tx_hash as its own disbursement (same wallet pair, same
  // $0.02 flat cold-start cap -- the concrete FIND-201 collision shape).
  const loanRows = [
    { loan_id: "loan_Franklin_1", lender_id: "L1", borrower_id: "franklin2", tx_hash: "0xalreadyclaimedbyloanA00000000000000000000000000000000000001", status: "active" },
  ];
  const rpc = await startMockRpc({
    eth_getLogs: () => [transferLog({ from: LENDER, to: BORROWER, valueBase: 20000, transactionHash: "0xalreadyclaimedbyloanA00000000000000000000000000000000000001" })],
  });
  try {
    const result = await reconcileProvisionalDisbursement({ loanRow: loanRowB, loanRows, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" });
    assert.equal(result.found, false, "a tx_hash already recorded against a DIFFERENT loan_id must never be counted as THIS loan's own disbursement -- fail closed, stay unconfirmed rather than misattribute");
  } finally {
    await rpc.close();
  }
});

test("FIND-201 fix: reconcileProvisionalDisbursement still finds a genuinely NEW, never-before-recorded tx_hash normally (positive control for the replay-rejection test above -- loanRows present but no collision)", async () => {
  const loanRow = {
    loan_id: "loan_Franklin_2",
    lender_id: "L1",
    borrower_id: "franklin2",
    lender_wallet: LENDER,
    borrower_wallet: BORROWER,
    principal_usd: 0.02,
  };
  const loanRows = [
    { loan_id: "loan_Franklin_1", lender_id: "L1", borrower_id: "franklin2", tx_hash: "0xunrelatedtxfromadifferentpriorloan0000000000000000000000000001", status: "active" },
  ];
  const rpc = await startMockRpc({
    eth_getLogs: () => [transferLog({ from: LENDER, to: BORROWER, valueBase: 20000, transactionHash: "0xgenuinelynewtxforloanB0000000000000000000000000000000000000002" })],
  });
  try {
    const result = await reconcileProvisionalDisbursement({ loanRow, loanRows, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" });
    assert.equal(result.found, true);
    assert.equal(result.txHash, "0xgenuinelynewtxforloanB0000000000000000000000000000000000000002");
  } finally {
    await rpc.close();
  }
});

test("FIND-301 fix (critical, impl-review iteration-4): reconcileProvisionalDisbursement's alreadyRecorded guard rejects a candidate whose extractTxHash-derived tx_hash matches an already-recorded row's tx_hash in a DIFFERENT case -- the same cross-source casing gap as the repayment guard above, on the reconciliation side", async () => {
  const loanRowB = {
    loan_id: "loan_Franklin_2",
    lender_id: "L1",
    borrower_id: "franklin2",
    lender_wallet: LENDER,
    borrower_wallet: BORROWER,
    principal_usd: 0.02,
  };
  // loan_Franklin_1 recorded this tx_hash lowercase (the SAME casing normalizeTxHash's storage-side fix
  // would produce); the mock RPC's own eth_getLogs response returns the SAME logical hash in a
  // DIFFERENT case -- mirrors a real facilitator-format-vs-RPC-format casing divergence for the
  // identical transaction (FIND-301's exact hazard shape).
  const loanRows = [
    { loan_id: "loan_Franklin_1", lender_id: "L1", borrower_id: "franklin2", tx_hash: "0xcasingmismatchreconciletx0000000000000000000000000000000001", status: "active" },
  ];
  const rpc = await startMockRpc({
    eth_getLogs: () => [transferLog({ from: LENDER, to: BORROWER, valueBase: 20000, transactionHash: "0xCASINGMISMATCHRECONCILETX0000000000000000000000000000000001" })],
  });
  try {
    const result = await reconcileProvisionalDisbursement({ loanRow: loanRowB, loanRows, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" });
    assert.equal(result.found, false, "a casing-only difference must never let an already-recorded tx_hash be counted as this loan's own disbursement");
  } finally {
    await rpc.close();
  }
});

test("PROP-106f/PROP-106g: reconcileProvisionalDisbursement reports no match when the on-chain lookup finds nothing (the disbursement_failed path)", async () => {
  const loanRow = { loan_id: "loan_L1_2", lender_id: "L1", borrower_id: "b1", lender_wallet: LENDER, borrower_wallet: BORROWER, principal_usd: 0.02 };
  const rpc = await startMockRpc({ eth_getLogs: () => [] });
  try {
    const result = await reconcileProvisionalDisbursement({ loanRow, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" });
    assert.equal(result.found, false);
  } finally {
    await rpc.close();
  }
});

test("PROP-106l: reconcileProvisionalDisbursement propagates a failure when the lookup itself throws — the caller must fail this specific attempt cleanly (zero sequence number consumed, zero row appended) and safely retry later", async () => {
  const loanRow = { loan_id: "loan_L1_3", lender_id: "L1", borrower_id: "b1", lender_wallet: LENDER, borrower_wallet: BORROWER, principal_usd: 0.02 };
  const rpc = await startMockRpc({}); // no eth_getLogs handler -> the mock server returns a JSON-RPC error
  try {
    await assert.rejects(() => reconcileProvisionalDisbursement({ loanRow, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" }));
  } finally {
    await rpc.close();
  }
});

test("reconcileProvisionalDisbursement only ever READS on-chain state — never invokes any transfer/settle call itself (it is a lookup, not a disbursement primitive)", async () => {
  const loanRow = { loan_id: "loan_L1_4", lender_id: "L1", borrower_id: "b1", lender_wallet: LENDER, borrower_wallet: BORROWER, principal_usd: 0.02 };
  let settleCalled = false;
  const rpc = await startMockRpc({
    eth_getLogs: () => [transferLog({ from: LENDER, to: BORROWER, valueBase: 20000 })],
    eth_sendRawTransaction: () => {
      settleCalled = true;
      return "0xshouldneverbecalled";
    },
  });
  try {
    await reconcileProvisionalDisbursement({ loanRow, rpcUrl: rpc.url, fromBlock: "0x1", toBlock: "0x64" });
    assert.equal(settleCalled, false, "a reconciliation lookup must never itself broadcast a transaction — it only reads");
  } finally {
    await rpc.close();
  }
});
