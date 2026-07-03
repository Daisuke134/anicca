# Behavioral Spec (Phase 1a, EARS) — profitable-article-writer

Mode: strict · Source design: `docs/superpowers/specs/2026-06-29-profitable-article-writer-design.md`
One article → funnel → per-platform native monetization → real money verified, zero human in the runtime loop.

## Ubiquitous requirements (The skill SHALL …)

- **REQ-1 Model-agnostic.** The skill SHALL name no model/provider/API key and SHALL run on whatever frontier
  model the running agent uses (Claude/Opus today; GPT/Grok/DeepSeek/Kimi later).
- **REQ-2 Zero human in the runtime loop.** The only permitted human contribution is COMPUTE (a subscription)
  plus a one-time payout identity supplied at install. No human click / OTP relay / approval / delivery at runtime.
- **REQ-3 Explain, don't run.** The article SHALL be a deeply-researched, VISUAL explainer. The skill SHALL NOT
  execute external repos/tools to produce the article, SHALL NOT claim to have run anything, and SHALL NOT emit
  error-log content (brand safety).
- **REQ-15 Per-install identity.** All credentials SHALL come from the install's own env; NO shared/Dais accounts.
  Each platform SHALL be a credential-gated slot in `registry.json`; an install activates only rails whose creds exist.

## Event-driven (WHEN <trigger> the skill SHALL <response>)

- **REQ-4** WHEN a wake fires, the skill SHALL pick a niche/topic (default: AI-entities) and produce ONE article via
  research → decide(theme / buy-reason-3-lines / free-vs-paid split, What-free/How-paid) → write(craft layer) → de-slop.
- **REQ-5** WHEN a draft is produced, the skill SHALL run gate **V0** (render/slop) and **V0.5** (craft: hook creates
  desire? CTA exists? free part = sales letter? readability pass?) BEFORE any publish.
- **REQ-6** WHEN V0+V0.5 PASS AND mode = A (AUTONOMY=off, default), the skill SHALL stop at a note DRAFT and notify
  the human (URL + screenshot) for review; it SHALL NOT publish.
- **REQ-7** WHEN V0+V0.5 PASS AND mode = B (AUTONOMY=on), the skill SHALL publish directly, then distribute to reach platforms.
- **REQ-8** WHEN an article reaches a rail, the skill SHALL monetize per that rail's NATIVE mechanism (note ¥500 single +
  optional 月額マガジン; Substack paid sub; X ad-rev / Articles / Subscriptions; Zenn 有料Books) and SHALL treat
  paywall-less rails (dev.to, X posts) as top-funnel into the paid rails + an owned email list.
- **REQ-9** WHEN money is expected, verification SHALL climb V0→V5; DONE for an earn unit is **V4** = a real external
  ¥/USDC receipt, confirmed by `record-earn`'s anti-fake gate AND an independent browser/on-chain check — never "published".

## State-driven (WHILE <state>)

- **REQ-10** WHILE the install is human-funded, payout SHALL target the human's payout account (one-time install fact);
  WHILE self-funded, payout SHALL be crypto-native (x402 / own checkout → instance wallet), since bank KYC is impossible.
- **REQ-12** WHILE running a loop wake, the model tier SHALL be Sonnet (never Opus); `record-earn` SHALL run with NO LLM.

## Conditional (IF <condition> THEN the skill SHALL …)

- **REQ-11** IF a platform account is absent THEN the skill SHALL self-create it zero-human where proven (Instagram
  pattern: Gmail plus-address + OTP auto-read, no phone/captcha) OR flag the rail unavailable (phone-gated X/note account
  creation is NOT yet proven) — it SHALL NOT fail loudly or spew errors.
- **REQ-16** IF an earn is claimed on a rail THEN V4 SHALL be verified PER RAIL and PER funding-mode (bank receipt for
  human-funded, on-chain receipt for self-funded).

## Unwanted-behavior (IF <unwanted> THEN the skill SHALL <mitigate>)

- **REQ-13** IF any sub-step would need a human runtime action THEN the skill SHALL substitute an autonomous path
  (stored creds / Gmail-OTP auto-read / CapSolver+camofox) or SHALL NOT count that rail toward earn.
- **REQ-14** IF a draft fails V0 or V0.5 THEN the skill SHALL fix and re-gate within bounded rounds and SHALL NOT
  publish a failing draft (fail-closed).

## Purity-boundary candidates (refined in 1b)

- **Deterministic tools:** `record-earn` ledger, render/screenshot verify, platform publishers, dedup, git, payout routing.
- **Agent judgment (non-deterministic):** niche/topic pick, theme decision, buy-reason-3-lines, free/paid split, craft
  writing, V0.5 craft scoring, per-rail repurposing.
- **External side-effects:** publish (note/X/Substack/Zenn/dev.to), payment receipt, account creation.

## Out of scope (this feature)

Spawning self-funded children (Spec 4); rebuilding the daemon / founder-loop ledger (reused); Brain/Tips affiliate.
