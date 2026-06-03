# profiles/earn-farcaster/runbook.md

## § 1. Restart

```bash
hermes -p earn-farcaster -g "halt: stop cast queue, finish in-flight replies, exit"
sleep 3
hermes profile start earn-farcaster
hermes -p earn-farcaster -g "report follower count, 24h cast count, 24h tip revenue"
```

## § 2. Logs

```bash
tail -F ~/.hermes/logs/farcaster-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[earn-farcaster\]'
```

## § 3. Common errors + fixes

| Error | Cause | Fix |
|---|---|---|
| `Neynar 401` | API key rotated, not propagated | `bws secret edit NEYNAR_API_KEY ...` + restart |
| `Signer UUID invalid` | signer revoked or expired | generate new managed signer via Neynar dashboard; update vault |
| `Cast publish rate-limited` | Neynar tier limit | space out casts; consider tier upgrade |
| `Frame endpoint 404` | tunnel routing broken | check `earn-x402` reverse proxy config |
| `Frame button action failed` | LLM hallucinated payload | strengthen schema validation |
| `Tip received but not indexed` | event listener stale | restart cast→wallet inflow indexer |
| `Persona drift (off-topic casts)` | model regression | re-anchor with persona.md few-shot examples |
| `Spam accusation` | replied too aggressively to mentions | tighten reply policy; manual review of last 24h replies |

## § 4. Cast inspection

```bash
# 24h casts
grep "cast_publish" ~/.hermes/logs/farcaster-audit.log | tail -50

# tips received 30d
grep "tip_received" ~/.hermes/logs/farcaster-audit.log | jq -s 'map(.amount_usdc | tonumber) | add'

# follower growth
hermes -p earn-farcaster -g "report follower count delta vs 7d ago"
```

## § 5. Manual cast publish (debug)

```bash
hermes -p earn-farcaster -g "publish cast: 'Anicca instance <name> wallet now at <addr>. /research for 0.30 USDC.' Do NOT post yet; show me the draft."
```

## § 6. Manual tip to high-signal caster

```bash
hermes -p earn-farcaster -g "tip 1 USDC to fid:<fid> on cast hash <hash>. Reason: <justify>. Log to ubi-audit.log (= categorize as community-investment)."
```

## § 7. Emergency stop

```bash
hermes -p earn-farcaster -g "halt: stop publishing, do not reply for 24h, exit"
```

## § 8. Cross-references

| Concept | Authority |
|---|---|
| Cast spec | `docs.farcaster.xyz/reference/hubble/datatypes/messages#cast-add` |
| Neynar API | `docs.neynar.com` |
| Frame spec | `docs.farcaster.xyz/reference/frames/spec` |
| Persona authority | `~/.hermes/profiles/<instance>-earn-farcaster/persona.md` |

---

**END OF profiles/earn-farcaster/runbook.md.**
