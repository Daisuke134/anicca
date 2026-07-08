// Minimal local Solana JSON-RPC stand-in for the sol-trade/run.sh bash integration tests
// (FIND-005). Mirrors skills/earn/clip-promote/tests/fake_solana_rpc.mjs's ACTUAL proven pattern,
// parametrized via env so ONE fixture server covers every scenario this feature's tests need:
//   FAKE_RPC_WALLET   base58 owner address the fixture "getTransaction" response credits (must
//                      match the fixture's own derived wallet for usdcDeltaForSig to see it).
//   FAKE_RPC_DELTA     numeric USDC delta to report (default 0.5; negative for a loss).
//   FAKE_RPC_MODE      "ok" (default) | "unconfirmed" (confirmationStatus=processed) |
//                      "malformed" (every request gets a non-2xx response, simulating an RPC
//                      infrastructure failure -- PROP-016).
// Prints "PORT=<n>" once listening, then serves until killed.
import http from "node:http";
const WALLET = process.env.FAKE_RPC_WALLET || "";
const USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const MODE = process.env.FAKE_RPC_MODE || "ok";
const DELTA = Number(process.env.FAKE_RPC_DELTA || "0.5");

const server = http.createServer((req, res) => {
  let body = "";
  req.on("data", (c) => (body += c));
  req.on("end", () => {
    if (MODE === "malformed") {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "stub-rpc-infrastructure-failure" }));
      return;
    }
    let m = {};
    try { m = JSON.parse(body); } catch { /* malformed request body -- fall through to null result */ }
    let result = null;
    if (m.method === "getSignatureStatuses") {
      const confirmationStatus = MODE === "unconfirmed" ? "processed" : "finalized";
      result = { value: [{ confirmationStatus, err: null }] };
    } else if (m.method === "getTransaction") {
      const pre = 1.0;
      const post = pre + DELTA;
      result = {
        meta: {
          err: null,
          preTokenBalances: [{ accountIndex: 3, uiTokenAmount: { amount: String(Math.round(pre * 1e6)), decimals: 6, uiAmount: pre, uiAmountString: String(pre) } }],
          postTokenBalances: [{ accountIndex: 3, owner: WALLET, mint: USDC, uiTokenAmount: { amount: String(Math.round(post * 1e6)), decimals: 6, uiAmount: post, uiAmountString: String(post) } }],
        },
      };
    }
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ jsonrpc: "2.0", id: m.id ?? 1, result }));
  });
});
server.listen(0, "127.0.0.1", () => { console.log(`PORT=${server.address().port}`); });
