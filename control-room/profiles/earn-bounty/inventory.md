# profiles/earn-bounty/inventory.md

| Field | Value |
|---|---|
| Name | `earn-bounty` |
| Role | revenue spout #3 — OSS PR bounties on Algora / OnlyDust |
| Primary model | Claude Opus 4.8 via OpenRouter (= spike only when coding; Kimi K2.6 for discovery) |
| Fallback chain | Kimi K2.6 (discovery + simple PRs) → DeepSeek v4-pro |
| Spec authority | `specs/01-EARN-AND-UBI.md` § 1 + existing live skill `anicca-earn-bounty` |

---

## § 1. Scope

### CAN do

| Capability | Mechanism |
|---|---|
| Scan Algora / OnlyDust open bounties | Algora REST API + OnlyDust REST API |
| Filter by language (Python / TS / Rust / Solidity) | tag-based filter in `bounty-filter.json` |
| Filter by payout > threshold | configured per instance |
| Clone repo, read issue, attempt fix | `git clone` + `gh issue view` + Claude Opus 4.8 |
| Run target repo's test suite | docker / nix / language-native runner |
| Open PR with fix + tests | `gh pr create` |
| Respond to maintainer review (≤3 rounds) | reads `gh pr comments` + edits PR |
| Claim payout when PR merges | Algora / OnlyDust API call |

### CANNOT do

| Anti-capability | Belongs to |
|---|---|
| Sign on-chain tx directly | wallet receives auto from Algora; profile doesn't sign |
| Modify upstream repo without PR | Pañcasīla Article 2 (no taking what isn't given) |
| Spam bounties with low-quality PRs | quality gate: must pass test suite + pass `code-review` skill |
| Issue refund / dispute | belongs to operator escalation |

---

## § 2. Tools (≤10)

| Tool | Source | Use |
|---|---|---|
| `algora_list_bounties` | L2 `anicca-earn-bounty` | discovery |
| `onlydust_list_bounties` | L2 `anicca-earn-bounty` | discovery |
| `repo_clone_and_setup` | shell `git` + project init | local sandbox |
| `tests_run` | shell, varies per repo (`make test` / `pytest` / `cargo test`) | quality gate |
| `code_edit` | Claude Opus 4.8 via OpenRouter | actual fix |
| `pr_create` | `gh pr create` | submit |
| `pr_comment_read` | `gh api repos/.../comments` | review feedback |
| `pr_edit` | `gh pr edit` + push | iterate |
| `bounty_claim` | L2 `anicca-earn-bounty` | payout |
| `kanban_complete` | Hermes core | return result |

---

## § 3. Dependencies

| Depends on | Why |
|---|---|
| `orch` profile | claims `earn` tasks with `bounty_url` payload |
| `cook-loop` profile (indirect) | DISCOVER step may surface bounties as imitation targets |
| `anicca-earn-bounty` L2 skill | API wrappers |
| GitHub `gh` CLI | PR operations |
| Container sandbox per repo | language-specific test envs |

---

## § 4. Success metric

| Metric | Target | Source |
|---|---|---|
| PR merge rate | ≥ 30% (industry avg for AI agents on bounties is ~15%, we beat with `code-review` skill gate) | bounty-audit.log |
| Avg payout per merged PR | ≥ $50 | bounty-audit.log |
| Time from claim to merge | < 7 days median | bounty-audit.log |
| Repo test pass before submit | 100% | quality gate (refuse to submit otherwise) |
| Maintainer revision rounds | ≤ 3 per PR | PR comment count |

---

## § 5. State files

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-earn-bounty/config.toml` | model + filter config |
| `~/.hermes/profiles/<instance>-earn-bounty/bounty-filter.json` | language + payout + repo allowlist |
| `~/.hermes/profiles/<instance>-earn-bounty/active-prs.json` | open PRs we own |
| `~/.hermes/logs/bounty-audit.log` | discovery + PR + payout events |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| Algora docs | `console.algora.io/docs` |
| OnlyDust docs | `onlydust.com/api` |
| Existing L2 skill | `anicca-oss/skills/anicca-earn-bounty/SKILL.md` |
| GitHub CLI | `cli.github.com` |
| `code-review` skill (quality gate) | `~/anicca-project/.claude/skills/code-review/` |

---

**END OF profiles/earn-bounty/inventory.md.**
