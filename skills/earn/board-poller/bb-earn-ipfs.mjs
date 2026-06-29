import lighthouse from "@lighthouse-web3/sdk";
import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const JOB="740fd768-1dcb-410c-a7ad-c64ac8be50af";
const CODE=readFileSync("/tmp/bb-work/flatten.py","utf8");
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const addr=acct.address;
// 1. lighthouse api key (wallet-derived, no secret stored)
const msg=JSON.parse(await(await fetch(`https://api.lighthouse.storage/api/auth/get_message?publicKey=${addr}`)).text());
const signed=await acct.signMessage({message:String(msg)});
const ak=(await(await fetch("https://api.lighthouse.storage/api/auth/create_api_key",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({publicKey:addr,signedMessage:signed,keyName:"anicca-"+Date.now()})})).text()).replace(/"/g,"");
console.log("lighthouse key:",ak.slice(0,8)+"…");
// 2. upload code → CID
const up=await lighthouse.uploadText(CODE,ak,"flatten.py");
const CID=up.data.Hash;
console.log("CID:",CID,"→ https://gateway.lighthouse.storage/ipfs/"+CID);
// verify CID is fetchable (oracle will fetch it)
const fetched=await(await fetch("https://gateway.lighthouse.storage/ipfs/"+CID)).text();
console.log("CID content matches:",fetched.trim()===CODE.trim());
// 3. BountyBook auth → claim → submit outputCID
const API="https://api.bountybook.ai";
const n=await(await fetch(`${API}/auth/nonce?address=${addr}`)).json();const bsig=await acct.signMessage({message:String(n.nonce||n.message||n)});
const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:addr,signature:bsig})})).json();
const H={Authorization:"Bearer "+v.token,"content-type":"application/json"};
const cl=await(await fetch(`${API}/jobs/${JOB}/claim`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr})})).json();console.log("claim:",cl.status);
const sub=await(await fetch(`${API}/jobs/${JOB}/submit`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr,outputCID:CID})})).json();console.log("submit:",sub.status,sub.message||"");
// 4. poll
for(let i=0;i<8;i++){await new Promise(r=>setTimeout(r,6000));const r=await(await fetch(`${API}/jobs/${JOB}/status`,{headers:H})).json();console.log(`[${i}] status=${r.status} payout=${r.payout_status||"-"} tx=${r.payout_tx_hash||"-"} verif=${JSON.stringify(r.verification_result||"-").slice(0,140)}`);if(r.payout_tx_hash||/verified|completed|paid|failed|rejected/i.test(r.status))break;}
