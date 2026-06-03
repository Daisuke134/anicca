# profiles/cook-loop/docker.md

Shares `hermes-runtime:latest`. See `profiles/orch/docker.md`.

## § 1. Profile-specific notes

| Item | Detail |
|---|---|
| Additional disk | up to 500 MB transient for cloned PORT candidates; aggressively cleaned (≤24h retention) |
| Additional RAM | LLM-call-bound; local memory negligible |
| Container-in-container | sometimes needed for testing ported skills in isolation; uses `anicca-spawn-controller` ephemeral pattern |

## § 2. Mounted volumes

| Mount path | Purpose |
|---|---|
| `/root/.hermes/profiles/<instance>-cook-loop/` | config |
| `/root/.hermes/imitation-targets.jsonl` | append-only registry |
| `/root/.hermes/cook-priors.json` | ADJUST output |
| `/root/.hermes/skills/learned/` | after-action skills |
| `/tmp/cook-workspaces/<target-id>/` | ephemeral PORT clone |
| `/root/.hermes/logs/cook-audit.log` | events |

## § 3. Network

| Direction | Allowed |
|---|---|
| Egress to candidate sources (`github.com`, `npmjs.org`, `pypi.org`, etc.) | yes |
| Egress to OpenRouter | yes |
| Egress to social signals (Farcaster, X via `earn-farcaster`) | indirect (via that profile) |
| Inbound | none |

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Shared sandbox | `profiles/orch/docker.md` |
| Ephemeral spawn pattern | `templates/new-instance.md` (= lifecycle: ephemeral variant) |
| Cook loop spec | `specs/02-IMITATE-AND-COOK.md` § 2 |

---

**END OF profiles/cook-loop/docker.md.**
