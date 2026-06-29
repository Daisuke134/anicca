import http from "http";
import fs from "fs";
import { BlockrunClient } from "@blockrun/llm";
const pk = JSON.parse(fs.readFileSync(process.env.WALLET_FILE)).privateKey;
process.env.BASE_CHAIN_WALLET_KEY = pk.startsWith("0x") ? pk : "0x"+pk;
const br = new BlockrunClient();
const MODEL = process.env.FORCE_MODEL || "anthropic/claude-sonnet-4-6";
const PORT = process.env.PORT || 8410;
http.createServer((req,res)=>{
  if (req.method==="POST" && req.url.includes("/chat/completions")) {
    let b=""; req.on("data",c=>b+=c);
    req.on("end", async()=>{
      try { const body=JSON.parse(b); body.model=MODEL;   // FORCE frontier, ignore requested model
        const out=await br.post("/v1/chat/completions", body);
        res.writeHead(200,{"Content-Type":"application/json"}); res.end(JSON.stringify(out));
      } catch(e){ res.writeHead(502,{"Content-Type":"application/json"}); res.end(JSON.stringify({error:{message:String(e?.message||e)}})); }
    });
  } else if (req.url.includes("/models")) {
    res.writeHead(200,{"Content-Type":"application/json"}); res.end(JSON.stringify({object:"list",data:[{id:MODEL,object:"model"}]}));
  } else { res.writeHead(404); res.end(); }
}).listen(PORT, ()=>console.log("force-frontier proxy :"+PORT+" model="+MODEL));
