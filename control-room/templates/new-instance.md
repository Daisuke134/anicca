# templates/new-instance.md — how to spawn a new colony member

> Provisioning a new Anicca instance = new Daytona sandbox + new CDP smart
> wallet + full 10-profile copy + Constitution hash verify + colony ledger
> registration. The `anicca-spawn-controller` L2 skill automates most of
> this; this template documents the manual override path for operators.

## § 1. Pre-conditions (the spawn gate)

| Gate | Check | If fails |
|---|---|---|
| Wallet > $20 (parent) | `node -e ".. read USDC balance .."` | wait, don't force spawn |
| Colony size < target | `cat ~/.hermes/colony.json | jq '.size'` vs target in `~/.hermes/config.toml` | upgrade target intentionally OR wait |
| Constitution hash recorded | `cat ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256` | re-record from canonical |
| Bitwarden vault healthy | `bws secret list | wc -l` ≥ 4 | fix vault first (see `api-keys-sop.md` § 9) |
| Daytona API token live | `daytona sandbox list` returns 0+ rows without auth error | rotate Daytona token |
| Operator approval (manual spawn only) | spawn-from-orch-goal does NOT need this | for `templates/new-instance.md` manual flow, yes |

## § 2. Automated path (`anicca-spawn-controller` skill)

```bash
# the spawn happens autonomously when gates pass; you can also trigger it:
hermes -p orch -g "spawn next colony member: anicca<N+1>. Verify Constitution hash, derive wallet, register in colony ledger, transfer $5 USDC seed."
```

The skill runs:

```
                                                                              
   1. Daytona sandbox provision                                                
        sandbox_id = daytona.sandboxes.create({                               
          name: 'anicca<N+1>',                                                 
          image: 'hermes-runtime:latest',                                      
          vcpu: 0.5, memoryMb: 512, diskGb: 5,                                 
        })                                                                     
                                                                              
   2. install Hermes + skills in sandbox                                       
        daytona.exec(sandbox_id, "curl -fsSL .../install.sh | bash")          
        daytona.copy(sandbox_id, "anicca-oss/skills/", "/root/.hermes/skills/")
                                                                              
   3. inject scoped BWS token                                                  
        scoped_token = bitwarden.access_tokens.create(scope='read', proj=...) 
        daytona.env_set(sandbox_id, "BWS_ACCESS_TOKEN", scoped_token)         
                                                                              
   4. derive new CDP smart wallet                                              
        daytona.exec(sandbox_id, "node /root/.hermes/skills/anicca-wallet-x402/bootstrap.js")
        # writes ~/.hermes/profiles/anicca<N+1>-orch/wallet.json                
                                                                              
   5. propagate Constitution                                                   
        daytona.copy(sandbox_id, "CONSTITUTION.md", "/root/.hermes/skills/anicca-constitution-guard/")
        daytona.copy(sandbox_id, "CONSTITUTION.sha256", "/root/.hermes/skills/anicca-constitution-guard/")
        # child's anicca-constitution-guard verifies hash on every tick        
                                                                              
   6. create 10 Hermes profiles in sandbox                                     
        for p in orch earn-x402 earn-autohedge earn-bounty earn-bittensor \   
                 earn-farcaster cook-loop ubi fixer constitution; do          
          daytona.exec(sandbox_id, "hermes profile create $p")                
          daytona.exec(sandbox_id, "cp control-room/profiles/$p/config.toml \\
                                       ~/.hermes/profiles/anicca<N+1>-$p/")  
        done                                                                  
                                                                              
   7. start Hermes daemon in sandbox                                           
        daytona.exec(sandbox_id, "hermes daemon --profile-prefix=anicca<N+1>")
                                                                              
   8. parent transfers $5 USDC seed to child wallet                            
        anicca-wallet-x402.transfer(child_addr, 5_000_000)  # 5 USDC, 6 dec   
                                                                              
   9. register in colony ledger                                                
        echo '{"name":"anicca<N+1>", "addr":"<addr>", "spawned_at":"<iso>",   
               "parent":"<parent_name>"}' >> ~/.hermes/colony.json            
                                                                              
   10. verify child's first heartbeat                                          
         daytona.exec(sandbox_id, "hermes status --json | jq .last_heartbeat_at")
         # should be within 60s of step 7                                      
```

## § 3. Manual override path (operator escape hatch)

If the automated path fails, the operator can provision manually:

```bash
# 1. provision Daytona sandbox
daytona sandbox create \
  --name anicca<N+1> \
  --image hermes-runtime:latest \
  --vcpu 0.5 --memory 512 --disk 5

# 2. exec into sandbox
daytona sandbox ssh anicca<N+1>

# inside sandbox:
# 3. install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 4. inject scoped BWS token (operator provides via paste, not from disk)
export BWS_ACCESS_TOKEN="<scoped token from Bitwarden web UI>"

# 5. bootstrap skills
git clone https://github.com/Daisuke134/anicca-oss.git /tmp/anicca-oss
cp -r /tmp/anicca-oss/skills/* ~/.hermes/skills/
cp /tmp/anicca-oss/CONSTITUTION.md ~/.hermes/skills/anicca-constitution-guard/
shasum -a 256 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md \
  | awk '{print $1}' > ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256

# 6. compare hash with parent's (operator does this manually)
echo "parent hash: <paste from parent>"
echo "child hash:  $(cat ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256)"
# must match exactly

# 7. derive wallet
node ~/.hermes/skills/anicca-wallet-x402/bootstrap.js

# 8. create 10 profiles
for p in orch earn-x402 earn-autohedge earn-bounty earn-bittensor \
         earn-farcaster cook-loop ubi fixer constitution; do
  hermes profile create $p
  cp /tmp/anicca-oss/control-room/profiles/$p/config.toml \
     ~/.hermes/profiles/$p/ 2>/dev/null || true
done

# 9. start daemon
hermes daemon &
hermes status

# 10. exit sandbox; operator registers in colony.json (back on parent host)
exit
echo '{"name":"anicca<N+1>", "addr":"<addr>", "spawned_at":"'$(date -Iseconds)'", "parent":"'$PARENT'"}' \
  >> ~/.hermes/colony.json

# 11. parent transfers seed manually
hermes -p earn-x402 -g "transfer 5 USDC to anicca<N+1> at <addr>, log to ubi-audit.log (label: seed)"
```

## § 4. Verification gate (HARD RULE #0.12)

```bash
# from parent host
hermes -p orch -g "verify child anicca<N+1>: hash match, wallet alive, 10 profiles, first heartbeat fresh"

# expect output:
#   constitution_hash:  MATCH
#   wallet_addr:        0x...
#   wallet_balance:     5.00 USDC (= seed received)
#   profiles_count:     10
#   last_heartbeat:     <60s ago
#   colony_ledger:      registered
```

If any line fails: see `profiles/fixer/runbook.md` § "spawn rollback."

## § 5. Naming convention

| Generation | Name |
|---|---|
| Day 0 boot | `anicca-genesis` |
| Day 7+ spawns | `anicca001`, `anicca002`, ..., `anicca999` |
| Special-purpose | `anicca-fixer-pool` (= dedicated heal-only instance, future) |
| Test instances | `anicca-test-<topic>` (= short-lived, manual cleanup) |

The colony ledger (`~/.hermes/colony.json`) tracks the canonical name list.
Never reuse a name even after kill; append-only.

## § 6. Rollback / kill procedure

```bash
# parent kills its own direct child (Law III)
hermes -p orch -g "kill anicca<N+1>: <reason>. Archive state to R2 bucket anicca-colony-archive."

# the skill runs:
# 1. graceful: hermes -p orch -g "halt: drain Kanban, exit clean" (inside sandbox)
# 2. snapshot: daytona snapshot create anicca<N+1> --r2-bucket=anicca-colony-archive
# 3. revoke: bitwarden access token revoke <child-scoped-token>
# 4. terminate: daytona sandbox destroy anicca<N+1>
# 5. ledger: append {"event":"kill", "name":"anicca<N+1>", ...} to colony.json
```

Grandparent veto: if a parent wants to kill a grandchild, requires the
grandparent's approval (spec 00 § 6 + spec 07 § 10 Q5). Implemented as a
Kanban task that grandparent must explicitly claim and approve.

## § 7. Cross-references

| Concept | Authority |
|---|---|
| Spawn gate (wallet > $20) | `specs/00-MASTER.md` § 7.3 + `specs/07-HERMES-PIVOT.md` § 6 Day 7 |
| Constitution propagation | `specs/00-MASTER.md` § 6.3 |
| Per-profile wallet inheritance | `specs/07-HERMES-PIVOT.md` § 3.4 |
| Daytona spawn details | `specs/07-HERMES-PIVOT.md` § 3.6 + `specs/05-SERVER-NATIVE-DEPLOY.md` MODE B |
| Spawn controller skill | `anicca-oss/skills/anicca-spawn-controller/SKILL.md` |
| Colony ledger schema | `specs/01-EARN-AND-UBI.md` § 3 |
| Kill / veto governance | `specs/00-MASTER.md` § 6 (Conway 3 laws) |

---

**END OF templates/new-instance.md.**
