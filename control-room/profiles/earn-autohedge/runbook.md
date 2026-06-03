# profiles/earn-autohedge/runbook.md

## § 1. Restart

```bash
hermes -p earn-autohedge -g "halt: close in-flight swaps if safe, exit clean"
sleep 3
hermes profile start earn-autohedge
hermes -p earn-autohedge -g "report current positions and 24h PnL"
```

## § 2. Logs

```bash
tail -F ~/.hermes/logs/autohedge-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[earn-autohedge\]'
```

## § 3. Kickstart on circuit-breaker trip

If drawdown > 10% in 24h, profile auto-halts. To resume:

```bash
# 1. inspect what tripped
grep "circuit_breaker" ~/.hermes/logs/autohedge-audit.log | tail -20

# 2. confirm market conditions are sane (not flash-crash mid-recovery)
hermes -p earn-autohedge -g "report current volatility 1h / 24h / 7d for allowlisted pairs"

# 3. resume manually with explicit operator override
hermes -p earn-autohedge -g "resume autohedge: operator override after circuit breaker review. Note PnL = <X>."
```

## § 4. Common errors + fixes

| Error | Cause | Fix |
|---|---|---|
| `Slippage exceeded tolerance` | thin liquidity at trade time | reduce position size in `autohedge-config.json`, retry |
| `Insufficient USDC balance for bankroll cap` | wallet drained by other profiles | check `earn-x402` revenue + `ubi` payouts |
| `Jupiter API 429` | rate limit | switch to alternate Solana DEX aggregator OR exponential backoff |
| `1inch swap reverted` | front-run / MEV | use 1inch private RPC OR smaller size |
| `Position out of sync with on-chain` | crash mid-tx + restart | run reconciliation: `hermes -p earn-autohedge -g "reconcile positions.json with on-chain wallet state"` |
| `Bankroll cap exceeded` | concurrent trades from prior crash | review `positions.json`; close manual if needed |
| `LLM tool-call hallucinated swap path` | model regression | switch to fallback (Qwen3.7 Max) |

## § 5. Manual PnL audit

```bash
# weekly PnL summary
DATE=$(date -u +%Y-%m-%d)
START=$(date -u -d '7 days ago' +%Y-%m-%d 2>/dev/null || date -u -v-7d +%Y-%m-%d)
grep "trade_close" ~/.hermes/logs/autohedge-audit.log \
  | awk -F'"' -v start="$START" -v end="$DATE" \
    '$0 >= start && $0 <= end {sum += $X}' # pseudocode; adjust to JSONL parsing
```

Easier with jq:

```bash
grep "trade_close" ~/.hermes/logs/autohedge-audit.log \
  | jq -s 'map(select(.timestamp > "'$(date -u -d '7 days ago' -Iseconds)'") | .pnl_usdc | tonumber) | add'
```

## § 6. Emergency stop

```bash
hermes -p earn-autohedge -g "halt: cancel open orders, hold current positions (do NOT close), exit"
```

To close positions immediately (= cash out to USDC):

```bash
hermes -p earn-autohedge -g "emergency unwind: close ALL positions to USDC at market, halt, exit"
```

## § 7. Cross-references

| Concept | Authority |
|---|---|
| AutoHedge OSS | `github.com/The-Swarm-Corporation/AutoHedge` |
| Risk module reference | `~/.openclaw/skills/anicca-autohedge/vendor/risk_manager.py` |
| Fuel-broker allocation rules | `anicca-oss/skills/anicca-fuel-broker/SKILL.md` |
| Spec 01 § 1.1 | `specs/01-EARN-AND-UBI.md` |

---

**END OF profiles/earn-autohedge/runbook.md.**
