# REQ-004 operator gate — REAL relay.link dry-run evidence (2026-07-11, thinker-executed)

Command: `ANICCA_HOME=/Users/operator/.blockrun ANICCA_INSTANCE=franklin python3 franklin_sol_base_refill.py --dry-run`
(non-signing; real Solana balance read + real relay.link /quote fetch)

Output (verbatim):
{"ok": true, "dry": true, "step": "franklin_sol_base_refill", "plan": {"sender_solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9", "recipient_base": "0x3EcCAD24794ca298D25378E9902A251322ea8749", "amount_usd": 6.5, "balance_usd": 12.943333, "cap_allowed": true, "cap_reason": "within caps", "fee_pct": 0.341664880349573, "fee_allowed": true, "fee_reason": "within fee cap", "in_usd": 6.498473, "out_usd": 6.47627}}

Verified empirically: (1) relay production /quote DOES return currencyIn.amountUsd / currencyOut.amountUsd (FIND-005 assumption confirmed against live API); (2) destination binding resolves to Franklin's OWN citizens-registry Base address; (3) real round-trip fee 0.34% << 8% cap; (4) caps evaluated on LIVE balance ($12.94).
