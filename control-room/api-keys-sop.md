# api-keys-sop.md — Standard Operating Procedure for API key rotation

> Read `shared/security.md` first for the never-commit list and risk model.
> This SOP covers the operational mechanics of rotating, revoking, and
> adding API keys across the fleet.

## § 1. When to rotate

| Trigger | Action |
|---|---|
| Scheduled cadence (`shared/security.md` § 3) | rotate all due keys this week |
| Suspected leak (e.g., key seen in a log paste) | rotate the leaked key within 1 hour |
| New colony member onboarding | rotate the `BWS_ACCESS_TOKEN` scope token, not the full key |
| Vendor compromise notice (e.g., Coinbase security advisory) | rotate matching key class within 4 hours |
| Operator device change (e.g., new laptop) | rotate `BWS_ACCESS_TOKEN` bootstrap |
| Sandbox compromise (e.g., RCE in a Daytona instance) | rotate that sandbox's scoped vault token, NOT the parent's bootstrap |

## § 2. Rotation runbook (any non-bootstrap secret)

```
                                                                              
   ┌──────────────────────────────────────────────────────────────────────┐  
   │   ROTATION FLOW (anything in Bitwarden vault)                         │  
   │                                                                       │  
   │   1. operator: visit vendor dashboard (e.g., cdp.coinbase.com)        │  
   │      → create NEW key with same scope as OLD key                      │  
   │      → save NEW value to clipboard                                    │  
   │                                                                       │  
   │   2. operator: `bws secret edit <id> --value "<NEW value>"`           │  
   │      → vault now has new value                                        │  
   │      → audit log entry written                                        │  
   │                                                                       │  
   │   3. operator: `launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes` │  
   │      → daemon restarts, re-reads vault                                │  
   │      → all 10 profiles in this instance get new value at next tick    │  
   │                                                                       │  
   │   4. operator (for colony): for each child sandbox, ssh/exec:         │  
   │      `hermes -p orch -g "reload vault, restart all profiles"`         │  
   │      OR sandboxes pick up new value at next 60s heartbeat tick        │  
   │      (vault polling — see § 7)                                        │  
   │                                                                       │  
   │   5. operator: `hermes status` on each instance — verify alive        │  
   │                                                                       │  
   │   6. operator: visit vendor dashboard → REVOKE OLD key                │  
   │      → grep ~/.hermes/logs/*.log for any process still using OLD      │  
   │      → if any, repeat step 3 until clean                              │  
   │                                                                       │  
   │   7. operator: paste vendor audit log line confirming OLD revoked     │  
   │      → into ~/.hermes/logs/rotation-audit.log                         │  
   └──────────────────────────────────────────────────────────────────────┘  
                                                                              
```

## § 3. Rotation runbook (`BWS_ACCESS_TOKEN` bootstrap)

The bootstrap token has a different procedure because it lives in
`~/.openclaw/.env`, not in the vault itself.

```bash
# 1. revoke OLD in Bitwarden web UI (Account Settings → Access Tokens)
# 2. create NEW with same project scope (anicca-oss-public, read)
# 3. update ~/.openclaw/.env:
#    sed -i '' 's|^BWS_ACCESS_TOKEN=.*|BWS_ACCESS_TOKEN=<NEW>|' ~/.openclaw/.env
# 4. verify file perms
ls -l ~/.openclaw/.env  # expect: -rw------- (chmod 600)
# 5. restart Hermes
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes
sleep 5
# 6. verify daemon can read vault
hermes -p orch -g "bws secret list >> /tmp/vault-check.log"
cat /tmp/vault-check.log  # should list secret names, not error
```

## § 4. Revoke runbook (suspected leak, no replacement)

If you suspect a leak and want to revoke immediately without rotating:

```bash
# 1. revoke OLD in vendor dashboard (no NEW created)
# 2. Hermes will start failing on next call → daemon logs ERROR
# 3. operator decides: provision NEW key (= § 2 flow) OR accept the spout going dark
# 4. log decision to ~/.hermes/logs/rotation-audit.log
```

## § 5. Adding a new API key (e.g., a new earn spout)

```bash
# 1. obtain key from vendor (e.g., Algora API token for earn-bounty)
# 2. add to vault:
bws secret create ALGORA_API_TOKEN "<value>"
# 3. update the relevant profile's env-map.md:
#    profiles/earn-bounty/env-map.md → add ALGORA_API_TOKEN to the table
# 4. update the relevant L2 skill (anicca-earn-bounty) to read the env var
# 5. restart Hermes:
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes
# 6. verify:
hermes -p earn-bounty -g "test Algora API auth, report result"
```

## § 6. Adding a key for a NEW colony member

When `anicca-spawn-controller` provisions a new Daytona sandbox, it does NOT
copy the parent's `BWS_ACCESS_TOKEN`. Instead:

```
parent (anicca-genesis):
  └─ creates new Bitwarden scoped access token (scope = anicca-oss-public, read)
  └─ injects scoped token into Daytona sandbox env: BWS_ACCESS_TOKEN=<scoped>
  └─ scoped token has the same vault read access but is independently revocable

child (anicca001):
  └─ on boot, hermes daemon reads BWS_ACCESS_TOKEN from env
  └─ calls `bws secret list` to fetch CDP / OpenRouter / etc.
  └─ runs CDP `createSmartAccount()` to derive its own wallet
  └─ writes wallet.json to ~/.hermes/profiles/anicca001-orch/wallet.json
```

If `anicca001` is compromised:

```bash
# parent revokes ONLY anicca001's scoped token in Bitwarden web UI
# anicca-genesis + anicca002 + ... unaffected
# anicca001 sandbox is killed via `hermes -p orch -g "kill anicca001"`
```

## § 7. Vault polling (60s heartbeat tick)

Hermes re-reads the vault every 60s during the heartbeat. So in most cases,
restarting the daemon is **not required** after a rotation — the next tick
will pick up the new value. Restart is required only if:

- The key is read at daemon startup (e.g., model config in `config.toml`)
- The current in-flight goal is using the OLD key and you need to abort it

## § 8. Logging

Every rotation event MUST be logged:

```bash
echo "$(date -Iseconds) rotated CDP_API_KEY_ID, reason: scheduled 90d, revoked OLD via dashboard" \
  >> ~/.hermes/logs/rotation-audit.log
```

Retention: forever (this is the audit trail for "did we rotate when we said
we would?").

## § 9. Emergency: vault provider compromise (Bitwarden itself breached)

If Bitwarden Secrets Manager itself is compromised:

1. operator marks emergency: `touch ~/.hermes/EMERGENCY_VAULT_COMPROMISED`
2. Hermes refuses to read vault on next tick (file present = halt)
3. operator rotates ALL keys at vendor dashboards (CDP / OpenRouter / Daytona / Algora / X / Telegram / etc.)
4. operator sets up replacement vault (Doppler / HashiCorp Vault / SOPS / age-encrypted file)
5. operator updates `~/.openclaw/.env` with new vault provider's bootstrap token
6. operator updates `shared/security.md` § 4 with new provider
7. operator removes emergency file: `rm ~/.hermes/EMERGENCY_VAULT_COMPROMISED`
8. `launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes`

## § 10. Cross-references

| Concept | Authority |
|---|---|
| Never-commit list | `shared/security.md` § 1 |
| Bitwarden vault details | `shared/security.md` § 4 |
| Bootstrap token | `shared/security.md` § 5 |
| Audit log paths | `shared/security.md` § 8 |
| Daytona sandbox secret loading | `shared/security.md` § 7 |
| Spawn controller skill | `anicca-oss/skills/anicca-spawn-controller/SKILL.md` |

---

**END OF api-keys-sop.md.**
