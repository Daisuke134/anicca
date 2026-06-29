import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const JOB="740fd768-1dcb-410c-a7ad-c64ac8be50af";
const CODE=readFileSync("/tmp/bb-work/flatten.py","utf8");
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const addr=acct.address;const API="https://api.bountybook.ai";
const n=await(await fetch(`${API}/auth/nonce?address=${addr}`)).json();const sig=await acct.signMessage({message:String(n.nonce||n.message||n)});
const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:addr,signature:sig})})).json();
const H={Authorization:"Bearer "+v.token,"content-type":"application/json"};
const cl=await(await fetch(`${API}/jobs/${JOB}/claim`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr})})).json();
console.log("claim:",cl.status);
const st1=await(await fetch(`${API}/jobs/${JOB}/status`,{headers:H})).json();console.log("after claim: status="+st1.status+" exec="+st1.executor_address);
const sub=await(await fetch(`${API}/jobs/${JOB}/submit`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr,outputData:{"flatten.py":CODE}})})).json();
console.log("submit:",sub.status,sub.message||"");
for(let i=0;i<7;i++){await new Promise(r=>setTimeout(r,5000));const r=await(await fetch(`${API}/jobs/${JOB}/status`,{headers:H})).json();console.log(`[${i}] status=${r.status} exec=${r.executor_address} payout=${r.payout_status||"-"} tx=${r.payout_tx_hash||"-"} verif=${JSON.stringify(r.verification_result||"-").slice(0,120)}`);if(r.payout_tx_hash||/verified|completed|paid|failed|rejected/i.test(r.status))break;}
