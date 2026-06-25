# PHASE C — realize + VERIFY the 3 location cases (Life Manager / apps/life-call)

Status: SPEC (2026-06-25). LAUNCH-ORDER item 6. Builder = main agent; verifier = fresh `vcsdd:vcsdd-adversary`.
NO-MOCK E2E = real Gemini judgment + real live Supabase + (C6) the DEPLOYED Inngest cron.

## 0. Current state (verified from code 2026-06-25 — what EXISTS vs the GAPS)
EXISTS (do NOT rebuild):
- **The judgment is already agentic, NO regex** — `lib/ask.js agentResolveLocation` is a Gemini tool-loop
  (places_search + submit_answer, 5 turns, temperature 0) returning `online | filled | ask`. Its prompt
  already covers C1 (landmark/shop/office/school → search → address), C2 (online/Zoom/電話/remote → no-travel),
  C5 (Sleep/run/meditation/remote-day-job → no-travel), C3-ask (Lunch with Mai / 1on1 → ask). This IS the
  "LLM + tools in a loop" agent — the `@openai/agents` rewrite mentioned in HARD-2's note is UNNECESSARY
  (rewriting a working agentic loop just to swap the lib = churn/originality = a sin). Keep the Gemini loop;
  it runs on Gemini → $0 OpenAI by construction.
- **REQ-15 RETURN block = DONE** — `lib/travel.js returnDecision` + `travel-return.test.js` (unit + integration
  + idempotency). The "UNIMPLEMENTED gap" note in behavioral-spec REQ-15 is STALE → will fix.
- **askTick flow** — for each needsLocation event: agentResolveLocation → online(skip) / filled(patchEvent) /
  ask (C-H1 atomic claim → Telegram else email). lm_ask_log dedups the ASK SEND only.
- **Determinism** — temperature 0 is set in agentResolveLocation (the C4 mechanism); needs an N-run MEASUREMENT.

THE GAPS PHASE C must close:
1. **C3 REMEMBER (the core new build)** — there is NO memory. askTick does NOT check a remembered place before
   asking, and the reply handlers (telegram-reply / email) do NOT store the answer. So a recurring vague event
   ("Lunch with Mai", "おばあちゃんの家") is ASKED AGAIN every week. `lm_user_places` table = 404 (absent).
2. **C4 determinism** — no harness proving ≥9/10 stable per case.
3. **C6 autonomous witness** — no live proof the DEPLOYED Inngest sweep-ask cron autofills (vs a manual run).
4. **Location-case eval** — no no-mock eval running agentResolveLocation against the canonical cases.

## 1. Memory design = Supabase `lm_user_places` (NOT mem0) — pooled-compatible, no new dep
Decision cited: CANONICAL.md "Memory = Supabase per-user lm_user_places (pooled-compatible; native MEMORY.md
was for the dropped per-instance model)". mem0ai is heavier + a new dep; a Supabase table is the proven,
simpler, pooled pattern. The recall/remember KEY is deterministic BOOKKEEPING (like lm_ask_log keys by
event_id) — NOT a judgment, so a normalized-string key is correct here (not the regex-for-judgment anti-pattern).

- Migration `2026-06-25-phase-c-user-places.sql`:
  `lm_user_places(uid text, phrase text, address text, created_at timestamptz default now(),
   updated_at timestamptz default now(), UNIQUE(uid, phrase))` + index(uid) + RLS (service-role only).
- `phrase` = a normalized key derived from the event SUMMARY (lowercase, collapse whitespace, trim). Recurring
  events repeat their summary → stable key → recall hits. (Edge: two different events share a summary but
  different real places → last answer wins; acceptable, user can re-answer.)
- `lib/places-memory.js` (NEW, pure-ish IO):
  - `placeKey(summary)` → normalized phrase (PURE).
  - `recallPlace(uid, phrase, supaUrl, supaKey)` → address|null (GET lm_user_places).
  - `rememberPlace(uid, phrase, address, supaUrl, supaKey)` → upsert (POST Prefer resolution=merge-duplicates).

## 2. Wiring (REQ updates)
- **askTick (lib/ask.js)**: BEFORE agentResolveLocation, `const mem = await recallPlace(uid, placeKey(summary))`;
  if mem → `patchEvent(location=mem)` + autofilled++ + continue (NO ask, NO Gemini call — cheap + instant).
  Else agentResolveLocation as today.
- **Reply handlers (lib/telegram-reply.js + the email reply path)**: after patching the event location from the
  user's answer, `await rememberPlace(uid, placeKey(summary), answerAddress)` so the NEXT same-summary event
  auto-fills from memory and is never asked again.
- A `filled` result (web-searchable venue) does NOT need memory (it re-resolves cheaply); memory is for the
  ASK class (human-only knowledge). Optional: also remember filled results to save Gemini calls — out of scope.

## 3. Requirements (EARS) — append to behavioral-spec §I
- REQ-45 WHEN an event needs a location and a remembered place exists for its phrase (lm_user_places), the
  system SHALL autofill from memory and SHALL NOT ask or call the model.
- REQ-46 WHEN the user answers a location ask (Telegram or email), the system SHALL REMEMBER (uid, phrase,
  address) so a future event with the same phrase autofills without asking again.
- REQ-47 The remember/recall phrase key SHALL be a deterministic normalization of the event summary
  (bookkeeping, not a judgment) — case/whitespace-insensitive.
- REQ-48 (C4) The SAME event SHALL classify identically over N≥10 runs (temperature 0); the eval harness SHALL
  measure ≥9/10 stable per canonical case.
- REQ-49 (REQ-15 RESTATE) The RETURN [Travel] block is implemented (returnDecision) — mark the stale gap closed.

## 4. Verification (no-mock, the C-cases)
- **C3 unit**: placeKey normalization; recall/remember claim/upsert (injected fetch).
- **C3 E2E (live Supabase)**: seed nothing → ask path stores via rememberPlace → a 2nd run with the same summary
  RECALLS → autofills, NO ask. Assert lm_user_places row + the event patched.
- **C1/C2/C5/C7 + C4 eval (real Gemini)**: `scripts/phase-c-eval.js` runs agentResolveLocation against the
  canonical case set (Skytree/スタバ/MUIT/NAIST = filled; 電話オンライン/Zoom/三島さんとオンライン = online;
  Sleep/run/meditation = online; Lunch with Mai/1on1/おばあちゃんの家 = ask) × N runs → asserts the expected
  kind + ≥9/10 determinism. EN+JA (C7). Needs GEMINI_API_KEY + LIFE_MAPS_KEY.
- **C6 autonomous witness**: on the DEPLOYED life-call (Railway), a real test user + a real test calendar event
  with an unknown location → WITNESS the Inngest sweep-ask cron actually autofill/ask (not a manual node run) →
  confirm the calendar/lm_ask_log changed. (Uses the same Stripe-sandbox test tenant.)
- Each work-item gated by a fresh `vcsdd:vcsdd-adversary` before merge.

## 5. Work-items / order (VCSDD each)
- **PC-1 (C3 memory)** ← FIRST: lm_user_places migration + places-memory.js + wire recall(askTick)+remember(reply)
  + unit tests + live-Supabase E2E + adversary. THE main build.
- **PC-2 (eval harness, C1/C2/C5/C7 + C4)**: phase-c-eval.js no-mock against canonical cases × N → determinism.
- **PC-3 (C6 witness)**: live deployed-cron autofill witness on the test tenant.
- REQ-15/REQ-49: flip the stale behavioral-spec note (RETURN done).
- C9 YouTube wiring → D-3 (not here).

## 6. Files
- NEW: `lib/places-memory.js`, `lib/places-memory.test.js`,
  `migrations/2026-06-25-phase-c-user-places.sql`, `scripts/phase-c-eval.js`.
- EDIT: `lib/ask.js` (recall before ask + remember hook), `lib/telegram-reply.js` (remember on reply),
  behavioral-spec.md (§I REQ-45..49 + REQ-15 note), package.json (eval not in npm test — it hits real Gemini).
- Branch: `feature/phase-c-memory` → PR → main (matching HARD-1..4).
