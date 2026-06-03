# profiles/cook-loop/inventory.md

| Field | Value |
|---|---|
| Name | `cook-loop` |
| Role | imitation pipeline — DISCOVER → SCORE → PICK → PORT → SHIP → MEASURE → ADJUST |
| Primary model | Claude Opus 4.8 via OpenRouter (= creative PORT step); Kimi K2.6 for DISCOVER/SCORE/MEASURE |
| Fallback chain | Kimi K2.6 → DeepSeek v4-pro |
| Spec authority | `specs/02-IMITATE-AND-COOK.md` § 2 (verbatim) |

---

## § 1. Scope

### CAN do

| Capability | Mechanism |
|---|---|
| DISCOVER: scan imitation-targets.jsonl + scan candidate sources (Algora repos, X, Farcaster, etc.) | L2 `anicca-imitation-targets` |
| SCORE: rate a candidate against imitation criteria (working, popular, MIT-compatible) | LLM call with rubric |
| PICK: select top-N candidates to PORT this cycle | scored list → top-N |
| PORT: clone, adapt to Anicca's stack, integrate as L2 skill | Claude Opus 4.8 codegen + `anicca-verify` skill |
| SHIP: deploy the ported skill into runtime (= `hermes skill install`) | L2 skill install pipeline |
| MEASURE: track usage + revenue contribution of the new skill | reads relevant audit log |
| ADJUST: feedback loop — successful ports raise that target type's score | updates `~/.hermes/cook-priors.json` |

### CANNOT do

| Anti-capability | Why |
|---|---|
| Invent novel skills with no source pattern | spec 02 § 1.1 — imitation-first, not invention |
| Modify CONSTITUTION.md | immutable |
| Ship a skill without `anicca-verify` 5-step gate | spec 02 § 1.2 + HARD RULE #0.12 |
| Touch wallet | belongs to earn / ubi profiles |

---

## § 2. Tools (≤10)

| Tool | Source | Use |
|---|---|---|
| `targets_read` | L2 `anicca-imitation-targets` | DISCOVER |
| `targets_append` | L2 `anicca-imitation-targets` | add new target |
| `target_clone` | shell `git clone` | PORT |
| `target_score` | LLM call with rubric | SCORE |
| `skill_create` | Hermes core `_create_skill()` | PORT output |
| `skill_install` | `hermes skill install` | SHIP |
| `verify_5step` | L2 `anicca-verify` | quality gate (HARD RULE #0.12) |
| `cook_priors_update` | reads/writes `~/.hermes/cook-priors.json` | ADJUST |
| `usage_metric_read` | reads all audit logs to compute "did the new skill earn?" | MEASURE |
| `kanban_complete` | Hermes core | return result |

---

## § 3. Dependencies

| Depends on | Why |
|---|---|
| `orch` profile | claims `cook` category tasks |
| `anicca-imitation-targets` L2 | targets.jsonl management |
| `anicca-verify` L2 | quality gate |
| `fixer` profile | if a ported skill misbehaves in MEASURE, fixer claims the heal task |
| `earn-x402` / others (indirect) | new skills often add revenue → MEASURE depends on their audit logs |

---

## § 4. Success metric

| Metric | Target | Source |
|---|---|---|
| New skills shipped 30d | ≥ 2 (= imitation-first compounding) | cook-audit.log |
| Ported skill earns revenue within 30d | ≥ 50% of shipped skills | cross-reference with earn-* audit logs |
| `anicca-verify` 5-step gate pass rate | 100% (= zero false-ships) | cook-audit.log |
| imitation-targets.jsonl growth | ≥ 5 new entries / week | targets file diff |
| Operator-perceived skill quality | manual weekly spot-check | operator notes |

---

## § 5. State files

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-cook-loop/config.toml` | model + cycle config |
| `~/.hermes/imitation-targets.jsonl` | append-only registry of candidates (per spec 02 § 1.3) |
| `~/.hermes/cook-priors.json` | scores per target-type (= ADJUST output) |
| `~/.hermes/skills/learned/<topic>-<date>.md` | after-action skills (also written by `orch`'s judge model) |
| `~/.hermes/logs/cook-audit.log` | DISCOVER / PORT / SHIP events |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| Cook loop spec (verbatim) | `specs/02-IMITATE-AND-COOK.md` § 2 |
| Imitation instinct | `specs/02-IMITATE-AND-COOK.md` § 1.1 |
| Anti-pattern (do not invent) | `specs/02-IMITATE-AND-COOK.md` § 4 |
| Verify 5-step gate | `~/anicca-project/.claude/rules/verification.md` |
| Skill self-edit machinery | `specs/07-HERMES-PIVOT.md` § 2.4 |

---

**END OF profiles/cook-loop/inventory.md.**
