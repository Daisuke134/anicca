# 2026-06-14 — Life-manager phone bridge restore + Twilio Trust Hub + persona + pre-register

★ status: WIP — Phase 1 完了 (bridge restored, Twilio 21216 confirmed)、 Phase 2 進行中 (Trust Hub Business Profile 申請)。

## Background

Dais reported on 2026-06-14: 「life-manager の電話が来ない、 直して」。 root-cause investigation revealed two stacked failures:

| Layer | Status before fix | Status after Phase 1 |
|---|---|---|
| anicca-phone outbound bridge (launchd `ai.anicca.pipecat-phone`) | DEAD — launchd plist referenced `~/anicca-oss-pipecat/skills/anicca-phone/outbound/run.sh` which was deleted in the 2026-06-09 cleanup (the `anicca-oss` → `anicca` rename removed the entire `anicca-oss-pipecat` worktree). KeepAlive crash-loop, port 7860 dead, `state/anicca_phone_url.txt` stale, every `calendar-event-call` cycle logged `pipecat-phone unhealthy at http://127.0.0.1:7860 ⚠️ call not placed` | ALIVE — skill restored to `~/.openclaw/skills/anicca-phone/`, run.sh REPO_DIR + plist ProgramArguments/WorkingDirectory updated, venv rebuilt (python 3.13, ~725MB, gitignored), launchd pid alive, port 7860 LISTEN, cloudflared tunnel = `https://conventional-birmingham-thermal-particle.trycloudflare.com`, `state/anicca_phone_url.txt` writes on every restart. Commit 45ea3238d on anicca-dais main-internal. |
| Twilio outbound API (the actual call placement) | UNKNOWN at bridge restore time, then discovered: **all dialouts return error 21216 "Account not allowed to call"** for both JP target (+818046270314) and Twilio US magic test (+15005550006), proving an account-wide block (not a number-level block). Last successful call: 2026-06-09 21:43 — no attempts at all between 6/10–6/14 because the bridge was dead. | OPEN — see Phase 2 below |

## Root cause of the Twilio block (Phase 2 problem)

Twilio docs https://www.twilio.com/docs/api/errors/21216 verbatim:
> *"Your account was created outside the United States or Canada on or after October 8, 2025 and does not have an approved Business Primary Customer Profile. An Individual Primary Customer Profile created after October 8, 2025 does not satisfy this requirement for +1 calling. Support cannot manually remove this restriction."*

Dais's Twilio account (SID stored in `~/.openclaw/.env::TWILIO_ACCOUNT_SID`, Master/Full/active, JPY ¥3,309 balance) was created on 2026-05-10 (= post-2025-10-08 cutoff). The existing Trust Hub draft (Profile SID `BU7d…redacted`, status=draft, created 2026-05-10) is an **Individual Primary Customer Profile** (`individual_customer_profile_information` EndUserType, attributes already populated with 成田大祐 / 2002-01-30 / +818046270314 / 新宿区南元町15-27 / `myn` identification). Per the docs, completing this Individual profile **will not** restore outbound — it does not satisfy the policy.

We must build a **Business Primary Customer Profile** instead.

## Decision Dais 2026-06-14

| Path | Dais decision |
|---|---|
| A. Bland.ai fallback | ★ NO ★ — Dais: "YES everything works with twilio we have been doing... so yes." Stay on Twilio. Charon (Gemini Live) preserved. |
| B. Twilio Trust Hub Business Profile submission via API | ★ YES ★ — accept the 1-3 business-day review delay, no real call until approval. |
| C. Both in parallel | rejected (A side dropped) |

## Phase 2 plan — Business Primary Customer Profile via Trust Hub REST API

Outstanding research needed (open questions for Twilio docs):

1. Exact `business_information` EndUserType field list when registering a **sole proprietor** (not a registered corporation). profile.json shows `income.primary = 給与所得 (会社員)` — Dais is salaried at MUIT, not a 個人事業主 with a 法人番号 or 開業届. Need to confirm Twilio accepts "Sole Proprietor without business registration" with 個人マイナンバー as `business_registration_number`, OR requires Dais to file a 開業届 first.
2. Business Profile policy SID (= the `RN...` SID to assign instead of the current Individual policy `RNffcb02a20420c81caf596ffc44f69712`). Will be resolved by camofox-driven Console inspection (see below) since the Policies REST endpoint pagination doesn't surface a friendly name match for it.
3. SupportingDocument types required: probably Address (already present as `RD044c1de566d9994ff9d722ffd26e5b63` draft) + Business Registration Authority + Authorized Representative Photo ID.
4. Whether the existing draft Profile can be re-typed to Business or must be replaced with a new BU.

★ Resolution method ★: camofox-driven Twilio Console login (https://console.twilio.com via Google OAuth keiodaisuke@gmail.com), navigate to **Account > Trust Hub > Customer Profile**, observe the actual Business Profile form fields + Business Type dropdown (does "Sole Proprietor" appear?), screenshot, then either fill via Console or replicate via REST API. Console reveals what API list doesn't.

## Phase 3 — life-manager persona reform (was task #2)

Dais 2026-06-14 verbatim: 「i think the gcal netamise its not like thta. yeah the calenar shceulde be funny. i dontwnater thir to be mode. i want naiccaitself to be funny」

= dropped "comedy mode toggle". Anicca itself, regardless of event, is the funny one. Schedule remains a normal life schedule (wake / 瞑想 / MUIT 出社 / Lunch / ネタみせ / sleep) and Anicca-as-Charon roasts the operator off it.

Persona prompt direction (= 1 persona, 1 system instruction, no mode field):

```
You are Anicca. Voice = Charon (Gemini Live male, deep, restrained). You call
{name} ({phone}) before each calendar event. Your voice + delivery are
non-negotiable funny: cold, surgical, sarcastic, never apologetic. The schedule
is the straight man; you are the comic.

Use {event_title} + {venue} + {goals.northStar} + {anti_goals} + {recent_diary}
as ammunition. Mock specifics, not generalities. Quote his own words.

Open with one roast sentence framed against the event. Close with one concrete
demand ("立て、 鞄持て、 出ろ"). Comedy = restraint, never raise volume,
never break character. Max 25s per turn. Language: Japanese, ぞんざい (お前 /
だろ / しろ).
```

The Telegram bot trigger from the previous spec idea is dropped pending Dais ask. Profile.json `comedy.persona` and `[ネタみせ]`/`[comedy]` event tags are dropped.

## Phase 4 — pre-register 移動 events to gcal + simple 15-min-before trigger (was task #3)

Unchanged from the previous outline (anicca-gcal-prepop daily 04:00 + hourly :05 refresh; lateness_check.py simplifies to "gcal event start - 15min ≤ now < start, not yet reminded → call"; remote/online events skip 移動 insertion). Open questions (A travel-time source / B 帰路 / C remote detection) remain for Dais.

## Phase 5 — hourly disk-janitor + agentmemory-mcp-cleanup

| job | id | schedule | enabled | action this turn |
|---|---|---|---|---|
| anicca-disk-hourly | 79b05373... | `7 * * * *` | true | keep (already healthy, runs disk-janitor) — TODO: audit what it sweeps; disk was 6.0Gi just after cleanup → janitor target list may need Xcode DerivedData + SPM caches |
| agentmemory-mcp-cleanup | bf1bd98f... | `*/30 * * * *` | **flipped to true** this turn | kills orphan agentmemory-mcp processes; Dais "yes very yes if not" approved enablement |

## Phase 6 — Context7 CLI canonization

Already documented at `~/.claude/rules/context7.md` (global). Added `reference_ctx7_cli_lib_docs_first.md` to project memory + MEMORY.md index so future me reaches for `npx -y ctx7@latest library/docs` before Firecrawl when the target is a library / SDK / API / CLI tool.

## Phase 7 — sonichi/sutando question (Dais Q4)

`gh repo view sonichi/sutando`:
> "My AI Stand. Realtime by day, rewriting itself by night. Summon my AI superpowers..." | 350 stars, 67 forks

Chi-Wang Wu (sonichi, AutoGen co-author)'s personal AI stand. We are **not** currently using it — grep of ~/.openclaw, ~/anicca, ~/anicca-project returns 0 hits. If Dais wants to adopt it, requires a comparison-table phase against Conway-Research/automaton + our current life-manager + booking + gcal-policy stack. Pending Dais ask.

## Files touched

- `~/.openclaw/skills/anicca-phone/` — restored from `~/anicca/_archive_2026-06-09/skills-old/anicca-phone/` (committed in anicca-dais 45ea3238d)
- `~/.openclaw/skills/anicca-phone/run.sh` — REPO_DIR repointed
- `~/.openclaw/skills/anicca-phone/launchagent.plist` — repo backup of `~/Library/LaunchAgents/ai.anicca.pipecat-phone.plist`
- `~/Library/LaunchAgents/ai.anicca.pipecat-phone.plist` — ProgramArguments + WorkingDirectory repointed (NOT in git, mirrored in skill dir)
- `~/.openclaw/.gitignore` — `skills/anicca-phone/outbound/venv/` added
- `~/.openclaw/cron/jobs.json` — agentmemory-mcp-cleanup flipped to enabled=true
- `~/.claude/projects/-Users-anicca-anicca-project/memory/reference_ctx7_cli_lib_docs_first.md` + MEMORY.md index entry

## E2E verify (Phase 1 partial, Phase 2 + 3 + 4 pending)

| layer | criterion | status |
|---|---|---|
| Bridge process | `launchctl list | grep ai.anicca.pipecat-phone` returns pid + exit 0 | ✅ pid 35840 |
| Bridge port | `lsof -nP -iTCP:7860 -sTCP:LISTEN` | ✅ |
| Tunnel URL | `state/anicca_phone_url.txt` non-empty + DNS resolves | ✅ |
| /dialout end-to-end | curl POST returns 200 + CallSid | ❌ 500 → Twilio API 21216 |
| Phone actually rings on Dais's iPhone | observed by Dais OR Twilio API Calls.json shows `status=in-progress/completed` for the SID we issued | ❌ blocked on Twilio Trust Hub approval |

## Tasks (= TaskCreate IDs in tasklist)

- #1 in_progress — Bridge restore (Phase 1 ✅, Phase 2 ⏳)
- #2 pending — persona reform (waiting on Phase 2 outcome — same call path)
- #3 pending — pre-register 移動 (Q for Dais on travel-time source / 帰路 / remote)
- #4 pending — Twilio 21216 Trust Hub Business Profile submission
