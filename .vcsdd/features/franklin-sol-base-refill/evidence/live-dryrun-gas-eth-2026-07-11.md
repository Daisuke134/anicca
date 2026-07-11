# REQ-GAS-004 gate — REAL relay.link --gas-eth dry-run evidence (2026-07-11, thinker-executed)

Command: `ANICCA_HOME=/Users/operator/.blockrun ANICCA_INSTANCE=franklin python3 franklin_sol_base_refill.py --gas-eth --recipient 0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3 --dry-run` (non-signing; real relay /quote for USDC-Solana → native-ETH-Base)

Output (verbatim):
{"ok": true, "dry": true, "step": "franklin_gas_eth_refill", "plan": {"sender_solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9", "recipient_base": "0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3", "amount_usd": 3.0, "balance_usd": 6.443333, "cap_allowed": true, "cap_reason": "within caps", "fee_pct": 0.7866224179054159, "fee_allowed": true, "fee_reason": "within fee cap", "in_usd": 2.999406, "out_usd": 2.975812, "expected_wei": 1654875211425918}}

Confirmed empirically for the ACTUAL pair (not a docs example): relay returns currencyOut.amount (raw wei) → expected_wei=1654875211425918 (~0.001655 ETH ≈ $2.98) AND currencyIn/Out.amountUsd. Native-ETH currency id 0x0000...0000 accepted. Fee 0.79% << 12% cap. Recipient = facilitator signer 0x1F5b (needs Base ETH gas).
