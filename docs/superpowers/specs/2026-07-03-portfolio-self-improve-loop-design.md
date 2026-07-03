# Portfolio Self-Improvement Loop — Design Spec (separate epic)

- **Date**: 2026-07-03
- **Status**: DESIGN — extracted from `life-manager-cost-connect-reliability` per adversary finding F3 (scope creep). This is its OWN epic; do not fold into the LM cost/connect/reliability feature.
- **Method**: to be run through its own VCSDD feature (`/vcsdd-init portfolio-self-improve-loop`) before implementation.

## Purpose
Apply ONE self-improvement loop to every product in `aniccaai.com/dais` + `anicca-project` (not just LM): read real metrics daily → fix the highest-leverage funnel bottleneck → verify by real side-effect → persist → repeat, with no human in the loop.

## Loop shape (Warp inner/outer + Reflexion/Self-Refine + Anthropic evaluator-optimizer)
- INNER (per task): apply a product/marketing skill → real side-effect → record a trace stamped `skill:<name> v:<N> run_id:<...>`.
- OUTER (daily `claude -p` Sonnet): observe traces + git since last bump → GRADE by metric delta attributed to the version window → synthesize ≤~12 GENERALIZABLE lessons → diff the skill + bump version → open a PR (never push main). Improvement = TEXT persisted in a versioned `SKILL.md` (Reflexion: verbal memory, not weights); repo = STATE (GLVS).

## 7 hard rules (or it degrades)
1 grounded external signal (grader = metric delta MRR/signup/conversion/cost, not self-opinion) · 2 generalizable-only lessons · 3 bounded guidelines (≤~12, consolidate/prune at cap) · 4 versioned skill + trace marker · 5 weak/conflicting signal = NO-OP (empty run = success) · 6 weighted evidence (MRR-drop/relabel strong > engagement moderate > silence weak-positive) · 7 PR gate + audit trail; no-human review = fresh-context vcsdd-adversary on the diff + regression guard (if previous bump's metric got WORSE → REVERT, don't stack).

## show-me-the-money = ADAPT (not use-as-is)
`~/.claude/plugins/cache/show-me-the-money/money/1.0.0/` (CC BY-NC OK). REUSE = `money-ops` 6-dim health-score bottleneck-picker, `~/.smtm/` state spine (`/money-save`,`/money-learn`,`/money-retro`,`/money-report`), `money-finance` business-type→metric router. REPLACE = wire real metric reads (deterministic tools write today's numbers to `~/.smtm/analytics/<slug>.jsonl` before the agent reasons — agent judges, tools fetch); swap human-confirm gates for adversary + browser E2E; AMPUTATE `money-social` X path.

## Funnel-lever priority at $0 MRR (AARRR, NOT acronym order)
0 Instrumentation → 1 Activation → 2 Retention (<5%/mo, NRR>100%) → 3 Revenue/Paywall (trial→paid>10%; reprice conv<5%=too dear / churn<2%+high-use=too cheap) → 4 Acquisition (compounding organic) → 5 Referral. One product × one lever × one action per day; pick the lowest BROKEN upstream stage.

## Marketing WITHOUT X (Dais bans X), effectiveness order
programmatic SEO + GEO (JSON-LD → cited by ChatGPT/Perplexity/Gemini) + directory submissions > paid ads > cold email (warmed domain, bounce<5%) > Product Hunt (episodic). No X.

## Metrics per product + source
Stripe (MRR/churn/subs/failed-pay) · RevenueCat MCP (`get-overview-metrics`,`get-revenue-metric`) · `asc` CLI (downloads/ASC conversion/proceeds, 3-day lag, weekly-smooth) · Supabase SQL (signups/activation/D7-D30) · GA4 (traffic/LP-conv). Derived: growth MoM, ARPU, CAC, LTV:CAC>3, payback<6mo.

## Daily loop (no human, no X)
[1] PULL metrics (deterministic) → [2] SCORE+PICK one product×one bottleneck → [3] SPEC the one action (VCSDD, right-altitude, agent decides) → [4] BUILD (SDD RED→GREEN, commit+push) → [5] VERIFY (① adversary disk-only ② my browser/on-chain E2E: curl 200 + Supabase event + Stripe/RC reflects; NO mock) → [6] PERSIST (money-save/learn + report row) → [7] GUARDRAILS (spend cap, new channel 10%→scale over 6d, canary 24h auto-flag on −50%×2, panic-stop) → next product; weekly money-retro rolls up.

## Early-stage grader (resolves the "$0 = noise" contradiction, ex-F10)
At $0 MRR / low-N, do NOT gate actions on MRR-delta (noise). Fitness = LEADING indicators (funnel-step conversion, activation events, cost-per-outcome). Rule-5 NO-OP still applies when even leading signal is absent; an action is required only when a non-noise signal exists. MRR-delta becomes the grader once N is large enough to exceed the noise threshold.

## Anti-patterns (Project Vend — Claude ran a real shop 1mo, LOST money)
selling at a loss / talked into discounts / missing lucrative offers / hallucinating payment details / not learning across runs / vanity metrics / unverified "done". Guards: LTV:CAC>3 enforced, no autonomous discounting, score-driven action, HONESTY+real-read, STATE memory, load-bearing-metric-only, E2E-mandatory.

## Ownership
human-funded instance (Claude sub) runs `earn/human/` + `earn/ai/`; self-funded instances run `earn/ai/` only. This loop = the `earn/human/` product-operator engine.

## Sources (verified 2026-07-03)
Warp issue-triage-loop; Reflexion arXiv 2303.11366; Self-Refine 2303.17651; Anthropic Building-Effective-Agents + Effective-Context-Engineering; MT-Bench 2306.05685; Hamel evals; AARRR (McClure); programmaticseo.com + ahrefs GEO; Anthropic Project Vend; show-me-the-money v2.5.1.
