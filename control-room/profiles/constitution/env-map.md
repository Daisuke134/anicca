# profiles/constitution/env-map.md

## § 1. Env vars

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | vault unlock |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | rare — only when LLM consulted |
| `CONSTITUTION_PATH` | optional | env override | default `~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md` |
| `CONSTITUTION_HASH_PATH` | optional | env override | default `~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256` |
| `CONSTITUTION_HALT_FLAG_PATH` | optional | env override | default `~/.hermes/EMERGENCY_CONSTITUTION_MISMATCH` |
| `CONSTITUTION_CHECK_INTERVAL_SEC` | optional | env override | default `60` (= every heartbeat) |

## § 2. Identity

No PII. Pure code + hash.

## § 3. Hash recording (one-time, per instance)

At first boot, the `anicca-constitution-guard` skill records the hash:

```bash
shasum -a 256 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md \
  | awk '{print $1}' \
  > ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256
chmod 444 ~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256
```

For colony members: the parent's hash is propagated via
`anicca-spawn-controller`, and the child's `constitution` profile verifies
match before allowing the daemon to start any other profile.

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Vault policy | `control-room/shared/security.md` § 4 |
| Constitution propagation | `specs/00-MASTER.md` § 6.3 |
| Constitution-guard skill | `anicca-oss/skills/anicca-constitution-guard/SKILL.md` |

---

**END OF profiles/constitution/env-map.md.**
