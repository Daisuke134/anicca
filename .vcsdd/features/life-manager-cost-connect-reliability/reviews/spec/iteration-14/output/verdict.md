# VCSDD Adversary Verdict — life-manager-cost-connect-reliability, spec iteration-3, review round iteration-14

- **Reviewer**: vcsdd-adversary (fresh context, disk-only)
- **Spec reviewed**: `.vcsdd/features/life-manager-cost-connect-reliability/specs/behavioral-spec.md` (frontmatter says "iteration 3", round 3)
- **Timestamp**: 2026-07-04
- **overallVerdict**: **FAIL**

## Reconciliation check (mandatory pre-check per task instructions)

CONFIRMED CLEAN. `apps/life-call/server.js` shows the simple `playWakeClip` (line 390, `async function playWakeClip()`) / `openGeminiLive` (line 409, `function openGeminiLive()`) pair as described — **not** a Groq/edge-tts compositional cascade. `compositional-voice.cjs`, `compositional-live.cjs`, `voice-turn.cjs` do **not** exist anywhere under `apps/life-call/` (grep = 0 hits). The abandoned compositional-cascade experiment is gone; the working tree matches `origin/main`'s actual shipped shape. Proceeding with full review on this basis.

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| Spec Fidelity | **FAIL** | FIND-001, FIND-002 |
| Edge Case Coverage | **FAIL** | FIND-003 |
| Implementation Correctness | **FAIL** | FIND-003, FIND-004 |
| Structural Integrity | **FAIL** | FIND-002 |
| Verification Readiness | **FAIL** | FIND-005 |

## Disk-fact claims that DID verify correctly (positive evidence, for completeness)

- `server.js:390` `playWakeClip` = DEFAULT clip player, `server.js:409` `openGeminiLive` = escalation-only opener — CONFIRMED exact.
- `server.js:444` `if (plan.mode === "oneway" && !gemini) playWakeClip();` on Telnyx `start` = the DEFAULT branch — CONFIRMED.
- `server.js:447` `if (kind === "dtmf" && !gemini) openGeminiLive();` = the only escalation trigger — CONFIRMED.
- `server.js:359` `if (!GEMINI_KEY) { ... close call }` — CONFIRMED (OQ6, C1 EDGE/ERROR).
- `server.js:371-375` `MAX_CONCURRENT` → 1013 reject — CONFIRMED.
- `server.js:365-370` `ctxFromReq` auth gate → 1008 on failure — CONFIRMED.
- `apps/life-call/lib/call-logic.js:28` `LIVE_MODEL = "gemini-2.5-flash-native-audio-preview-09-2025"` — CONFIRMED.
- `apps/life-call/lib/call-logic.js:378` `function buildCallPrompt(event, urgency, lang, name)` — CONFIRMED: no route/duration argument, matches C1's "does NOT recite the route" claim exactly.
- `apps/life-call/lib/call-bridge.cjs:131` `function geminiSetupForEvent(event, urgency, lang, name, model)` — CONFIRMED.
- `scheduler.js:31-34` `WAKE_LEVELS = [{min:10,urgency:"firm"},{min:5,urgency:"harsh"}]` — CONFIRMED (2 levels, no T-15; spec cited 30-33, off by one line, immaterial).
- `scheduler.js:43` (`supaUsers`, batch) and `scheduler.js:281` (`getUserByUid`, per-user refetch) both call `calendarProviderFilter()` — CONFIRMED both sites widened.
- `lib/user-selector.js:7,10-12` `WAKE_CALENDAR_PROVIDERS=["composio_gcal","pipedream_gcal"]` / `calendarProviderFilter()` — CONFIRMED.
- `lib/travel.js:14` `const _routeCache = makeRouteCache({ store: new Map(), ttlMs: 10*60_000 });` — CONFIRMED in-process Map, 10-min TTL, keyed via `route-cache.js` on `(uid, from_geo, to_geo, time_bucket)`.
- `lib/transit.js:15,29-33` `JP_BBOX={latMin:24,latMax:46,lonMin:122,lonMax:146}` + `chooseRouter` = deterministic bbox gate, not journeys-based — CONFIRMED, matches C2 exactly.
- `lib/ask.js:1-9` "We NEVER read or send from the user's Gmail" verbatim, `lib/ask.js:18` imports only `getCalendar` (no `getMail`) — CONFIRMED; `getMail`/`listInbox` exist only at `lib/transport/mail-gog.js` + `lib/transport/mail-unipile.js` (spec cited path as `lib/mail-gog.js`/`lib/mail-unipile.js` — imprecise but the file/dead-code claim itself holds; only caller of `getMail` in the whole `apps/life-call` tree is `transport-gog.test.js`, confirming "dead code, only a test calls it").
- `GEMINI_API_KEY` guard exists; `GROQ` has zero references anywhere in `server.js` — CONFIRMED OQ6 "unused on live path".
- `apps/life-call/package.json:6` `"main":"server.js"`, `apps/life-call/railway.toml:5` `startCommand="node server.js"` — CONFIRMED.
- `apps/landing/app/lm/LmClient.tsx:34` `STRIPE_LM_URL = process.env.NEXT_PUBLIC_STRIPE_LM_URL || ''` — CONFIRMED.
- `apps/life-voice/` (Pipecat/Kokoro, `server.py`, `bot.py`) exists on disk, shelved, not required by `server.js` — CONFIRMED.
- `apps/life-call/migrations/2026-07-04-lm-route-cache.sql` (`lm_route_cache` table, optional future store) exists — CONFIRMED, matches C3's "exists as an OPTIONAL future upgrade... NOT wired as the store today" framing.

## Findings

### FIND-001 — spec_fidelity / requirement_mismatch — misattributed import source for the "two-way Gemini machinery"
- **Severity**: medium
- **Where the false claim lives**: `specs/behavioral-spec.md:11` (§0c) and `specs/behavioral-spec.md:58` (C1 "CURRENT STATE") both state: *"The two-way Gemini machinery (geminiLiveWsUrl, geminiSetupForEvent, routeGeminiMessage, buildGeminiTurn, all imported from lib/call-bridge.cjs) is ALREADY wired into server.js."*
- **Disk fact**: `apps/life-call/server.js:18-28` shows a **split** import: `routeTelnyxMessage, routeGeminiMessage, geminiSetupForEvent, buildTelnyxMediaFrame` come from `./lib/call-bridge.cjs` (lines 18-23), but `geminiLiveWsUrl, buildGeminiTurn, parseGeminiTranscripts` come from `./lib/call-logic.js` (lines 24-28) — a **different file**. `call-bridge.cjs`'s own `module.exports` (lines 139-145) confirms it does NOT export `geminiLiveWsUrl` or `buildGeminiTurn` at all; those two only exist in `call-logic.js`'s exports (lines 465-489).
- **Why it matters**: the spec repeatedly labels this table row and C1 section as "verified 2026-07-04" disk-fact claims. A reader/builder trusting the citation as-written would misdiagnose which file to touch if either function needed changing during the C1 flip. This is a real, checkable inaccuracy, not a nitpick — it appears twice, identically wrong both times.
- **Evidence**: `apps/life-call/server.js:18-28`, `apps/life-call/lib/call-bridge.cjs:139-145`, `apps/life-call/lib/call-logic.js:465-489`.

### FIND-002 — structural_integrity / spec_fidelity — "voice-cheap.js already gone" is FALSE; the file is live and actively imported
- **Severity**: high
- **Where the false claim lives**: `specs/behavioral-spec.md:61` (C1 step 2): *"...delete apps/life-call/lib/{compositional-voice,compositional-live,voice-turn,voice-synth}.cjs + their *.test.js ... (voice-cheap.js already gone.)"*
- **Disk fact**: `apps/life-call/lib/voice-cheap.js` **EXISTS** (44 lines) and is **actively required** by `server.js:29`: `const { buildWakeLine, planVoice } = require("./lib/voice-cheap.js");` — then USED at `server.js:391` (`buildWakeLine` inside `playWakeClip`), `server.js:430` (`planVoice({})`), and `server.js:444` (`plan.mode === "oneway"` gate). Its companion `apps/life-call/lib/voice-cheap.test.js` also exists.
- **Why it matters**: because the spec falsely believes this file is "already gone," C1's explicit delete-list (compositional-voice/compositional-live/voice-turn/voice-synth) **omits `voice-cheap.js` entirely**. C1's prose does say to "remove buildWakeLine/planVoice(one-way) *usage*" from `server.js`, so the import line would presumably get deleted as a side effect of removing `playWakeClip` — but the **file itself and its test are never scheduled for deletion**, because the spec's own tracking sheet says there's nothing left to delete. Per this project's own coding-style rule ("原則: 容赦なく削除する（例外なし）" — ruthlessly delete unused code, no exceptions, no `// UNUSED` comments left lying around), an orphaned `voice-cheap.js` + `voice-cheap.test.js` sitting in the tree post-C1 is exactly the anti-pattern the project's own rules forbid, and the spec's false "already gone" belief is precisely what would let it slip through unnoticed by whoever executes C1 mechanically against the spec's delete-list.
- **Evidence**: `apps/life-call/lib/voice-cheap.js:1-44`, `apps/life-call/server.js:29,391,430,444`, `.claude/rules/coding-style.md` "Refactoring Policy (未使用コード)".

### FIND-003 — edge_case_coverage / requirement_mismatch — barge-in / Gemini `interrupted` handling does not exist on disk, contradicting Goal-1's proof requirement and C1's "existing behavior" claim
- **Severity**: critical
- **Where the false claim lives**: §3 Goal 1 (`specs/behavioral-spec.md:43`): *"Proof = a real answered call where the caller asks a follow-up, gets a spoken Charon answer, and **can interrupt (barge-in)**."* And C1 "OUT" (`specs/behavioral-spec.md:64`): *"a real two-way Charon phone conversation from second 1; **barge-in via Gemini Live's realtimeInput/VAD (existing routeGeminiMessage behavior)**."*
- **Disk fact**: `grep -rn "interrupted|\"clear\"" apps/life-call` returns **zero matches** anywhere in the tree. `routeGeminiMessage` (`apps/life-call/lib/call-bridge.cjs:109-124`) only branches on `msg.setupComplete` and on audio chunks from `parseGeminiAudio(msg)` (`call-logic.js:256-265`, which only reads `serverContent.modelTurn.parts[].inlineData.data`). Neither function reads `serverContent.interrupted`, and nothing ever sends a Telnyx `{"event":"clear"}` frame to flush in-flight/queued playback audio on the carrier side.
- **Why it matters**: per the Gemini Live + Telnyx wire-protocol rules this very project's own CLAUDE.md/rules encode (`~/.claude/rules/building-voice-agents.md`: *"Turn signals on serverContent: generationComplete, turnComplete, interrupted (barge-in → drop playback buffer)"*; *"On interrupted send clear + drop local buffer"*; debug-ladder item #11: *"No interruption flush → on interrupted send clear + drop local buffer"*), real barge-in over a telephony bridge REQUIRES explicitly handling the `interrupted` signal and clearing the carrier's playback queue — Gemini's server-side VAD stopping generation does NOT retroactively un-send audio frames Telnyx has already buffered/started playing. Without this, when a caller speaks over Charon mid-sentence, the previously-queued Telnyx audio will keep playing over them — the opposite of "can interrupt." C1 claims this is "existing routeGeminiMessage behavior" — it is not, per the actual function body cited above. Since C1 as scoped ("small, surgical... only the /ws DEFAULT branch flips from clip→Live... Do NOT extract a new file") does not add interruption handling, and Goal-1's proof explicitly requires demonstrated barge-in, the C1 change as literally specified cannot satisfy its own parent Goal's acceptance condition.
- **Evidence**: `apps/life-call/lib/call-bridge.cjs:109-124`, `apps/life-call/lib/call-logic.js:256-265`, grep of `apps/life-call/**` for `interrupted`/`"clear"` = 0 hits, `~/.claude/rules/building-voice-agents.md` (Telnyx interruption section + debug ladder #11).

### FIND-004 — implementation_correctness — §4 RED plan omits any automated check for the barge-in claim it depends on
- **Severity**: high
- **Where**: `specs/behavioral-spec.md:109` (§4 RED — C1), items (a)-(e) plus the parenthetical "NO-MOCK E2E" line: *"real wake call on the Gemini Live path (Dais hears + converses + interrupts)"*.
- **Issue**: none of RED items (a)-(e) assert anything about interruption handling (no grep for `interrupted`, no unit test proposed for a "send clear on Gemini interrupt" pure function analogous to `routeGeminiMessage`/`routeTelnyxMessage`). The ONLY place barge-in is checked is a manual, subjective, human-observed E2E step ("Dais hears + converses + interrupts") that runs AFTER the adversary already PASSed the logic review. Given FIND-003 shows the underlying mechanism doesn't exist in code today and C1 doesn't add it, a builder following §4's RED/GREEN checklist literally would get every listed assertion to GREEN (the flip + deletions) while still shipping non-functional barge-in — and nothing in the automated verification plan would catch that regression before the manual call.
- **Evidence**: `specs/behavioral-spec.md:109-110` (§4), cross-referenced against FIND-003's `apps/life-call/lib/call-bridge.cjs:109-124` gap.

### FIND-005 — verification_readiness — RED assertion (c) has a blind spot that lets FIND-002's dead file through undetected
- **Severity**: medium
- **Where**: `specs/behavioral-spec.md:109`, RED item (c): *"grep proves compositional-{voice,live}.cjs/voice-turn.cjs/voice-synth.cjs are GONE and nothing requires them."*
- **Issue**: because `voice-cheap.js` was (incorrectly, per FIND-002) believed already-deleted, it is not part of this grep-based GREEN gate. A post-C1 tree that still contains `apps/life-call/lib/voice-cheap.js` + `voice-cheap.test.js` (dead, unreferenced) would pass RED-item (c) as literally written, silently permitting the exact dead-code regression the project's own coding-style rule forbids. A verification plan that is supposed to prove "the ONLY voice path is Gemini Live... the one-way clip + cascade files are gone" (C1 INVARIANT, `specs/behavioral-spec.md:69`) should enumerate every file the clip path touches, not a stale subset.
- **Evidence**: `specs/behavioral-spec.md:69,109`, cross-referenced against FIND-002's disk evidence (`apps/life-call/lib/voice-cheap.js` existing + imported).

## Convergence signals
- findingCount: 5
- allCriteriaEvaluated: n/a (spec review, no CRIT-XXX contract criteria in this manifest)
- duplicateFindings: none (FIND-002/FIND-005 are related but distinct: FIND-002 = the false disk-fact claim + resulting dead file; FIND-005 = the verification-plan blind spot that would let it through undetected)

## Summary for the Builder
This is NOT a "looks good" pass. Three of five dimensions fail on freshly-verified, file:line-cited disk facts that contradict the spec's own "verified 2026-07-04" claims:
1. Fix the import-source citation for `geminiLiveWsUrl`/`buildGeminiTurn` (they come from `call-logic.js`, not `call-bridge.cjs`).
2. Either (a) add `voice-cheap.js` + `voice-cheap.test.js` to C1's explicit delete-list, or (b) if there's a reason to keep it, say so — but "already gone" is false and must not ship as a verified fact.
3. Add explicit barge-in handling (Gemini `serverContent.interrupted` → send Telnyx `{"event":"clear"}` + drop the local playback state) to C1's scope, since Goal-1's proof condition literally requires demonstrated interruption and the code that would make that true does not currently exist.
4. Extend §4 RED with an assertion that covers the interruption/clear mechanism (not just the default-flip + file deletions) and widen RED-item (c)'s file list to include `voice-cheap.js`.
