# Behavioral Spec (Phase 1a, EARS) — profitable-article-writer

Mode: strict · Source design: `docs/superpowers/specs/2026-06-29-profitable-article-writer-design.md`
One article → funnel → per-platform native monetization → real money verified, zero human in the runtime loop.

## Ubiquitous requirements (The skill SHALL …)

- **REQ-1 Model-agnostic.** The skill SHALL name no model/provider/API key and SHALL run on whatever frontier
  model the running agent uses (Claude/Opus today; GPT/Grok/DeepSeek/Kimi later).
- **REQ-2 Zero human in the runtime loop — asserted of the END STATE (Mode B) ONLY.** The only human contribution is a
  ONE-TIME INSTALL provisioning of: COMPUTE (a subscription), a payout identity, AND — for any rail whose zero-human
  account creation is not yet proven (REQ-11: e.g. note / phone-gated X) — the platform account itself. These are
  install-time facts, NOT runtime steps. At RUNTIME in Mode B (write→gate→publish→verify) there is no human
  click/OTP/approval/delivery. **Mode A (draft-first, REQ-6) is an EXPLICIT, temporary supervised bootstrap that
  INTENTIONALLY carries a human review+publish gate**; it is the trust ramp and does NOT satisfy — and is NOT claimed
  to satisfy — the zero-human invariant. The invariant is asserted of Mode B, never of Mode A. (Resolves FIND-001, new FIND-005.)
- **REQ-3 Explain, don't run.** The article SHALL be a deeply-researched, VISUAL explainer. The skill SHALL NOT
  execute external repos/tools to produce the article, SHALL NOT claim to have run anything, and SHALL NOT emit
  error-log content (brand safety).
- **REQ-15 Per-install identity.** All credentials SHALL come from the install's own env; NO shared/Dais accounts.
  Each platform SHALL be a credential-gated slot in `registry.json`; an install activates only rails whose creds exist.

## Event-driven (WHEN <trigger> the skill SHALL <response>)

- **REQ-4** WHEN a wake fires, the skill SHALL pick a niche/topic (default: AI-entities) and produce ONE article via
  research → decide(theme / buy-reason-3-lines / free-vs-paid split, What-free/How-paid) → write(craft layer) → de-slop.
- **REQ-4b** IF, at a wake, no viable topic exists OR research is insufficient for a genuinely useful piece, THEN the
  skill SHALL SKIP the wake (produce NO article) rather than emit a thin/slop piece. (Resolves FIND-004.)
- **REQ-5** WHEN a draft is produced, the skill SHALL run gate **V0** (render/slop, existing note-publish vision check)
  and **V0.5** BEFORE any publish. **V0.5 is a REPRODUCIBLE gate: a fresh-context adversary scores the draft against a
  FIXED set of BINARY criteria; PASS = ALL true** — (a) an opening hook states a reader pain / curiosity / concrete
  number; (b) a CTA to a paid rail is present; (c) the free part ends at a payoff cut (the How is withheld); (d) the
  draft makes NO claim of having executed/run anything and contains NO error-log/stack-trace text (this is where
  REQ-3's semantic check lives); (e) readability, measured mechanically: ≥70% of
  sentences are ≤60 characters (mobile-scannable) — an objective, computable threshold, not a subjective judgment.
  Any FALSE ⇒ V0.5 FAIL. (Resolves FIND-008/009, iter2 FIND-002/003, iter3 FIND-001.)
  **Edge case (Sprint 2, PROP-18):** criterion (e)'s sentence-splitter SHALL recognize Japanese full-width
  terminal punctuation (。！？) as sentence boundaries, in addition to ASCII ('.','!','?') — REQ-19's daily
  executor writes a JAPANESE note DRAFT, and an ASCII-only splitter collapses an entire well-punctuated
  Japanese paragraph into one sentence, permanently failing (e) regardless of true sentence length.
- **REQ-6** WHEN V0+V0.5 PASS AND mode = A (AUTONOMY=off, default), the skill SHALL stop at a note DRAFT and notify
  the human (URL + screenshot) for review; it SHALL NOT publish.
- **REQ-7** WHEN V0+V0.5 PASS AND mode = B (AUTONOMY=on), the skill SHALL publish directly, then distribute to reach platforms.
- **REQ-8** WHEN an article reaches a rail, the skill SHALL monetize per that rail's NATIVE mechanism (note ¥500 single +
  optional 月額マガジン; Substack paid sub; X ad-rev / Articles / Subscriptions; Zenn 有料Books) and SHALL treat
  paywall-less rails (dev.to, X posts) as top-funnel into the paid rails + an owned email list.
- **REQ-9** WHEN money is expected, verification SHALL climb V0→V5; DONE for an earn unit is **V4** = a real external
  ¥/USDC receipt, confirmed by `record-earn`'s anti-fake gate AND an independent browser/on-chain check — never "published".

## State-driven (WHILE <state>)

- **REQ-10** WHILE human-funded, payout SHALL target the human's payout account (one-time install fact) AND the
  bank-KYC rails (note / Substack / Zenn) ARE available. WHILE self-funded, bank KYC is impossible, so those rails
  are NOT available for payout and SHALL be disabled; the self-funded install SHALL monetize ONLY via crypto-native
  checkout (x402 / own → instance wallet). Thus REQ-8's usable rail set is gated by funding mode, not by credentials
  alone. (Resolves FIND-002.)
- **REQ-12** WHILE running a loop wake, the model tier SHALL be Sonnet (never Opus); `record-earn` SHALL run with NO LLM.

## Conditional (IF <condition> THEN the skill SHALL …)

- **REQ-11** IF a platform account is absent THEN the skill SHALL self-create it zero-human where proven (Instagram
  pattern: Gmail plus-address + OTP auto-read, no phone/captcha) OR flag the rail unavailable (phone-gated X/note account
  creation is NOT yet proven) — it SHALL NOT fail loudly or spew errors.
- **REQ-16** IF an earn is claimed on a rail THEN V4 SHALL be verified PER RAIL and PER funding-mode by a
  ZERO-HUMAN-verifiable signal read with the install's STORED creds: **self-funded = an on-chain USDC receipt**
  (record-earn anti-fake). **human-funded = a platform sale event read with zero human** — concretely: note =
  authenticated GET of the note sales-management endpoint the creator dashboard calls (via the stored
  NOTE_SESSION_COOKIE), parsed for the sale; Substack = Stripe API (charge/balance) via the stored key; X = the
  creator analytics API. The subsequent BANK withdrawal is a ONE-TIME human install-setup, OUTSIDE the per-earn loop,
  and SHALL NOT be asserted as an automated runtime gate. (Resolves FIND-006, new FIND-001.)

## Unwanted-behavior (IF <unwanted> THEN the skill SHALL <mitigate>)

- **REQ-13** IF any sub-step would need a human runtime action THEN the skill SHALL substitute an autonomous path
  (stored creds / Gmail-OTP auto-read / CapSolver+camofox) or SHALL NOT count that rail toward earn.
- **REQ-14** IF a draft fails V0 or V0.5 THEN the skill SHALL fix and re-gate for AT MOST 3 rounds; IF still failing
  after 3 rounds THEN it SHALL abort the wake (produce no publish) and record the failure. It SHALL NEVER publish a
  failing draft (fail-closed). (Resolves FIND-003.)

## Real publish (Sprint 2.5, Dais 2026-07-04: "the note is not actually published, we have to have it actually published, after the verification")

- **REQ-21 Real ONE-OFF publish tool — NOT wired into run.sh, NOT Mode B.** The skill SHALL provide a standalone,
  human/main-agent-invoked tool (`lib/note-publish-live.py`) that, given an EXPLICIT note draft key argument and
  a note draft already carrying a validated 記事タイプ=有料/¥500 configuration and cover + visuals, drives the
  browser to click 投稿する/更新する for real, making that ONE draft PUBLIC. This tool is explicitly OUT OF
  `run.sh`'s call graph — it SHALL NOT be invoked from `run.sh`, from the `AUTONOMY` branch logic, or from any
  unattended daily wake path; it is only ever invoked directly, once, by a human or the main agent, naming the
  exact draft key. This does NOT satisfy, and SHALL NOT be described as satisfying, REQ-2's zero-human-in-Mode-B
  invariant — REQ-2 remains scoped to `run.sh`'s own automated publish branch (REQ-7), which this tool is
  structurally excluded from. Mode A's draft-only scripts SHALL continue to NEVER contain a 投稿する/更新する
  click target (REQ-6 is unaffected; grep-verifiable). The tool SHALL require an explicit trigger
  (`NOTE_LIVE_PUBLISH=1`) AND a named `--draft-key` argument (no default/wildcard key). It SHALL fail closed: if
  the pre-publish state (price/type/visuals) cannot be confirmed for that exact key, it SHALL NOT click publish
  and SHALL report the exact blocking reason. On a successful invocation with a confirmed-ready draft, the tool
  SHALL actually perform the click and SHALL NOT be satisfiable by an always-refuse stub (a real success path
  must exist and be exercised, not merely a refusal path).
- **REQ-22 Post-publish verification (V1 real) — independent of the publish tool.** After REQ-21's tool reports a
  publish attempt, verification SHALL be performed by a SEPARATE process/invocation from the publish tool itself
  (the tool's own stdout claim is not sufficient) — a logged-out HTTP fetch (no stored cookies) of the public
  note.com URL, checking BOTH a 200 status AND the presence of page content proving the specific article rendered
  (e.g. the article title or note ID in the HTML), not just any 200 (guards against an SPA shell returning 200
  for a non-existent path). The live URL + timestamp + this independent verification's result SHALL be recorded
  to state for V4 (earn) tracking to begin against it.

## Mode-B in-loop publish (Sprint 4, Dais 2026-07-04: "then wire that in, yes, we have to")

REQ-21's tool proved the mechanism works but requires a human/main-agent hand on the trigger. This section wires
the SAME mechanism into the unattended daily loop so no human/Opus ever triggers it again.

- **REQ-23 Mode-B publish branch, in-loop.** WHEN `run.sh`'s branch-selection logic evaluates the EFFECTIVE mode
  for the current wake (REQ-25's ratio-derived value, not the raw `AUTONOMY` variable in isolation) AND that
  evaluates to Mode B AND V0∧V0.5 PASS, THEN `run.sh` SHALL call a SHARED, importable core function — the SAME
  module `lib/note-publish-live.py` imports for its own confirm→click sequence, with the pre-publish checks
  (price/type/eyecatch/visuals) AND the try/except/finally exception-safety (the REQ-21/FIND-004 fix) living
  INSIDE that shared unit, not re-wrapped or reimplemented per caller — a future change to the shared function
  SHALL apply to both callers identically (single source, grep-verifiable: the publish-click statement appears
  in exactly one file). This is the ONLY code path allowed to reach a real publish click from an unattended
  wake. Mode A's branch SHALL be REQUIRED to demonstrate — by a dynamic call-count assertion on the shared
  function (the same pattern PROP-6 already uses for Mode A's no-publish invariant), not merely a static grep —
  that it never calls the shared publish function under any AUTONOMY/branch-selection value that resolves to
  Mode A, including a deliberately-injected branch-selection bug in the test harness.
- **REQ-24 Mode-B post-publish verify, in-loop.** Immediately after a Mode-B publish click, `run.sh` SHALL
  invoke the SAME independent-verification logic as REQ-22's standalone verifier (logged-out fetch, 200 AND
  content-match) and record the result to state. ON SUCCESS, `run.sh` SHALL record the SAME fields REQ-22
  requires (URL + timestamp + verification result) so V4 (earn) tracking begins exactly as it does for the
  standalone tool — a success path SHALL be positively tested, not merely inferred from the absence of a
  failure test. ON verification failure or inconclusive result, the wake SHALL record an UNCONFIRMED-publish
  state (never silently assume success) for a later wake or self-heal (REQ-17, Sprint 7) to reconcile — it
  SHALL NOT retry-publish the same draft blindly (risking a duplicate/garbled post).
- **REQ-25 Graduation is per-install, gradual, explicit, and ACTUALLY CONSULTED.** The effective per-wake mode
  SHALL be computed from an install-level ratio/mix configuration value (e.g. "1-in-N wakes run Mode B"), read
  from runtime config/state — NOT a source-code default, and NOT satisfiable by a bundled installer template
  that pre-sets a fixed value equivalent to a hardcoded default (the config value SHALL be re-readable/mutable
  at runtime without a code change, and a test SHALL prove changing it changes wake behavior without redeploying
  code). REQ-23's branch-selection logic SHALL consult THIS ratio-derived effective mode, not a raw binary
  `AUTONOMY` flag read independently — a test SHALL prove that setting the ratio to "1-in-N" actually produces
  N-1 Mode-A wakes and 1 Mode-B wake over N consecutive wakes, not merely that the ratio value is stored.

## Self-operation (self-heal + self-improve — zero Opus + zero human, Dais 2026-07-04)

- **REQ-17 Self-heal.** WHILE running unattended, IF a wake fails (crash, stuck gate, publish error, expired/blocked
  cred) THEN the skill SHALL detect it from its OWN logs/state, diagnose the root cause, and attempt an autonomous fix
  (retry, refresh cred, back off, switch rail) with NO Opus and NO human in the loop. An unrecoverable rail SHALL be
  quarantined + recorded and the wake loop SHALL survive — a single failure NEVER crashes the whole loop. (Sprint 5.)
- **REQ-18 Self-improve.** WHILE running daily, the skill SHALL read its OWN per-rail stats (V2 reach, V3 convert,
  V4 earn) and adjust the NEXT wake's choices (topic / niche / hook / price / rail-mix) to increase earn — a closed
  improvement loop the running model drives BY JUDGMENT (right-altitude prompt, NOT hardcoded rules), with NO Opus and
  NO human. Every change SHALL be recorded to state for audit. (Sprint 5.)

## Operating model (Dais 2026-07-04) — daily executor + verifier, roles are separate

- **REQ-19 Daily executor = `claude -p` (Sonnet).** The DAILY article wake — research → write → V0/V0.5 → **post a
  note DRAFT (Mode A)** — SHALL be executed by the headless `claude -p --model sonnet` loop, unattended, one wake per
  day. This is the executor; it does the work and posts the draft. (Wiring into the runtime loop = Sprint 4.)
- **REQ-20 Verifier = the main agent (Opus), out of the daily loop.** Verification of what the loop posted (the
  rendered note DRAFT: no slop, paywall gate, hook/CTA present, renders correctly) SHALL be done by the verifier
  (me / the main agent) via a real browser look at the posted draft — NOT by the executor grading itself. The
  executor posts; the verifier checks. (This is the Mode-A trust ramp: executor drafts daily, verifier approves;
  once trusted, Mode B flips to autonomous publish, and self-heal/self-improve (Sprint 5) removes the verifier too.)
  **Sprint-2 note-publish integration (PROP-19/20/21):** the real note DRAFT post SHALL REUSE the existing,
  already-proven `ai-entity-article-writer/scripts/note-publish/` pipeline for AUTH and VERIFY only (session
  cookies, and the `verify` subcommand's ground-truth API + logged-out screenshot check) — that part is NEVER
  rebuilt. The one genuinely-missing piece (creating a BRAND-NEW note draft, as opposed to updating the
  pre-existing Automaton note) SHALL use `note_mcp.api.articles.create_draft` — the SAME underlying library the
  reused pipeline's own `note-stage2-publish.py` already depends on for `update_article` — so no non-Automaton
  article can ever overwrite the live published Automaton note (that note's numeric id stays hardcoded-and-guarded
  in the upstream script; the new-draft path never touches it).
  **Round-2 correction (FIND-009):** the OLD pipeline's own eyecatch/目次/paywall-gate sub-scripts
  (`publish.py`/`toggle-plan.py`/`set-eyecatch-republish.py`) are NOT reused for eyecatch or monetization —
  a real live-wake evidence draft exposed that those scripts hardcode a メンバーシップ (recurring
  membership) monetization path regardless of REQ-8's native single ¥500 有料note requirement, and never set
  an eyecatch at all. This is a legitimate, contract-approved (CRIT-106) engineering deviation: eyecatch is
  now set via this skill's own `lib/note-set-eyecatch.py` (driving the editor's own 画像を追加 button — the
  note_mcp `upload_eyecatch_image` API path was tried first and reproducibly fails), and the single ¥500
  paid-area price is set via this skill's own `lib/note-set-single-price.py` (selecting 記事タイプ=有料,
  never メンバーシップ). Visuals (hero + inline figures) are embedded via this skill's own
  `lib/note-create-rich-draft.py`, orchestrating note_mcp's `upload_body_image`/`generate_image_html` before
  `create_draft`. Any failure in the create/eyecatch/price/verify chain SHALL degrade to the Mode-A safe
  placeholder (REQ-6) rather than crash the wake or fabricate a URL.

## Purity-boundary candidates (refined in 1b)

- **Deterministic tools:** `record-earn` ledger, render/screenshot verify, platform publishers, dedup, git, payout routing.
- **Agent judgment (non-deterministic):** niche/topic pick, theme decision, buy-reason-3-lines, free/paid split, craft
  writing, V0.5 craft scoring, per-rail repurposing.
- **External side-effects:** publish (note/X/Substack/Zenn/dev.to), payment receipt, account creation.

## Out of scope (this feature)

Spawning self-funded children (Sprint 6); rebuilding the daemon / founder-loop ledger (reused); Brain/Tips affiliate.
Opus is OUT of the runtime loop entirely (build-time only); self-heal + self-improve run on the same Sonnet loop.
