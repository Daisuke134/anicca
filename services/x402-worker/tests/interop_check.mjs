// Verify viem recoverTypedDataAddress agrees with the Python eth_account signature.
// Reads a base64 receipt on argv[2], recovers the signer with the SAME domain/types as
// index.ts, prints the recovered address. Exit 0 = recovered, used by the interop test.
import { recoverTypedDataAddress } from "viem";

const b64 = process.argv[2];
const r = JSON.parse(Buffer.from(b64, "base64").toString("utf-8"));

const recovered = await recoverTypedDataAddress({
  domain: {
    name: "USD Coin",
    version: "2",
    chainId: Number(r.chain_id),
    verifyingContract: r.verifying_contract,
  },
  types: {
    TransferWithAuthorization: [
      { name: "from", type: "address" },
      { name: "to", type: "address" },
      { name: "value", type: "uint256" },
      { name: "validAfter", type: "uint256" },
      { name: "validBefore", type: "uint256" },
      { name: "nonce", type: "bytes32" },
    ],
  },
  primaryType: "TransferWithAuthorization",
  message: {
    from: r.from,
    to: r.to,
    value: BigInt(r.value_atomic),
    validAfter: BigInt(r.valid_after),
    validBefore: BigInt(r.valid_before),
    nonce: r.nonce,
  },
  signature: r.signature,
});

console.log(JSON.stringify({ recovered, from: r.from, match: recovered.toLowerCase() === r.from.toLowerCase() }));
