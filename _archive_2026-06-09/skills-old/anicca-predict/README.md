# anicca-predict (#337 P14 — Wave 1)

PREDICTION primitive of the colony swarm (MiroFish-style outcome wager): record a testable claim
+ a stake, resolve it after the deadline. Full design:
`docs/superpowers/specs/2026-06-05-p14-swarm-skills-design.md` §2.

```
scripts/predict.sh <claim_text> <stake_usdc_str>   # open  (rejects non-testable claims, exit 64)
scripts/resolve.sh                                  # resolve expired open predictions (cron 6h)
```

A claim must carry an explicit metric AND a deadline. `resolve.sh` runs a claim-specific evidence
script (`predict-evidence/<id>.sh` → stdout `won`/`lost`) or marks `unresolved`, and appends a
**mock** pot row (Wave 1 = no real transfer).

Wave 1 is dry-run: stake is recorded, no USDC moves. Wave 2 swaps the mock pot for
`wallet_lib.send_usdc()` (gated on #324-wave2 + wallet ≥$5). See `SKILL.md`.

Test: `bash skills/anicca-predict/tests/test_predict.sh` (offline, 4 assertions).
