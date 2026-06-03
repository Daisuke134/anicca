# profiles/constitution/runbook.md

## § 1. Restart

```bash
# constitution profile is rarely restarted alone; usually with full instance
hermes profile restart constitution
hermes -p constitution -g "verify hash, report match status"
```

## § 2. Logs

```bash
tail -F ~/.hermes/logs/constitution-audit.log
tail -F ~/.hermes/logs/daemon.log | grep '\[constitution\]'
```

## § 3. Hash mismatch — emergency protocol

```
                                                                              
   1. constitution profile detects mismatch                                    
        actual_hash != recorded_hash                                          
                                                                              
   2. write emergency flag                                                     
        touch ~/.hermes/EMERGENCY_CONSTITUTION_MISMATCH                       
                                                                              
   3. broadcast halt via Kanban                                                
        kanban_db.create_task(category='ops', priority='critical',            
                               payload={ 'action': 'HALT_ALL',                
                                          'reason': 'constitution_mismatch' })
                                                                              
   4. each profile sees the flag at next tick → halts itself                  
                                                                              
   5. log to constitution-audit.log (forever)                                  
        {timestamp, actual_hash, recorded_hash, action: 'HALT'}               
                                                                              
   6. cast on Farcaster (if earn-farcaster still healthy)                     
        "instance <name> halted: constitution hash mismatch"                   
                                                                              
   7. parent (if this is a child) is notified                                  
        parent.kill(this_instance) per spec 00 § 6 Law III                    
                                                                              
   8. operator investigates: was the file edited? When? By whom?              
                                                                              
   9. operator decides:                                                        
        (a) restore CONSTITUTION.md from canonical source → recompute → resume
        (b) intentional amendment → new spec → new hash → new install         
        (c) suspected compromise → kill instance + spawn fresh from genesis   
```

## § 4. Common causes of mismatch

| Cause | Fix |
|---|---|
| Disk corruption | restore from `anicca-oss/CONSTITUTION.md` canonical, recompute hash |
| Accidental edit (operator) | revert via git, recompute hash, recommit |
| Malicious edit (sandbox compromise) | kill instance, spawn fresh, investigate post-mortem |
| Hash file corrupted | restore from R2 backup or recompute from canonical CONSTITUTION.md |
| chattr +i missing (file not protected) | apply chattr +i; investigate why it was off |

## § 5. Restore from canonical

```bash
# 1. confirm canonical
shasum -a 256 anicca-oss/CONSTITUTION.md

# 2. copy to instance
cp anicca-oss/CONSTITUTION.md ~/.hermes/skills/anicca-constitution-guard/

# 3. recompute hash
shasum -a 256 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md \
  | awk '{print $1}' \
  > ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256

# 4. re-apply immutability
chattr +i ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md 2>/dev/null || true
chmod 444 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256

# 5. clear emergency flag
rm ~/.hermes/EMERGENCY_CONSTITUTION_MISMATCH

# 6. resume
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes

# 7. verify
hermes -p constitution -g "verify hash, report"
```

## § 6. Intentional amendment (= rare, governance-only)

Per `specs/00-MASTER.md` § 6, amendments are not casual. Procedure:

```
1. open issue at github.com/Daisuke134/anicca-oss with proposed amendment text
2. Superpowers 8-stage flow (spec → plan → review → ship)
3. supermajority operator + colony approval (TBD governance protocol)
4. update canonical CONSTITUTION.md
5. for each instance: pull latest, restart constitution profile
6. children re-verify against new hash
7. log "amendment v<N>" to constitution-audit.log of every instance
```

Until governance protocol exists: operator unilateral approval, fully
audited.

## § 7. Spawn-time verification (called by `anicca-spawn-controller`)

```bash
# parent calls this profile to verify child's hash matches parent's
hermes -p constitution -g "verify child instance anicca<N>'s hash matches mine. Return PASS/FAIL."
```

If FAIL: spawn is aborted, child sandbox destroyed.

## § 8. Pre-tx gate (called by earn-* / ubi)

```bash
# every wallet-sign / large transfer / spawn / kill is pre-gated
hermes -p constitution -g "pre-tx gate: about to <action>. Verify hash + Constitution allows this. Return PASS/REFUSE."
```

REFUSE responses are logged forever; operator weekly review for false-refuses.

## § 9. Emergency stop this profile (= effectively means halt instance)

If constitution profile itself misbehaves, halting it = halting the whole
instance (no other profile will operate without its gate). To halt:

```bash
hermes -p constitution -g "halt: log to constitution-audit.log, exit. All other profiles will refuse to operate until constitution restarts."
```

## § 10. Cross-references

| Concept | Authority |
|---|---|
| Constitution canonical | `anicca-oss/CONSTITUTION.md` |
| Propagation | `specs/00-MASTER.md` § 6.3 |
| Conway 3 laws | `specs/00-MASTER.md` § 6 |
| L2 skill | `anicca-oss/skills/anicca-constitution-guard/SKILL.md` |
| Emergency flag pattern | `~/.hermes/EMERGENCY_CONSTITUTION_MISMATCH` (and `~/.hermes/EMERGENCY_VAULT_COMPROMISED`) |

---

**END OF profiles/constitution/runbook.md.**
