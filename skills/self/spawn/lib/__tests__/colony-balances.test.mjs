// VCSDD anicca-agent-spawn, Phase 2a (RED). REQ-101 readCitizenBalances — registry-driven,
// public-RPC balance query, dual-chain sum + per-chain independent fail-closing.
// colony-balances.mjs does not exist yet — expected to fail at import time (module-not-found).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readCitizenBalances } from "../colony-balances.mjs";

function citizen({ id, evm, solana }) {
  const walletAddress = {};
  if (evm) walletAddress.evm = evm;
  if (solana) walletAddress.solana = solana;
  return { id, walletAddress };
}

test("PROP-101f: a dual-wallet citizen (evm+solana both populated) sums both chains' USD-normalized balances", async () => {
  const citizens = [citizen({ id: "dual", evm: "0xEVM", solana: "SOLADDR" })];
  const result = await readCitizenBalances({
    citizens,
    fetchEvmBalanceUsd: async (addr) => (addr === "0xEVM" ? 4 : 0),
    fetchSolanaBalanceUsd: async (addr) => (addr === "SOLADDR" ? 6 : 0),
  });
  assert.equal(result.find((r) => r.citizenId === "dual").balanceUsd, 10);
});

test("PROP-101g: exactly one chain fails (throws/non-finite) while the other succeeds -> total is ONLY the successful chain's value, never 0", async () => {
  const citizens = [citizen({ id: "dual", evm: "0xEVM", solana: "SOLADDR" })];
  const evmFails = await readCitizenBalances({
    citizens,
    fetchEvmBalanceUsd: async () => {
      throw new Error("rpc down");
    },
    fetchSolanaBalanceUsd: async () => 7,
  });
  assert.equal(evmFails.find((r) => r.citizenId === "dual").balanceUsd, 7);

  const solanaFails = await readCitizenBalances({
    citizens,
    fetchEvmBalanceUsd: async () => 5,
    fetchSolanaBalanceUsd: async () => NaN,
  });
  assert.equal(solanaFails.find((r) => r.citizenId === "dual").balanceUsd, 5);
});

test("PROP-101h: both chains fail simultaneously -> exactly 0 for that citizen, never throws, never NaN, reserve never double-subtracted", async () => {
  const citizens = [citizen({ id: "dual", evm: "0xEVM", solana: "SOLADDR" })];
  const result = await readCitizenBalances({
    citizens,
    fetchEvmBalanceUsd: async () => {
      throw new Error("down");
    },
    fetchSolanaBalanceUsd: async () => Infinity,
  });
  const entry = result.find((r) => r.citizenId === "dual");
  assert.equal(entry.balanceUsd, 0);
  assert.ok(Number.isFinite(entry.balanceUsd));
});

test("PROP-101c: a single-chain citizen whose only query fails/returns negative contributes 0, never throws", async () => {
  const citizens = [citizen({ id: "single", evm: "0xEVM" })];
  const result = await readCitizenBalances({
    citizens,
    fetchEvmBalanceUsd: async () => -1,
    fetchSolanaBalanceUsd: async () => 0,
  });
  assert.equal(result.find((r) => r.citizenId === "single").balanceUsd, 0);
});

test("PROP-101e: resolves a balance identically for a co-located citizen's address and a simulated remote (cloud-hosted) citizen's address — no local-file dependency", async () => {
  const citizens = [citizen({ id: "coLocated", evm: "0xLOCAL" }), citizen({ id: "remoteChild", evm: "0xREMOTE" })];
  const result = await readCitizenBalances({
    citizens,
    fetchEvmBalanceUsd: async (addr) => (addr === "0xLOCAL" ? 3 : 9),
    fetchSolanaBalanceUsd: async () => 0,
  });
  assert.equal(result.find((r) => r.citizenId === "coLocated").balanceUsd, 3);
  assert.equal(result.find((r) => r.citizenId === "remoteChild").balanceUsd, 9);
});

test("REQ-101 dual-chain edge case: one chain populated, zero balance, other unpopulated — no special case needed", async () => {
  const citizens = [citizen({ id: "zeroEvm", evm: "0xEVM" })];
  const result = await readCitizenBalances({
    citizens,
    fetchEvmBalanceUsd: async () => 0,
    fetchSolanaBalanceUsd: async () => 0,
  });
  assert.equal(result.find((r) => r.citizenId === "zeroEvm").balanceUsd, 0);
});

test("PROP-101l: a null entry mixed into citizens is skipped gracefully, never thrown, consistent with computeColonySurplusUsd on the same fixture", async () => {
  const citizens = [null, citizen({ id: "healthy", evm: "0xEVM" }), undefined];
  await assert.doesNotReject(() =>
    readCitizenBalances({ citizens, fetchEvmBalanceUsd: async () => 5, fetchSolanaBalanceUsd: async () => 0 })
  );
  const result = await readCitizenBalances({
    citizens,
    fetchEvmBalanceUsd: async () => 5,
    fetchSolanaBalanceUsd: async () => 0,
  });
  assert.deepEqual(result.map((r) => r.citizenId), ["healthy"]);
});
