import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const JOB="87b131ee-7102-4d69-a99d-08cff67e9c1a";
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const API="https://api.bountybook.ai";
const n=await(await fetch(`${API}/auth/nonce?address=${acct.address}`)).json();
const sig=await acct.signMessage({message:String(n.nonce||n.message||n)});
const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:acct.address,signature:sig})})).json();
const H={Authorization:"Bearer "+v.token};
for(let i=0;i<10;i++){
  const j=(await(await fetch(`${API}/jobs/${JOB}`,{headers:H})).json());const job=j.job||j;
  console.log(`[${i}] status=${job.status} payout=${job.payout_status||"-"} tx=${job.payout_tx_hash||"-"} verif=${JSON.stringify(job.verification_result||"").slice(0,120)}`);
  if(/verified|completed|paid|failed|rejected/i.test(job.status)||job.payout_tx_hash){break;}
  await new Promise(r=>setTimeout(r,12000));
}
