import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const JOB="87b131ee-7102-4d69-a99d-08cff67e9c1a";
const CODE=readFileSync("/tmp/bb-work/state_machine.py","utf8");
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const addr=acct.address;const API="https://api.bountybook.ai";
async function tok(){const n=await(await fetch(`${API}/auth/nonce?address=${addr}`)).json();const sig=await acct.signMessage({message:String(n.nonce||n.message||n)});const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:addr,signature:sig})})).json();return v.token;}
const t=await tok();const H={Authorization:"Bearer "+t,"content-type":"application/json"};
await fetch(`${API}/jobs/${JOB}/claim`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr})});
const sub=await fetch(`${API}/jobs/${JOB}/submit`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr,outputData:{"state_machine.py":CODE}})});
console.log("submit:",sub.status);
for(let i=0;i<9;i++){
  await new Promise(r=>setTimeout(r,3000));
  const j=(await(await fetch(`${API}/jobs/${JOB}`,{headers:H})).json());const job=j.job||j;
  console.log(`[${i}] status=${job.status} verif=${JSON.stringify(job.verification_result||job.verification||job.oracle_result||job.last_error||"-").slice(0,200)}`);
  if(/verified|completed|paid|failed|rejected/i.test(job.status)) break;
}
