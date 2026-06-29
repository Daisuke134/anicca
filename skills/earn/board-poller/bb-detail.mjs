import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const API="https://api.bountybook.ai";
const n=await(await fetch(`${API}/auth/nonce?address=${acct.address}`)).json();
const sig=await acct.signMessage({message:String(n.nonce||n.message||n)});
const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:acct.address,signature:sig})})).json();
const tok=v.token;
for(const id of process.argv.slice(2)){
  const j=await(await fetch(`${API}/jobs/${id}`,{headers:{Authorization:"Bearer "+tok}})).json();
  const job=j.job||j;
  console.log("\n===== $"+job.budget_usdc+" | "+job.title+" | "+job.status+" =====");
  console.log("instructions:",job.spec?.instructions);
  console.log("test_code:\n"+(job.spec?.success_condition?.test_code||JSON.stringify(job.spec?.success_condition)));
}
