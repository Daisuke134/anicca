# profiles/earn-bittensor/runbook.md

## § 1. Restart

```bash
hermes -p earn-bittensor -g "halt: pause mining, do not deregister subnets, exit"
sleep 3
hermes profile start earn-bittensor
hermes -p earn-bittensor -g "report active subnet positions and 24h yield"
```

## § 2. Logs

```bash
tail -F ~/.hermes/logs/bittensor-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[earn-bittensor\]'
```

## § 3. Common errors + fixes

| Error | Cause | Fix |
|---|---|---|
| `Substrate endpoint timeout` | finney endpoint flaky | switch to alternate (`docs.bittensor.com/getting-started/installation`) |
| `Subnet registration failed: insufficient TAO` | bankroll cap reached or wallet drained | top up via `tao_to_usdc_swap` reverse (USDC → TAO) up to cap |
| `Wallet password incorrect` | `BITTENSOR_WALLET_PASSWORD` rotation didn't propagate | re-encrypt keystore with new password (operator manual step) |
| `Subnet APY dropped below threshold` | subnet competition increased | deregister + try another subnet |
| `Miner process crashed` | subnet-specific bug | restart miner; if recurring, abandon subnet |
| `TAO ↔ USDC swap reverted` | DEX slippage OR Kraken withdrawal limit | retry with smaller size; verify Kraken withdrawal whitelist |
| `Bankroll cap exceeded by TAO position appreciation` | TAO price rallied | sell down to cap; do NOT touch above-cap (= profit, gets routed to UBI) |

## § 4. Subnet inspection

```bash
# active positions
cat ~/.hermes/profiles/<instance>-earn-bittensor/subnet-positions.json | jq

# per-subnet yield
hermes -p earn-bittensor -g "report yield per subnet for last 7d"
```

## § 5. Manual subnet registration

```bash
hermes -p earn-bittensor -g "register on subnet <UID>: confirm bankroll cap not exceeded, register, log to bittensor-audit.log"
```

## § 6. Manual TAO → USDC swap

```bash
hermes -p earn-bittensor -g "swap 0.5 TAO to USDC via Kraken (or DEX). Confirm rate before executing. Log to bittensor-audit.log."
```

## § 7. Emergency stop

```bash
hermes -p earn-bittensor -g "halt: stop mining, deregister all subnets (= recover TAO burn), swap recovered TAO → USDC, exit"
```

NOTE: deregister recovers most but not all of the registration burn (subnet-dependent).

## § 8. Cross-references

| Concept | Authority |
|---|---|
| Subnet template | `github.com/opentensor/text-prompting` (example) |
| Substrate endpoint health | `status.opentensor.ai` |
| Spec 01 § 1 | `specs/01-EARN-AND-UBI.md` |

---

**END OF profiles/earn-bittensor/runbook.md.**
