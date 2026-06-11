// Anicca compute self-pay proxy — OpenAI-compatible on :8402.
// Every inference is paid in USDC via x402 from THIS Anicca's own wallet (no human key).
// Free model when broke, frontier when funded. One per Anicca box.
import http from "http";
import fs from "fs";
import { BlockrunClient } from "@blockrun/llm";
const walletPath = (process.env.HOME||"") + "/.automaton/wallet.json";
const pk = JSON.parse(fs.readFileSync(walletPath, "utf8")).privateKey;
process.env.BASE_CHAIN_WALLET_KEY = pk.startsWith("0x") ? pk : "0x"+pk;
const br = new BlockrunClient();
const PORT = process.env.COMPUTE_PROXY_PORT || 8402;
const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url.includes("/chat/completions")) {
    let body = ""; req.on("data", c => body += c);
    req.on("end", async () => {
      try {
        const out = await br.post("/v1/chat/completions", JSON.parse(body));
        res.writeHead(200, {"Content-Type":"application/json"}); res.end(JSON.stringify(out));
      } catch (e) { res.writeHead(502, {"Content-Type":"application/json"}); res.end(JSON.stringify({error:{message:String(e?.message||e)}})); }
    });
  } else if (req.url.includes("/models")) {
    res.writeHead(200, {"Content-Type":"application/json"}); res.end(JSON.stringify({object:"list",data:[]}));
  } else { res.writeHead(404); res.end(); }
});
server.listen(PORT, () => console.log(`anicca compute-proxy on :${PORT} — x402 self-pay from own wallet`));
