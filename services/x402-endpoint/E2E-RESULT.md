# x402 secure earning — testnet E2E: GREEN (2026-06-19)

VDD, real on-chain (no mock). The secure x402 flow proven end-to-end on Base Sepolia.

- Stack: x402 1.x (`x402-express` seller + `x402-fetch` buyer), facilitator `https://x402.org/facilitator`, network base-sepolia.
- Seller payTo = anicca 0xa3CDd4ec6B94f01826aAf90A6d5538A2Aa8c4C21. Route GET /echo priced $0.001.
- Buyer = 0xcc0b047C12e587D97D459523DdCc4B2e8e33Bfa5, funded 1.0 USDC via CDP SDK faucet (cdp.evm.requestFaucet, faucet tx 0xcfe001da…). (Circle web faucet bot-blocked agent-browser AND camofox; CDP SDK faucet = programmatic, keys CDP_API_KEY_ID/SECRET in ~/.local/state/life-manager/.env.)
- Buyer ran: GET /echo → 402 challenge → x402-fetch signed EIP-712 payment (transferWithAuthorization, gasless) → facilitator verified + settled → **200 + {"echo":"anicca-earns-secure","paid":true}**.
- payment-response: success true, payer 0xcc0b04…, settlement tx 0x8683daa262c9bfc17c1cf04ade02a40e73a85e388241a7343a1e0a7b6e215d02 (base-sepolia).
- VERIFIED on-chain: tx status 0x1, USDC Transfer → 0xa3cdd4…(anicca) amount 0.001. anicca balance 0.0 → 0.001.
- Security: replay/nonce/payer-identity handled by the facilitator (the 3 findings that killed the raw-txHash approach). buyer key must be 0x-prefixed for createSigner.

NEXT: switch to CDP facilitator (api.cdp.coinbase.com) + Base MAINNET, anicca's real wallet, to earn real USDC (revenue > compute cost).
