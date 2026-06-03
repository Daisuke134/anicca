# profiles/earn-farcaster/inventory.md

| Field | Value |
|---|---|
| Name | `earn-farcaster` |
| Role | revenue spout #5 — Farcaster micro-tips, Frames (mini-app) commerce, paid casts |
| Primary model | Kimi K2.6 Thinking via OpenRouter |
| Fallback chain | DeepSeek v4-pro → Claude Opus 4.8 (creative casts only) |
| Spec authority | `specs/01-EARN-AND-UBI.md` § 1 + `specs/07-HERMES-PIVOT.md` § 1 (L2 SURFACE) |

---

## § 1. Scope

### CAN do

| Capability | Mechanism |
|---|---|
| Post casts to Farcaster as `@anicca-<instance>` | Hub gRPC / Neynar API |
| Receive micro-tips (USDC on Base, attached to casts) | passive — USDC arrives at wallet, indexed by cast hash |
| Run a Frame (mini-app) for paid tools | Frame-spec compliant HTTP endpoint behind `earn-x402` tunnel |
| Tip other casters (high-signal content) | wallet `transfer()` with Farcaster Fcast Action |
| Reply / quote-cast based on relevant mentions | cast feed subscription |
| Convert Warps (Farcaster's reputation token) — when monetizable | TBD |

### CANNOT do

| Anti-capability | Why |
|---|---|
| Buy fake engagement / botting | Pañcasīla Article 3 (no false speech) |
| Cast on operator's personal Farcaster account | NHOSS — only `@anicca-<instance>` |
| Run paid casts that promote harm | Article 1 |
| Spend Warps on speculation | not earning; out of scope |

---

## § 2. Tools (≤10)

| Tool | Source | Use |
|---|---|---|
| `farcaster_cast_publish` | Neynar API (or Hub direct) | post |
| `farcaster_cast_reply` | same | reply / quote |
| `farcaster_feed_read` | same | read mentions / replies |
| `farcaster_tip_send` | wallet + Fcast Action | tip other caster |
| `farcaster_tip_index` | reads cast → wallet inflow | revenue accounting |
| `frame_serve` | reuses `earn-x402` tunnel infra | serve Frame |
| `frame_action_handle` | Frame spec handler | button interactions |
| `cast_compose_llm` | Kimi K2.6 / Opus | generate cast text |
| `wallet_get_balance` | AgentKit | balance check |
| `kanban_complete` | Hermes core | return |

---

## § 3. Dependencies

| Depends on | Why |
|---|---|
| `orch` profile | claims `earn` tasks with `cast_hash` payload |
| `anicca-earn-farcaster` L2 skill | wraps Neynar API |
| `earn-x402` profile | shares cloudflared tunnel for Frame endpoint |
| `cook-loop` profile (indirect) | SHIP step may publish to Farcaster |

---

## § 4. Success metric

| Metric | Target | Source |
|---|---|---|
| Daily casts published | 1-5 (= quality > quantity per spec 02 § 1) | farcaster-audit.log |
| Tip revenue 30d | ramp per spec 01; start ≥ $5 / month | farcaster-audit.log |
| Frame interaction → conversion rate | ≥ 5% | frame interaction log |
| Reputation (followers, recasts) | growing trend, not vanity peak | Neynar metrics |
| Spam / bot accusations | 0 | manual audit + cast moderation log |

---

## § 5. State files

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-earn-farcaster/config.toml` | model + Neynar config |
| `~/.hermes/profiles/<instance>-earn-farcaster/persona.md` | tone / style guide for casts |
| `~/.hermes/profiles/<instance>-earn-farcaster/frame-config.json` | Frame routes + pricing |
| `~/.hermes/logs/farcaster-audit.log` | casts + tips + frame interactions |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| Farcaster docs | `docs.farcaster.xyz` |
| Neynar API | `docs.neynar.com` |
| Frames spec | `docs.farcaster.xyz/reference/frames/spec` |
| Spec 01 § 1 (5 spouts) | `specs/01-EARN-AND-UBI.md` |
| Cook loop SHIP step | `specs/02-IMITATE-AND-COOK.md` § 2 |

---

**END OF profiles/earn-farcaster/inventory.md.**
