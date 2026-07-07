import { verifyRepayment } from "/Users/anicca/anicca/skills/economy/lending/lib/lending-verify.mjs";

const RPC = "https://mainnet.base.org";
const RPC2 = "https://base-rpc.publicnode.com"; // independent, separate provider for cross-check

const txHash = "0x849362757b4ec7e2a6f982384475a2d08156b2d3162741880e4719ed05598a44";

function topicToAddress(topic) {
  return "0x" + topic.slice(-40);
}

async function rpcCall(url, method, params) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  const json = await res.json();
  if (json.error) throw new Error(JSON.stringify(json.error));
  return json.result;
}

const receipt = await rpcCall(RPC, "eth_getTransactionReceipt", [txHash]);
const log = receipt.logs.find(l => l.address.toLowerCase() === "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913" && l.topics[0].toLowerCase() === "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef");
const expectedFrom = topicToAddress(log.topics[1]);
const expectedTo = topicToAddress(log.topics[2]);
console.log("Derived from receipt: expectedFrom=", expectedFrom, "expectedTo=", expectedTo, "blockNumber=", receipt.blockNumber);

// independent cross-check via a SEPARATE RPC provider (never trust a single source)
const receipt2 = await rpcCall(RPC2, "eth_getTransactionReceipt", [txHash]);
console.log("Independent RPC2 receipt status:", receipt2.status, "blockNumber:", receipt2.blockNumber, "match:", receipt2.blockNumber === receipt.blockNumber && receipt2.status === receipt.status);

const result = await verifyRepayment({ txHash, expectedFrom, expectedTo, rpcUrl: RPC, loanRows: [] });
console.log("verifyRepayment LIVE result:", JSON.stringify(result));

// negative control: wrong expectedTo must be rejected even though txHash/finalization are real
const badResult = await verifyRepayment({ txHash, expectedFrom, expectedTo: "0x000000000000000000000000000000000000ff", rpcUrl: RPC, loanRows: [] });
console.log("verifyRepayment LIVE negative-control (wrong expectedTo) result:", JSON.stringify(badResult));

// replay-rejection control: a loanRows fixture already recording this REAL txHash as credited must reject it
const replayResult = await verifyRepayment({ txHash, expectedFrom, expectedTo, rpcUrl: RPC, loanRows: [{ loan_id: "loan_x_1", tx_hash: txHash }] });
console.log("verifyRepayment LIVE replay-rejection control result:", JSON.stringify(replayResult));
