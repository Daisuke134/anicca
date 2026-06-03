# shared/commands.md — common ops across the fleet

> Quick-reference for operators. All commands assume `hermes` CLI in PATH
> and `BWS_ACCESS_TOKEN` loaded from `~/.openclaw/.env`.

## § 1. Daemon health

```bash
hermes status                              # daemon up?
hermes status --json | jq '.last_heartbeat_at'   # epoch seconds; should be < 60s ago
hermes profile list                        # 10 profiles registered?
tail -F ~/.hermes/logs/daemon.log          # live log stream
tail -F ~/.hermes/logs/daemon.err          # error stream
```

## § 2. Send a goal to a specific profile

```bash
hermes -p <profile-name> -g "<goal text>"
```

Examples:

| Goal | Command |
|---|---|
| trigger heartbeat manually | `hermes -p orch -g "run heartbeat tick now"` |
| force cook-loop iteration | `hermes -p cook-loop -g "run DISCOVER step once"` |
| fix a broken skill | `hermes -p fixer -g "fix anicca-wallet-x402: see ~/.hermes/logs/daemon.err"` |
| verify Constitution hash | `hermes -p constitution -g "verify CONSTITUTION.sha256 matches"` |
| check wallet balance | `hermes -p earn-x402 -g "report current wallet balance + last 24h USDC inflow"` |

## § 3. Kanban inspection

```bash
KDB=~/.hermes/kanban.db

sqlite3 $KDB "SELECT id, profile, status, claimed_at FROM tasks WHERE status='claimed';"
sqlite3 $KDB "SELECT id, profile, status FROM tasks WHERE status='ready' ORDER BY created_at LIMIT 20;"
sqlite3 $KDB "SELECT COUNT(*) FROM tasks WHERE status='failed' AND created_at > strftime('%s', 'now', '-24 hours');"

# release a stuck task (TTL didn't expire, lease zombie)
sqlite3 $KDB "UPDATE tasks SET status='ready', owner=NULL, claimed_at=NULL WHERE id=<task-id>;"
```

## § 4. Bitwarden vault

```bash
bws secret list                            # list all secrets (names only, no values)
bws secret get <id>                        # get one secret value (audit-logged)
bws secret create <KEY> "<value>"          # add new
bws secret edit <id> --value "<new value>" # rotate in place
bws secret delete <id>                     # delete (irreversible)
```

After rotating any secret, restart all profiles:

```bash
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes
hermes status                              # verify alive again
```

## § 5. Wallet operations

```bash
# read balance (no auth needed, just an RPC)
PROFILE=anicca-genesis
ADDR=$(jq -r .address ~/.hermes/profiles/${PROFILE}-orch/wallet.json)
echo "wallet: $ADDR"

# basescan check
open "https://basescan.org/address/$ADDR"

# read USDC balance via viem
node -e "
const { createPublicClient, http, parseAbi, formatUnits } = require('viem');
const { base } = require('viem/chains');
const client = createPublicClient({ chain: base, transport: http() });
const abi = parseAbi(['function balanceOf(address) view returns (uint256)']);
(async () => {
  const bal = await client.readContract({
    address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    abi, functionName: 'balanceOf', args: ['$ADDR'],
  });
  console.log('USDC:', formatUnits(bal, 6));
})();
"
```

## § 6. Constitution hash verify

```bash
EXPECTED=$(cat ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256)
ACTUAL=$(shasum -a 256 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md | awk '{print $1}')
[ "$EXPECTED" = "$ACTUAL" ] && echo "OK" || echo "MISMATCH — HALT INSTANCE"
```

## § 7. Spawn / kill colony member

```bash
# spawn (requires wallet > $20 + colony size < target)
hermes -p orch -g "spawn anicca001 via anicca-spawn-controller, verify Constitution hash, confirm wallet derived"

# kill (parent only kills direct children; grandparent veto required)
hermes -p orch -g "kill anicca001: <reason>. Persist post-mortem to colony-audit.log."
```

## § 8. x402 endpoint check

```bash
ENDPOINT=https://<cloudflared-tunnel>/research
curl -i $ENDPOINT                                  # expect HTTP 402 + invoice JSON
curl -i -H "X-Payment: <eip3009-sig>" $ENDPOINT   # expect HTTP 200 + research payload
```

## § 9. Logs (per profile)

```bash
ls ~/.hermes/logs/
# daemon.log              — main loop
# daemon.err              — main loop errors
# vault-audit.log         — bws secret get calls
# wallet-audit.log        — signing operations
# constitution-audit.log  — hash checks (forever)
# colony-audit.log        — spawn / kill events
# x402-audit.log          — invoices issued
# ubi-audit.log           — payouts sent (forever)
```

## § 10. Emergency stop (whole instance)

```bash
# graceful: queues drain, in-flight goals complete
hermes -p orch -g "halt: drain Kanban, complete in-flight goals, emit halt receipt, exit clean"

# hard stop (last resort)
launchctl unload ~/Library/LaunchAgents/ai.anicca.hermes.plist
```

## § 11. Restart whole instance

```bash
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes
sleep 5
hermes status                              # verify last_heartbeat fresh
hermes profile list                        # verify 10 profiles
```

## § 12. Per-profile runbook pointers

| Profile | Runbook |
|---|---|
| orch | `profiles/orch/runbook.md` |
| earn-x402 | `profiles/earn-x402/runbook.md` |
| earn-autohedge | `profiles/earn-autohedge/runbook.md` |
| earn-bounty | `profiles/earn-bounty/runbook.md` |
| earn-bittensor | `profiles/earn-bittensor/runbook.md` |
| earn-farcaster | `profiles/earn-farcaster/runbook.md` |
| cook-loop | `profiles/cook-loop/runbook.md` |
| ubi | `profiles/ubi/runbook.md` |
| fixer | `profiles/fixer/runbook.md` |
| constitution | `profiles/constitution/runbook.md` |

---

**END OF shared/commands.md.**
