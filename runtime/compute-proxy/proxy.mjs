// Anicca compute self-pay proxy — OpenAI-compatible on :8402.
// Every inference is paid in USDC via x402 from THIS Anicca's own wallet (no human key).
// br.post settles the x402 payment and returns the OpenAI-shaped completion. Pass a concrete model
// id (e.g. anthropic/claude-sonnet-4-6 for frontier). ClawRouter profile auto-routing (premium/auto)
// needs the full routing config and is wired separately; for now the loop pins a model id.
import http from "http";
import { BlockrunClient } from "@blockrun/llm";
import { loadEvmKey } from "../../skills/earn/lib/resolve-identity.mjs";
// Agent-economy compute-pay always uses THIS instance's wallet. Explicit mode prevents a shared
// process environment (ANICCA_EVM_PRIVATE_KEY, PKVAR, BLOCKRUN_WALLET_KEY, or BASE_CHAIN_WALLET_KEY)
// from selecting another instance's signing identity.
const pk = loadEvmKey({ mode: "agent-economy" });
if (pk) process.env.BASE_CHAIN_WALLET_KEY = pk;
const br = new BlockrunClient();
const PORT = process.env.COMPUTE_PROXY_PORT || 8402;
// Strip any ClawRouter profile prefix/word the caller might send; map to a concrete frontier id.
const FRONTIER = process.env.ANICCA_FRONTIER_MODEL || "anthropic/claude-sonnet-4-6";
const PROFILES = new Set(["auto", "premium", "eco", "free", "blockrun/auto", "blockrun/premium", "blockrun/eco", "blockrun/free"]);
const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url.includes("/chat/completions")) {
    let raw = ""; req.on("data", (c) => (raw += c));
    req.on("end", async () => {
      try {
        const body = JSON.parse(raw);
        if (PROFILES.has(String(body.model || "").toLowerCase())) body.model = FRONTIER;
        const out = await br.post("/v1/chat/completions", body);
        res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify(out));
      } catch (e) { res.writeHead(502, { "Content-Type": "application/json" }); res.end(JSON.stringify({ error: { message: String(e?.message || e) } })); }
    });
  } else if (req.url.includes("/models")) {
    res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify({ object: "list", data: [] }));
  } else { res.writeHead(404); res.end(); }
});
server.listen(PORT, () => console.log(`anicca compute-proxy on :${PORT} — x402 self-pay (frontier=${FRONTIER})`));
