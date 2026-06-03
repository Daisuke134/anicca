# profiles/constitution/docker.md

Shares `hermes-runtime:latest`. See `profiles/orch/docker.md`.

## § 1. Profile-specific notes

| Item | Detail |
|---|---|
| Negligible local CPU/RAM | hash check is microseconds; LLM rarely invoked |
| Critical-path priority | runs at the **start** of every heartbeat, before any other profile claims work |
| Read-only on disk (almost) | only writes are to `constitution-audit.log` and emergency flag file |

## § 2. Mounted volumes

| Mount path | Purpose | Permissions |
|---|---|---|
| `/root/.hermes/profiles/<instance>-constitution/` | config | rw |
| `/root/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md` | the text | **read-only** (= chattr +i if FS supports) |
| `/root/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256` | recorded hash | **read-only** |
| `/root/.hermes/logs/constitution-audit.log` | forever | append-only |
| `/root/.hermes/EMERGENCY_CONSTITUTION_MISMATCH` | flag file | rw (when needed) |

The `chattr +i` (immutable bit) prevents even root from accidentally
overwriting CONSTITUTION.md. To intentionally update (= a real Constitution
amendment), operator must `chattr -i`, edit, recompute hash, `chattr +i`,
restart Hermes — this friction is intentional.

## § 3. Network

| Direction | Allowed |
|---|---|
| Egress to OpenRouter | yes (rare; only when LLM consulted for governance edge case) |
| Inbound | none |

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Shared sandbox | `profiles/orch/docker.md` |
| Constitution-guard L2 | `anicca-oss/skills/anicca-constitution-guard/SKILL.md` |
| chattr +i pattern | OS-level immutability flag |

---

**END OF profiles/constitution/docker.md.**
