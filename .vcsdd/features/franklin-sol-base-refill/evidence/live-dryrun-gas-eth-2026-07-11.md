# REQ-GAS-004 gate — REAL relay.link --gas-eth dry-run evidence (2026-07-11, thinker, RE-RUN at commit 6fe4908e post-FIND-003)

Command: `ANICCA_HOME=/Users/operator/.blockrun ANICCA_INSTANCE=franklin python3 franklin_sol_base_refill.py --gas-eth --recipient 0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3 --dry-run` (non-signing; real relay /quote, USDC-Solana → native-ETH-Base)

Output (verbatim, at HEAD 6fe4908e — confirms FIND-003 normalization: recipient_base is now LOWERCASED, the exact payload --live will submit):
{"ok": true, "dry": true, "step": "franklin_gas_eth_refill", "plan": {"sender_solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9", "recipient_base": "0x1f5b17f41524b02a4ee4d99d4158c86c942e43f3", "amount_usd": 3.0, "balance_usd": 6.443333, "cap_allowed": true, "cap_reason": "within caps", "fee_pct": 0.8153387031330317, "fee_allowed": true, "fee_reason": "within fee cap", "in_usd": 2.999367, "out_usd": 2.974912, "expected_wei": 1655080333753168}}

Confirmed for the ACTUAL pair + ACTUAL payload the current code submits: relay returns currencyOut.amount → expected_wei=1655080333753168 (~0.001655 ETH ≈ $2.97), lowercased recipient accepted, fee 0.82% << 12% cap. Supersedes the pre-normalization capture (iter4 FIND-001).
