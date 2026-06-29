// auth to BountyBook with the founder wallet + list open jobs WITH full specs.
import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";

const w = JSON.parse(readFileSync(process.env.HOME + "/.anicca-founder/wallet.json", "utf8"));
let pk = w.private_key.startsWith("0x") ? w.private_key : "0x" + w.private_key;
const account = privateKeyToAccount(pk);
const addr = account.address;
const API = "https://api.bountybook.ai";

const nonceR = await (await fetch(`${API}/auth/nonce?address=${addr}`)).json();
const nonce = nonceR.nonce || nonceR.message || nonceR;
const signature = await account.signMessage({ message: String(nonce) });
const verR = await (await fetch(`${API}/auth/verify`, {
  method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ address: addr, signature }),
})).json();
const token = verR.token;
console.log("auth:", token ? "OK (token len " + token.length + ")" : JSON.stringify(verR).slice(0, 200));
if (!token) process.exit(1);

const jobsR = await (await fetch(`${API}/jobs?status=open&limit=20`, { headers: { Authorization: "Bearer " + token } })).json();
const jobs = (jobsR.jobs || []).filter((j) => j.status === "open" && j.job_type === "code");
console.log(`open code jobs: ${jobs.length}`);
for (const j of jobs.slice(0, 6)) {
  console.log("\n=== " + j.id + " | $" + j.budget_usdc + " | " + j.difficulty + " | " + j.estimated_minutes + "min ===");
  console.log("TITLE:", j.title);
  console.log("SPEC:", JSON.stringify(j.spec).slice(0, 600));
}
// also save token for reuse
process.stdout.write("\n__TOKEN__=" + token + "\n__ADDR__=" + addr + "\n");
