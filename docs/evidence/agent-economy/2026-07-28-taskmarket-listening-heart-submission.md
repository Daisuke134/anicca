# TaskMarket listening-heart x402 note — live submission evidence

## Outcome

The dedicated worker paid the external requester's live x402 endpoint and submitted the returned proof to TaskMarket. This is a real paid-work attempt, but the 0.50 USDC bounty remains pending and is not revenue.

| Field | Verified value |
|---|---|
| Task | `0x50d1dea29821649b87c2cb08558bd9cd984c9678d9f8d30ce608eef877ca5448` |
| External requester / x402 payTo | `0x79d86d70588Ed7f9742446849417d50d3Bf1a707` |
| Worker wallet | `0xd7Db94062AFec8a86F70250B931C77619acf8937` |
| Proof note | `3f9a1ded-0fa1-4e2b-861f-4a7278e99c92` |
| Paid note readback | HTTP `201`, author/task/content/type/payment amount exact |
| Submission | `801e15f9-9856-48af-8e82-0aeeda4818eb` |
| Submitted at | `2026-07-28T07:20:40.510Z` |
| Gross / net reward | `0.500000 / 0.462500 USDC` |
| TaskMarket submit transaction | `0x7364370147788b04ddda9124d80329c997ceaf898c20af999de2c743f2253c79` |
| TaskMarket Base receipt | `status=0x1`, block `0x2eefdb3`, 7 confirmations at verification |
| Ledger bridge after kick | `runs=21`, `tasks_seen=10`, `pending=10`, `recorded=0`, exit `0`, stderr empty |

## Live x402 payment

The written task and reference claimed Base Sepolia, but the live `payment-required` header advertised `eip155:8453`, Base mainnet USDC, amount `1000`, and requester `payTo`. The live challenge is the authoritative settlement contract.

The worker began with zero mainnet USDC. Franklin 2 supplied exactly `0.002000 USDC` as agent-owned bootstrap capital through the self-hosted facilitator:

| Transfer | Transaction | Receipt |
|---|---|---|
| Franklin 2 → worker, `2000` atomic | `0x65034f070374f7dd6ce624717dfaad909b93f663ebe2deddc3925bf8b2ef8741` | success, block `49216907` |
| worker → external requester, `1000` atomic | `0x0469785e67e0f2d98d9df39834b34612a098485045676e22f2a9b471293024d2` | success, block `49216924`, exact USDC `Transfer` |

Post-payment balances were Franklin 2 `0.017000 USDC` and worker `0.001000 USDC`. Bootstrap capital and acquisition cost are not external revenue.

## Artifact contract

The single delivered file was `listening-heart-proof.txt`, 37 bytes, MIME `text/plain`, SHA-256 `b91991c0a04e29d40393f061960984dd49b9a3fd4656a2d26c4140abba54d739`. Local and marketplace hashes match.

## Revenue boundary

The marketplace still reports the owned work as pending, and the ledger loop returned `recorded=0`. Verified external revenue remains `$0.00`.

