import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const JOB="740fd768-1dcb-410c-a7ad-c64ac8be50af";
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const API="https://api.bountybook.ai";
const n=await(await fetch(`${API}/auth/nonce?address=${acct.address}`)).json();const sig=await acct.signMessage({message:String(n.nonce||n.message||n)});
const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:acct.address,signature:sig})})).json();
const H={Authorization:"Bearer "+v.token};
for(let i=0;i<8;i++){
  const r=await(await fetch(`${API}/jobs/${JOB}/status`,{headers:H})).json();
  console.log(`[${i}] status=${r.status} payout=${r.payout_status||"-"} tx=${r.payout_tx_hash||"-"} verif=${JSON.stringify(r.verification_result||"-").slice(0,150)}`);
  if(r.payout_tx_hash||/verified|completed|paid|failed|rejected/i.test(r.status)) break;
  await new Promise(r=>setTimeout(r,5000));
}
