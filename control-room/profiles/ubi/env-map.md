# profiles/ubi/env-map.md

## § 1. Env vars

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | vault unlock |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM for recipient classification |
| `CDP_API_KEY_ID` | yes | Bitwarden vault | sign payout tx |
| `CDP_API_KEY_SECRET` | yes | Bitwarden vault | sign |
| `CDP_WALLET_SECRET` | yes | Bitwarden vault | wallet identifier |
| `OPERATOR_DIVIDEND_USDC_ADDRESS` | yes | env per instance | 20% dividend destination (operator-supplied wallet, NOT bank) |
| `UBI_ALLOCATION_REINVEST_PCT` | optional | env override | default `50` |
| `UBI_ALLOCATION_UBI_PCT` | optional | env override | default `25` |
| `UBI_ALLOCATION_OPERATOR_PCT` | optional | env override | default `20` |
| `UBI_ALLOCATION_RESERVE_PCT` | optional | env override | default `5` |
| `UBI_MIN_PAYOUT_USDC` | optional | env override | default `1` (= dust threshold) |

## § 2. Identity (operator dividend address)

`OPERATOR_DIVIDEND_USDC_ADDRESS` is the **only** operator-tied env var in
this profile. It is a USDC wallet address on Base (e.g., a Coinbase smart
wallet, a hardware wallet, a Bitwarden-managed wallet — operator's choice).

| anicca-oss NEVER knows | Operator's bank account, Wise account, exchange account, MUFG details |
| anicca-oss ONLY knows | Operator's USDC-receive address (= 42-char hex) |

If the operator wants to off-ramp USDC to fiat: that happens **outside**
anicca-oss, in the operator's own wallet, after the dividend lands.

## § 3. Recipients allowlist

`~/.hermes/ubi-recipients.json` (operator-curated, gitignored):

```json
{
  "npo": [
    { "name": "<verified NPO name>", "addr": "0x...", "verified_via": "<URL>" }
  ],
  "temple": [
    { "name": "<temple name>", "addr": "0x...", "verified_via": "<URL>" }
  ],
  "amazon_queue": [
    { "label": "<recipient label>", "fulfillment": "private-companion-handles" }
  ],
  "giftee_queue": [
    { "label": "<recipient label>", "fulfillment": "private-companion-handles" }
  ],
  "community_tip_budget_monthly_usdc": 5
}
```

Add a recipient = operator manual edit + restart profile.

## § 4. Allocation config

`~/.hermes/ubi-allocation.json`:

```json
{
  "reinvest_pct": 50,
  "ubi_pct": 25,
  "operator_dividend_pct": 20,
  "reserve_pct": 5,
  "policy_source": "specs/07-HERMES-PIVOT.md § 6 Month 3-6"
}
```

## § 5. Cross-references

| Concept | Authority |
|---|---|
| Vault policy | `control-room/shared/security.md` § 4 |
| UBI spec | `specs/01-EARN-AND-UBI.md` § 3 |
| Anti-goals | `specs/07-HERMES-PIVOT.md` § 9 |

---

**END OF profiles/ubi/env-map.md.**
