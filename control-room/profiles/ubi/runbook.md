# profiles/ubi/runbook.md

## § 1. Restart

```bash
hermes -p ubi -g "halt: finish in-flight payouts, exit"
sleep 3
hermes profile start ubi
hermes -p ubi -g "report MTD payouts by category"
```

## § 2. Logs

```bash
tail -F ~/.hermes/logs/ubi-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[ubi\]'
```

## § 3. Common errors + fixes

| Error | Cause | Fix |
|---|---|---|
| `Recipient not on allowlist` | operator hasn't added | operator edits `~/.hermes/ubi-recipients.json` + restart profile |
| `OFAC list outdated (>48h)` | daily refresh failed | force refresh: `hermes -p ubi -g "refresh OFAC list now"` |
| `OFAC match` | tried to pay sanctioned address | refuse; alert operator; log |
| `Treasury cap exceeded (per-tx / hourly / daily)` | too many payouts | rate-limit; queue overflow to next window |
| `USDC balance insufficient` | wallet drained by earn-side losses | halt UBI; alert operator |
| `Transfer reverted on-chain` | gas spike / RPC issue | retry; if persistent, switch RPC |
| `Operator dividend address invalid` | env typo | operator must fix `OPERATOR_DIVIDEND_USDC_ADDRESS` |
| `Amazon queue not draining` | private companion is down | log; private companion is out of scope for anicca-oss to fix |

## § 4. Payout inspection

```bash
# MTD by category
grep "$(date +%Y-%m)" ~/.hermes/logs/ubi-audit.log \
  | jq -s 'group_by(.category) | map({cat: .[0].category, total_usdc: (map(.amount_usdc | tonumber) | add)})'

# all-time operator dividend
grep "category=operator_dividend" ~/.hermes/logs/ubi-audit.log \
  | jq -s 'map(.amount_usdc | tonumber) | add'

# all-time community tips
grep "category=community_tip" ~/.hermes/logs/ubi-audit.log \
  | jq -s 'map(.amount_usdc | tonumber) | add'
```

## § 5. Manual payout (debug)

```bash
hermes -p ubi -g "manual payout: send 1 USDC to <addr> as test-npo, log to ubi-audit.log. Confirm on-chain receipt before completing task."
```

## § 6. Allocation reconciliation

```bash
# does actual MTD split match policy?
hermes -p ubi -g "reconcile MTD payouts against ubi-allocation.json policy; report drift % per category; if drift > 5%, propose correction next month."
```

## § 7. Emergency stop

```bash
hermes -p ubi -g "halt: do not send any more payouts, exit. Reason: <operator note>."
```

## § 8. Recipient onboarding

Adding a new NPO / temple:

```bash
# 1. operator verifies the recipient (= reads their published USDC-receive
#    address from their official site; checks OFAC; checks domain authenticity)

# 2. operator edits ~/.hermes/ubi-recipients.json (add object)

# 3. restart profile
hermes profile restart ubi

# 4. test with $1
hermes -p ubi -g "test payout 1 USDC to <new recipient>: verify receipt on-chain, log to ubi-audit.log as onboarding-test."

# 5. confirm receipt with recipient (operator step, outside anicca-oss)
```

## § 9. Cross-references

| Concept | Authority |
|---|---|
| UBI spec | `specs/01-EARN-AND-UBI.md` § 3 |
| First payout milestone | `specs/14-UBI-FIRST-PAYOUT.md` |
| Allocation policy | `specs/07-HERMES-PIVOT.md` § 6 |

---

**END OF profiles/ubi/runbook.md.**
