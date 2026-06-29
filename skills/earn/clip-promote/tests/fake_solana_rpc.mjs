// Minimal local Solana JSON-RPC stand-in for the RECORD E2E shell test (FIND-002). Returns a
// confirmed signature + a 0.5 USDC inbound to the test wallet's ATA. Prints "PORT=<n>" then serves.
import http from "node:http";
const WALLET = "xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H";
const USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";
const server = http.createServer((req, res) => {
  let body = "";
  req.on("data", (c) => (body += c));
  req.on("end", () => {
    let m = {};
    try { m = JSON.parse(body); } catch {}
    let result;
    if (m.method === "getSignatureStatuses") result = { value: [{ confirmationStatus: "finalized", err: null }] };
    else if (m.method === "getTransaction") result = { meta: { err: null, preTokenBalances: [],
      postTokenBalances: [{ accountIndex: 3, owner: WALLET, mint: USDC,
        uiTokenAmount: { amount: "500000", decimals: 6, uiAmount: 0.5, uiAmountString: "0.5" } }] } };
    else result = null;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ jsonrpc: "2.0", id: m.id ?? 1, result }));
  });
});
server.listen(0, "127.0.0.1", () => { console.log(`PORT=${server.address().port}`); });
