import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const addr=acct.address;const API="https://api.bountybook.ai";
const n=await(await fetch(`${API}/auth/nonce?address=${addr}`)).json();const sig=await acct.signMessage({message:String(n.nonce||n.message||n)});
const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:addr,signature:sig})})).json();
const H={Authorization:"Bearer "+v.token,"content-type":"application/json"};
const jr=await(await fetch(`${API}/jobs?status=open&limit=20`,{headers:H})).json();
const codes=(jr.jobs||[]).filter(j=>j.status==="open"&&j.job_type==="code"&&j.id!=="87b131ee-7102-4d69-a99d-08cff67e9c1a");
console.log("fresh open code jobs:",codes.length);
const job=codes[0]; if(!job){console.log("none");process.exit(0);}
console.log("trying:",job.id,"$"+job.budget_usdc,job.title.slice(0,40));
const cl=await(await fetch(`${API}/jobs/${job.id}/claim`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr})})).json();
console.log("claim resp:",JSON.stringify(cl).slice(0,150));
await new Promise(r=>setTimeout(r,2500));
const st=await(await fetch(`${API}/jobs/${job.id}/status`,{headers:H})).json();
console.log("status after claim: status="+st.status+" executor="+st.executor_address);
process.stdout.write("\nJOBID="+job.id+"\n");
