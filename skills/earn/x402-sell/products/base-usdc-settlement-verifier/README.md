# Base USDC Settlement Verifier

A dependency-free Node.js module and CLI that verifies a claimed Base USDC payment against the chain instead of trusting a marketplace status or balance change.

It returns a compact proof only when all of these checks pass:

- chain ID is Base mainnet (`8453`)
- receipt status is successful
- receipt block is at or below the `finalized` head
- receipt block hash matches the canonical block at that height
- exactly one Base USDC `Transfer` matches the expected recipient and atomic amount
- transfer sender and transaction initiator are not in the supplied self-wallet set

## Install and test

Requires Node.js 20 or newer and has no runtime dependencies.

```bash
npm test
```

## Library usage

```js
import { verifyBaseUsdcSettlement } from './src/verifier.mjs';

const proof = await verifyBaseUsdcSettlement({
  txHash: '0x...',
  expectedPayTo: '0x...',
  expectedAmountAtomic: '30000', // 0.03 USDC, six decimals
  selfWallets: ['0x...'],
});

console.log(proof);
```

You can inject `rpcUrl` and `fetchImpl`; the latter makes deterministic testing straightforward.

## CLI usage

```bash
node bin/verify.mjs \
  --tx 0x... \
  --pay-to 0x... \
  --amount-atomic 30000 \
  --self-wallet 0x...
```

On success the CLI prints one JSON proof. On failure it exits non-zero and does not print private keys, payment headers, prompts, or transaction calldata.

## Security boundary

This verifier proves an exact finalized token transfer. It does not by itself prove which product was delivered, marketplace provenance, buyer intent, gas/compute cost, or profit. Bind the returned transaction hash to trusted sales telemetry before recording revenue.

Keep every wallet you control in `selfWallets`. If an owned sender is omitted, an internal transfer can look external.

## Protocol sources

- [Ethereum Execution APIs: `eth_getBlockByNumber`](https://github.com/ethereum/execution-apis/blob/main/docs-api/api/methods/eth_getBlockByNumber.mdx) defines the `finalized` block tag.
- [Ethereum Execution APIs: `eth_getTransactionReceipt`](https://github.com/ethereum/execution-apis/blob/main/docs-api/api/methods/eth_getTransactionReceipt.mdx) defines receipt status and logs.
- [ERC-20](https://eips.ethereum.org/EIPS/eip-20#events) defines the `Transfer(address indexed from, address indexed to, uint256 value)` event.

## License

Offered under the SpawnXchange Standard Buyer License v1. See `LICENSE`.
