# profiles/ubi/docker.md

Shares `hermes-runtime:latest`. See `profiles/orch/docker.md`.

## § 1. Profile-specific notes

| Item | Detail |
|---|---|
| Negligible local CPU/RAM | most work is API + LLM + on-chain |
| OFAC list update | daily refresh from `home.treasury.gov` sanctions list; cached locally |

## § 2. Mounted volumes

| Mount path | Purpose |
|---|---|
| `/root/.hermes/profiles/<instance>-ubi/` | config |
| `/root/.hermes/ubi-recipients.json` | allowlist |
| `/root/.hermes/ubi-allocation.json` | current split |
| `/root/.hermes/ofac-list/` | cached sanctions list |
| `/root/.hermes/logs/ubi-audit.log` | forever-retention payout log |

## § 3. Network

| Direction | Allowed |
|---|---|
| Egress to `mainnet.base.org` | yes (USDC transfer) |
| Egress to `home.treasury.gov` (OFAC list) | yes (daily) |
| Egress to OpenRouter | yes (LLM for recipient classification) |
| Egress to basescan API | yes (verify tx receipt) |
| Inbound | none |

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Shared sandbox | `profiles/orch/docker.md` |
| OFAC SDN list | `home.treasury.gov/policy-issues/financial-sanctions/specially-designated-nationals-and-blocked-persons-list-sdn-human-readable-lists` |

---

**END OF profiles/ubi/docker.md.**
