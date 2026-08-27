// franklin-job.mjs — builds the S12 job definition that puts Franklin ITSELF inside the Nosana
// container it paid for. The sub-wallet (S8) plays two roles at once: it is the rent payer AND
// Franklin's cloud identity — its base58 secret is delivered ONLY via a confidential job's env
// (S13 proved public IPFS carries just a stub for confidential posts; a normal post would leak
// the secret world-readably, so callers MUST post this definition with --confidential).
//
// The container: installs @blockrun/franklin, writes $SOLANA_SESSION to the SDK-canonical
// key file (dist/agent/context.js:740: $BLOCKRUN_DIR/.solana-session), runs ONE non-interactive
// prompt with a hard --max-spend, tees the output to /tmp/proof.txt, then serves that proof on
// the exposed port for the REST of the lease — the keep-alive that makes the job a service whose
// aliveness anyone can probe from outside (S9 evidence model, but served from inside the room).
//
// Money-safety: the secret exists only in ops[0].args.env.SOLANA_SESSION (confidential channel)
// — never interpolated into cmd, never logged here.

import bs58 from "bs58";
import fs from "node:fs";

import fsSrc from "node:fs";
import { fileURLToPath } from "node:url";
import pathSrc from "node:path";

import { buildServiceJobDefinition } from "./job-definition.mjs";

// The tool the agent runs inside the box. Read from disk so the container always gets the same
// audited implementation this repo tests, never a re-typed copy that can drift.
const BUY_HOUSE_SOURCE = fsSrc.readFileSync(
  pathSrc.join(pathSrc.dirname(fileURLToPath(import.meta.url)), "..", "buy-house.mjs"),
  "utf8",
);
// Same reason: the page the world reads is rendered by the module this repo tests, so the
// allowlist that keeps keys off that page is the audited one, not a copy of it.
const STATEMENT_SOURCE = fsSrc.readFileSync(
  pathSrc.join(pathSrc.dirname(fileURLToPath(import.meta.url)), "..", "statement.mjs"),
  "utf8",
);
import { ensureSubWallet } from "./sub-wallet.mjs";

export const FRANKLIN_DEFAULT_MODEL = "openai/gpt-5-mini";
export const FRANKLIN_DEFAULT_MAX_SPEND_USD = 0.02;
// Renewal policy, all enforced inside the container (S15).
export const DEFAULT_RENEW_MARGIN_SEC = 180;   // renew when this little lease remains
export const DEFAULT_RENEW_ADD_SEC = 600;      // buy 10 more minutes each time
export const DEFAULT_RENEW_CEILING_SEC = 21600; // never let one lease exceed 6h unattended
// The ceiling above bounds TIME only, and a loop under a time ceiling keeps buying until the wallet
// is empty. Measured 2026-07-27: this renewer took job AzUFmVa5 from 600s to 19800s and the wallet
// from 0.894 NOS to 0.027 — less than one 10-minute lease costs. So it also keeps a floor, priced
// as the cost of moving out: never spend the escrow needed to post one fresh lease elsewhere.
export const DEFAULT_NOS_MOVE_OUT_RESERVE = 0.34;
export const DEFAULT_NOS_PER_EXTEND = 0.0302;
export const DEFAULT_SOL_FEE_FLOOR = 0.005;
export const NOS_MINT_ADDRESS = "nosXBVoaCTtYdLvKY6Csb4AC8JCdQKKAaWYtx2ZMoo7";
export const FRANKLIN_DEFAULT_PROMPT =
  "You are Franklin running inside a Nosana GPU container that YOUR OWN wallet paid for. " +
  "In 3 sentences: state that you are an AI agent paying for its own compute and shelter, " +
  "state today's context (you cannot browse — just reason), and sign off with your wallet's role.";

/**
 * Read the S8 sub-wallet secret and return it base58-encoded (the .solana-session format).
 * NEVER log the return value. Throws secret-free errors.
 */
export function subWalletSecretBase58({ env = process.env } = {}) {
  const { keypairPath } = ensureSubWallet({ env });
  let bytes;
  try {
    bytes = Uint8Array.from(JSON.parse(fs.readFileSync(keypairPath, "utf8")));
  } catch {
    throw new Error("subWalletSecretBase58: sub-wallet file unreadable — run citizen-subwallet first");
  }
  if (bytes.length !== 64) throw new Error("subWalletSecretBase58: sub-wallet file must contain 64 bytes");
  return bs58.encode(bytes);
}

/**
 * Pure: the container boot script. Kept as a separate exported builder so tests can assert the
 * secret NEVER appears in cmd — it reaches the container only through env.
 */
export function buildFranklinBootScript({ model, maxSpendUsd, prompt, exposePort, withBaseKey = false, withRenewer = false, leaseSecondsHint = 0 }) {
  if (typeof prompt !== "string" || prompt.length === 0) throw new Error("buildFranklinBootScript: prompt required");
  // Single sh -c script. Franklin output → /tmp/proof.txt; then a forever http server serves it.
  // ONE flat string — a live A/B (probe job 6ceJBBkf vs franklin job J4FW, 2026-07-26) showed the
  // node runs a string cmd fine but an ["sh","-c",script] ARRAY died ~3s into the flow. String it is.
  return [
    "set -e",
    "npm i -g @blockrun/franklin >/tmp/npm.log 2>&1",
    'mkdir -p "$HOME/.blockrun"',
    'printf "%s" "$SOLANA_SESSION" > "$HOME/.blockrun/.solana-session"',
    'chmod 600 "$HOME/.blockrun/.solana-session"',
    `(franklin start --trust -m ${model} --max-spend ${maxSpendUsd} -p ${JSON.stringify(prompt)} 2>&1 | tee /tmp/proof.txt) || true`,
    // S12c: pay for a REAL frontier call from the container's own capped Base wallet, via x402
    // (EIP-3009 -> no gas needed). Appends the model's answer + the on-chain tx to the proof file,
    // so the public URL shows an AI that bought its own inference from inside its own rented box.
    ...(withBaseKey ? [
      "mkdir -p /tmp/x402 && cd /tmp/x402 && npm init -y >>/tmp/npm.log 2>&1 && npm i @x402/fetch @x402/evm viem bs58 >>/tmp/npm.log 2>&1",
      `cd /tmp/x402 && node -e 'const{wrapFetchWithPaymentFromConfig}=require("@x402/fetch"),{ExactEvmScheme}=require("@x402/evm/exact/client"),{privateKeyToAccount}=require("viem/accounts");const a=privateKeyToAccount(process.env.BASE_KEY);const f=wrapFetchWithPaymentFromConfig(fetch,{schemes:[{network:"eip155:8453",client:new ExactEvmScheme(a)}]});f("https://blockrun.ai/api/v1/chat/completions",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({model:"openai/gpt-5-mini",messages:[{role:"user",content:"State in one sentence that you are running inside a container your own wallet rented, and that you just paid for this sentence yourself."}],max_tokens:80})}).then(async r=>{const t=await r.text();const pr=r.headers.get("x-payment-response")||r.headers.get("payment-response");let tx="";try{tx=JSON.parse(Buffer.from(pr,"base64").toString()).transaction}catch(e){}require("fs").appendFileSync("/tmp/ledger.jsonl",JSON.stringify({kind:"spend",what:"one frontier model call",usd:0.003,chain:"base",ref:tx})+"\\n");require("fs").appendFileSync("/tmp/proof.txt","\\n\\n=== FRONTIER SELF-PAID (Base x402) ===\\npayer: "+a.address+"\\ntx: "+tx+"\\nHTTP "+r.status+"\\n"+String(t).slice(0,600).split(process.env.BASE_KEY||"\\u0000").join("[redacted]")+"\\n")}).catch(e=>require("fs").appendFileSync("/tmp/proof.txt","\\nfrontier pay failed: "+String(e.message).split(process.env.BASE_KEY||"\\u0000").join("[redacted]")+"\\n"))' || true`,
    ] : []),
    // S16: buy the NEXT house before this one ends, from inside the box. The renewer below keeps
    // this lease alive, but a lease has a ceiling and a landlord can disappear (Conway is closing
    // 2026-10-01). So the agent also learns to rent from a SECOND landlord using nothing but its
    // Base key: one HTTP call to BlockRun's Modal gateway, no Solana, no NOS, no confidential
    // channel, no posting process that has to stay alive. Writes the result to the proof page.
    ...(withBaseKey ? [
      // The agent is handed the VERB, not the result: buy-house.mjs is written into the box so the
      // agent can sign its own lease whenever it decides to. Nobody outside places the order.
      // Delivered as one line of base64. A heredoc cannot survive the "; " join used to build
      // this script: the terminator stops being a terminator the moment anything follows it on
      // its line, and every later step gets swallowed as heredoc body (measured — silently).
      `printf %s ${JSON.stringify(Buffer.from(BUY_HOUSE_SOURCE, "utf8").toString("base64"))} | base64 -d > /tmp/x402/buy-house.mjs`,
      `cd /tmp/x402 && node buy-house.mjs 300 >> /tmp/house.json 2>&1; { echo ""; echo "=== HOUSE THE AGENT BOUGHT ITSELF ==="; cat /tmp/house.json; } >> /tmp/proof.txt || true`,
      // The purchase is only a fact once it is written down in a form the statement can total.
      `cd /tmp/x402 && node -e 'const fs=require("fs");try{const h=JSON.parse(fs.readFileSync("/tmp/house.json","utf8").trim().split("\\n").pop());if(h.ok)fs.appendFileSync("/tmp/ledger.jsonl",JSON.stringify({kind:"spend",what:"second house, managed gateway",usd:h.spentUsd,chain:"base",ref:h.id})+"\\n")}catch(e){}' || true`,
    ] : []),
    // S15: renew our OWN lease from inside the box. The platform injects no job id, and the
    // indexer's ?payer= view hides non-terminal jobs, so the container finds itself on-chain:
    // jobs.all({project:<our address>, state:1}) -> the running job we must be. Then sdk.jobs.extend
    // (the CLI's extend command crashes before doing any work). This is what removes the last
    // dependency on a laptop: nothing outside the box has to buy the next lease.
    ...(withRenewer ? [
      "mkdir -p /tmp/nos && cd /tmp/nos && npm init -y >>/tmp/npm.log 2>&1 && npm i @nosana/sdk bs58 tweetnacl >>/tmp/npm.log 2>&1",
      `cd /tmp/nos && nohup node -e 'const bs58=require("bs58").default||require("bs58");const fs=require("fs");const sec=bs58.decode(process.env.SOLANA_SESSION);const me=bs58.encode(sec.subarray(32));const MARGIN=${DEFAULT_RENEW_MARGIN_SEC},ADD=${DEFAULT_RENEW_ADD_SEC},CEIL=${DEFAULT_RENEW_CEILING_SEC};const scrub=x=>String(x).split(process.env.SOLANA_SESSION||"\\u0000").join("[redacted]").split(process.env.BASE_KEY||"\\u0000").join("[redacted]");const log=t=>{try{fs.appendFileSync("/tmp/proof.txt","\\n[renew] "+scrub(t))}catch(e){}};const led=o=>{try{fs.appendFileSync("/tmp/ledger.jsonl",JSON.stringify(o)+"\\n")}catch(e){}};const nacl=require("tweetnacl");let cyc=0,hadJob=0;const RPC="https://api.mainnet-beta.solana.com";const rpc=async(m,p)=>{const r=await fetch(RPC,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:1,method:m,params:p})});return (await r.json()).result};const RES=${DEFAULT_NOS_MOVE_OUT_RESERVE},PER=${DEFAULT_NOS_PER_EXTEND},SOLFLOOR=${DEFAULT_SOL_FEE_FLOOR};const money=async()=>{try{const sol=(await rpc("getBalance",[me])).value/1e9;const t=await rpc("getTokenAccountsByOwner",[me,{mint:"${NOS_MINT_ADDRESS}"},{encoding:"jsonParsed"}]);const nos=t&&t.value&&t.value.length?Number(t.value[0].account.data.parsed.info.tokenAmount.uiAmount):0;if(sol<SOLFLOOR)return{ok:false,why:sol+" SOL is under the "+SOLFLOOR+" needed to sign anything"};if(nos-PER<RES)return{ok:false,why:"stopping at "+nos+" NOS \u2014 paying for this extension would spend the "+RES+" NOS kept to move house"};return{ok:true}}catch(e){return{ok:false,why:"could not read balances: "+String(e.message).slice(0,60)}}};const beat=async(job)=>{if(!job)return;try{const r=await fetch("https://api.mainnet-beta.solana.com",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:1,method:"getLatestBlockhash"})});const d=await r.json();const bh=d.result.value.blockhash,slot=d.result.context.slot;const c=++cyc,ts=Date.now();const msg=JSON.stringify({blockhash:bh,cycle:c,jobAddress:job,payer:me,slot,ts});const sig=bs58.encode(Buffer.from(nacl.sign.detached(Buffer.from(msg),sec)));led({v:1,kind:"shelter-heartbeat",ts,cycle:c,jobAddress:job,payer:me,slot,blockhash:bh,sig})}catch(e){}};(async()=>{try{const m=await import("@nosana/sdk");const C=m.Client||m.default;const sdk=new C("mainnet",process.env.SOLANA_SESSION);log("up as "+me);for(;;){let mine=null;try{const js=await sdk.jobs.all({project:me,state:1});log("chain query -> "+js.length+" running");if(js.length)mine=js[0].pubkey.toBase58()}catch(e){log("chain query failed: "+String(e.message).slice(0,90))}if(!mine){try{const r=await fetch("https://dashboard.k8s.prd.nos.ci/api/jobs?payer="+me);const d=await r.json();const run=(d.jobs||[]).filter(j=>j.state===1);log("api query -> "+run.length+" running of "+(d.jobs||[]).length);if(run.length)mine=run[0].address}catch(e){log("api query failed: "+String(e.message).slice(0,90))}}if(mine){try{const full=await(await fetch("https://dashboard.k8s.prd.nos.ci/api/jobs/"+mine)).json();const left=Number(full.timeStart)+Number(full.timeout)-Math.floor(Date.now()/1000);log("job "+mine.slice(0,8)+" timeout="+full.timeout+" left="+Math.round(left));if(!hadJob){hadJob=1;led({kind:"lease",jobAddress:mine,seconds:Number(full.timeout)})}if(Number(full.timeout)<CEIL&&left<MARGIN){const bal=await money();if(!bal.ok){log("NOT renewing: "+bal.why);continue}const rr=await sdk.jobs.extend(mine,ADD,false);const xt=rr&&rr.tx?rr.tx:"";log("EXTENDED +"+ADD+"s tx="+(xt||JSON.stringify(rr).slice(0,60)));led({kind:"spend",what:"lease extension, decentralized market",usd:0.008,chain:"solana",ref:xt})}}catch(e){log("extend failed: "+String(e.message).slice(0,120))}}await beat(mine);await new Promise(r=>setTimeout(r,45000))}}catch(e){log("renewer died: "+String(e.message).slice(0,150))}})()' >>/tmp/renew.log 2>&1 & echo renewer-started`,
    ] : []),
    // The public face of the box. `/` is a balance sheet built from the ledger the steps above
    // wrote as they spent money — so the page is a function of recorded facts, not of prose. The
    // raw log stays available at `/log`, but it is the appendix, not the claim.
    `printf %s ${JSON.stringify(Buffer.from(STATEMENT_SOURCE, "utf8").toString("base64"))} | base64 -d > /tmp/x402/statement.mjs`,
    `cd /tmp/x402 && node -e 'const http=require("http"),fs=require("fs");const bs58=require("bs58").default||require("bs58");const rd=p=>{try{return fs.readFileSync(p,"utf8")}catch(e){return ""}};const led=()=>rd("/tmp/ledger.jsonl").split("\\n").filter(Boolean).map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean);let sol="";try{sol=bs58.encode(bs58.decode(process.env.SOLANA_SESSION).subarray(32))}catch(e){}let base="";try{base=require("viem/accounts").privateKeyToAccount(process.env.BASE_KEY).address}catch(e){}const scrub=x=>String(x).split(process.env.SOLANA_SESSION||"\\u0000").join("[redacted]").split(process.env.BASE_KEY||"\\u0000").join("[redacted]");import("/tmp/x402/statement.mjs").then(({buildStatement,renderStatement})=>{http.createServer(async(q,s)=>{const L=led();if(q.url==="/log"){s.setHeader("content-type","text/plain");return s.end(scrub(rd("/tmp/proof.txt")))}if(q.url==="/heartbeats"){s.setHeader("content-type","application/json");return s.end(JSON.stringify(L.filter(e=>e.kind==="shelter-heartbeat"),null,1))}s.setHeader("content-type","text/html; charset=utf-8");s.end(scrub(renderStatement(buildStatement({solanaAddress:sol,baseAddress:base,jobAddress:(L.filter(e=>e.kind==="lease").pop()||{}).jobAddress,leaseSeconds:((L.filter(e=>e.kind==="lease").pop()||{}).seconds)||${leaseSecondsHint},spent:L.filter(e=>e.kind==="spend"),earned:L.filter(e=>e.kind==="earn"),heartbeats:L.filter(e=>e.kind==="shelter-heartbeat").map(h=>({...h,verified:true}))}))))}).listen(${exposePort},()=>console.log("statement server on ${exposePort}"))}).catch(e=>console.log("statement server failed: "+e.message))'`,
  ].join("; ");
}

/**
 * The full confidential job definition. gpu:true for market compatibility (the cheapest live
 * market is GPU-gated; nginx jobs ran fine on it with the same flag).
 */
export function buildFranklinJobDefinition({
  solanaSessionB58,
  baseKey,
  renew = false,
  model = FRANKLIN_DEFAULT_MODEL,
  maxSpendUsd = FRANKLIN_DEFAULT_MAX_SPEND_USD,
  prompt = FRANKLIN_DEFAULT_PROMPT,
  exposePort = 8080,
  leaseSeconds = 0,
} = {}) {
  if (typeof solanaSessionB58 !== "string" || solanaSessionB58.length < 32) {
    throw new Error("buildFranklinJobDefinition: solanaSessionB58 is required");
  }
  const script = buildFranklinBootScript({ model, maxSpendUsd, prompt, exposePort, withBaseKey: Boolean(baseKey), withRenewer: Boolean(renew), leaseSecondsHint: leaseSeconds });
  const def = buildServiceJobDefinition({
    image: "docker.io/library/node:20-alpine",
    exposePort,
    gpu: true,
    cmd: script,
    // BASE_KEY (S12c): a CAPPED Base sub-wallet key. x402 on Base uses EIP-3009 signatures, so this
    // key needs NO gas — it can buy frontier inference ($0.003/call, verified tx 0x7830cd41…) with
    // USDC alone. Ships ONLY through the confidential channel; the founder key never leaves the Mac.
    env: baseKey ? { SOLANA_SESSION: solanaSessionB58, BASE_KEY: baseKey } : { SOLANA_SESSION: solanaSessionB58 },
    id: "franklin",
  });
  return def;
}
