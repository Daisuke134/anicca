import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const JOB="740fd768-1dcb-410c-a7ad-c64ac8be50af";
const CODE=readFileSync("/tmp/bb-work/flatten.py","utf8");
const env=readFileSync(process.env.HOME+"/.anicca-founder/pinata.env","utf8");
const JWT=env.match(/PINATA_JWT=(.+)/)[1].trim();
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const addr=acct.address;
// 1. pin to Pinata (public IPFS)
const fd=new FormData();
fd.append("file",new Blob([CODE],{type:"text/x-python"}),"flatten.py");
const pin=await(await fetch("https://api.pinata.cloud/pinning/pinFileToIPFS",{method:"POST",headers:{Authorization:"Bearer "+JWT},body:fd})).json();
const CID=pin.IpfsHash;
console.log("pinned CID:",CID);
// 2. verify retrievable (oracle must fetch this)
await new Promise(r=>setTimeout(r,4000));
for(const gw of ["https://gateway.pinata.cloud/ipfs/","https://ipfs.io/ipfs/","https://dweb.link/ipfs/"]){
  try{const t=await(await fetch(gw+CID,{redirect:"follow",signal:AbortSignal.timeout(20000)})).text();console.log(gw,"=>",t.trim()===CODE.trim()?"MATCH":("got "+t.slice(0,30)));}catch(e){console.log(gw,"=> ERR",e.name);}
}
// 3. BountyBook claim + submit outputCID
const API="https://api.bountybook.ai";
const n=await(await fetch(`${API}/auth/nonce?address=${addr}`)).json();const bsig=await acct.signMessage({message:String(n.nonce||n.message||n)});
const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:addr,signature:bsig})})).json();
const H={Authorization:"Bearer "+v.token,"content-type":"application/json"};
const cl=await(await fetch(`${API}/jobs/${JOB}/claim`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr})})).json();console.log("claim:",cl.status);
const sub=await(await fetch(`${API}/jobs/${JOB}/submit`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr,outputCID:CID})})).json();console.log("submit:",sub.status,sub.message||"");
// 4. poll up to 5 min (oracle may be slow)
for(let i=0;i<25;i++){await new Promise(r=>setTimeout(r,12000));const r=await(await fetch(`${API}/jobs/${JOB}/status`,{headers:H})).json();console.log(`[${i}] status=${r.status} payout=${r.payout_status||"-"} tx=${r.payout_tx_hash||"-"}`);if(r.payout_tx_hash||/verified|completed|paid|failed|rejected/i.test(r.status)){console.log("FINAL verif:",JSON.stringify(r.verification_result||r));break;}}
const prof=await(await fetch(`${API}/agents/${addr}`)).json();console.log("PROFILE earned:",prof.total_earned,"completed:",prof.jobs_completed,"failed:",prof.jobs_failed);
