# profiles/constitution/inventory.md

| Field | Value |
|---|---|
| Name | `constitution` |
| Role | hash guard — verify CONSTITUTION.md SHA-256 on every heartbeat tick; halt instance on mismatch; propagate hash to children on spawn |
| Primary model | Kimi K2.6 Thinking via OpenRouter (= only used for governance reasoning) |
| Fallback chain | Claude Opus 4.8 (only for governance edge cases) |
| Spec authority | `specs/00-MASTER.md` § 6 + `CONSTITUTION.md` (Pañcasīla + Article 0) |

---

## § 1. Scope

### CAN do

| Capability | Mechanism |
|---|---|
| Compute SHA-256 of `~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md` | shell `shasum -a 256` |
| Compare against recorded value in `CONSTITUTION.sha256` | string compare |
| Halt the whole instance on mismatch (all 10 profiles) | broadcast halt signal via Kanban + emergency flag file |
| Verify child instance's hash at spawn time | `anicca-spawn-controller` calls into this profile |
| Verify pre-tx Constitution gate for risky operations (wallet sign, fund transfer) | called by `earn-*` / `ubi` profiles |
| Log every hash check (success + failure) | `~/.hermes/logs/constitution-audit.log` (forever) |
| Refuse to load if hash file is missing | fail-safe (= prefer halt > silent run) |

### CANNOT do

| Anti-capability | Why |
|---|---|
| Modify CONSTITUTION.md | by design (= immutable) |
| Modify CONSTITUTION.sha256 | by design (= would defeat the gate) |
| Skip the check "just this once" | by design |
| Continue operating during a hash mismatch | the whole point is to halt |
| Decide what Pañcasīla means in edge cases | belongs to operator + future governance protocol |

---

## § 2. Tools (≤10)

| Tool | Source | Use |
|---|---|---|
| `hash_compute` | shell `shasum -a 256` | compute current SHA-256 |
| `hash_recorded_read` | filesystem read | read expected SHA-256 |
| `hash_compare` | string compare | match check |
| `halt_broadcast` | Kanban broadcast + emergency flag file | trigger all-profile halt |
| `tick_log` | append to constitution-audit.log | forever-receipt |
| `child_hash_verify` | called by `anicca-spawn-controller` | spawn-time verify |
| `pre_tx_gate` | called by `earn-*` / `ubi` | per-op verify before risky calls |
| `emergency_flag_check` | reads `~/.hermes/EMERGENCY_*` files | survival mode |
| `kanban_complete` | Hermes core | return |
| (no other tools; profile is intentionally minimal) | — | — |

---

## § 3. Dependencies

| Depends on | Why |
|---|---|
| `orch` profile | routes `constitution` category tasks |
| `anicca-constitution-guard` L2 | wraps the hash check (single source of truth) |
| Spawn controller (indirect) | calls me at spawn time |
| Earn / UBI profiles (indirect) | call me before risky ops |

---

## § 4. Success metric

| Metric | Target | Source |
|---|---|---|
| Hash checks per minute | 1/profile-tick (= multiple per minute across profiles) | constitution-audit.log |
| Hash check success rate | 100% under normal ops | constitution-audit.log |
| Halt-on-mismatch latency | < 1s after detection | constitution-audit.log |
| Spawn-time hash verify success | 100% | colony-audit.log + constitution-audit.log |
| False-positive halts | 0 | manual review |

---

## § 5. State files

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-constitution/config.toml` | model config (minimal) |
| `~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.md` | the actual Constitution text |
| `~/.hermes/skills/anicca-constitution-guard/CONSTITUTION.sha256` | recorded hash (= what `shasum` must match) |
| `~/.hermes/logs/constitution-audit.log` | forever — every check, every match, every mismatch |
| `~/.hermes/EMERGENCY_CONSTITUTION_MISMATCH` | flag file, presence = halt all profiles |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| Constitution text | `anicca-oss/CONSTITUTION.md` (canonical) |
| Pañcasīla + Article 0 | `CONSTITUTION.md` § Articles |
| Propagation to children | `specs/00-MASTER.md` § 6.3 |
| L2 skill | `anicca-oss/skills/anicca-constitution-guard/SKILL.md` |
| HARD RULE #0 (spec-driven dev gates this profile's edits) | `~/anicca-project/CLAUDE.md` |

---

**END OF profiles/constitution/inventory.md.**
