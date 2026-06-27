#!/usr/bin/env node
// mock-rpc.mjs — a fixture JSON-RPC server to exercise record-earn's REAL RPC path (eth_getBlockByNumber "finalized"
// + eth_getLogs) WITHOUT the FOUNDER_BLOCK_NOW / FOUNDER_*_LOGS seams, so the actual finalized-decode and the real
// getLogs parse are unit-tested (FIND-705). env: MOCK_FINALIZED (hex like "0xc8", or "null", or "numbernull"),
// MOCK_LOGS (raw eth_getLogs result JSON), MOCK_PORT.
import http from "node:http";
const FIN = process.env.MOCK_FINALIZED ?? "0xc8";
const LOGS = process.env.MOCK_LOGS || "[]";
const PORT = Number(process.env.MOCK_PORT || 8599);
http.createServer((req, res) => {
  let b = "";
  req.on("data", (d) => (b += d));
  req.on("end", () => {
    let j; try { j = JSON.parse(b); } catch { j = {}; }
    let result = null;
    if (j.method === "eth_getBlockByNumber") result = FIN === "null" ? null : FIN === "numbernull" ? { number: null } : { number: FIN };
    else if (j.method === "eth_getLogs") result = JSON.parse(LOGS);
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ jsonrpc: "2.0", id: j.id ?? 1, result }));
  });
}).listen(PORT, () => console.error("mock-rpc on " + PORT));
