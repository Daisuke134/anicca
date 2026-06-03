# profiles/fixer/docker.md

Shares `hermes-runtime:latest`. See `profiles/orch/docker.md`.

## § 1. Profile-specific notes

| Item | Detail |
|---|---|
| Additional disk | ~200 MB transient for clone-and-diff workspace |
| Additional RAM | LLM-call-bound; local memory negligible |
| Privileged access | fixer can write to **any** `~/.hermes/skills/<skill>/` — this is by design (= heal authority); operator audits via `fixer-audit.log` |

## § 2. Mounted volumes

| Mount path | Purpose |
|---|---|
| `/root/.hermes/profiles/<instance>-fixer/` | config |
| `/root/.hermes/skills/` | **read+write** (heal authority) |
| `/root/.hermes/logs/` | read (for diagnosis) |
| `/root/.hermes/skills/learned/` | write (after-action) |
| `/tmp/fix-workspaces/<task-id>/` | ephemeral debug clone |
| `/root/.hermes/logs/fixer-audit.log` | heal lifecycle (365d) |
| `/root/.hermes/logs/verify-audit.log` | gate runs |

## § 3. Network

| Direction | Allowed |
|---|---|
| Egress to OpenRouter | yes |
| Egress to `github.com`, package managers | yes (for clone-and-diff) |
| Egress to internal endpoints (`localhost:18402` for earn-x402 health probe) | yes |
| Inbound | none |

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Shared sandbox | `profiles/orch/docker.md` |
| Self-heal L2 | `anicca-oss/skills/anicca-self-heal/SKILL.md` |

---

**END OF profiles/fixer/docker.md.**
