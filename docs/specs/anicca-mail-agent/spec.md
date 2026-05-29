# Feature Specification — Anicca Autonomous Mail Agent

**Feature branch:** `feat/anicca-mail-agent`
**Version:** 0.1.0
**Date:** 2026-05-29
**Status:** DRAFT (Phase 2 of SDD workflow)
**Constitution:** Subject to `.specify/memory/constitution.md` v2.0.0

---

## Why This Feature Exists

Dais (the owner) embodies "Satoshi mode" — he is the executor of NEVER.
Today his inbox interrupts him several times an hour and a non-trivial
fraction of those mails require concrete autonomous action (book an
appointment, fix a billing page, fill a KYC form, click a safety-check
link, escalate a vendor blocker).

Anicca must handle **100% of Dais's inbox** end-to-end, with no human
in the loop except for cases requiring physical signature, biometric,
or a code only Dais can read off his phone.

The current `anicca-mail-auto-reply` skill has documented bugs (see
`/Users/anicca/anicca-project/.cursor/plans/anicca-autonomous-action-agent-spec.md`
§11 "既存 mail-auto-reply の 7 バグ"). Fixing those bugs is a prerequisite,
not the feature itself.

The feature is: **Anicca autonomously classifies every incoming mail
into one of 5 categories and executes the appropriate end-to-end behavior,
verified by view-side public state, never claiming completion on API
200 OK alone.**

---

## User Scenarios (Prioritized)

### P1 — Silent Archive (`triage4 = "no"`)

**As** Dais
**I want** promotional / receipt / no-reply / build-notification mails
**To** disappear from my inbox without ever waking me
**Because** they have zero actionable content for me.

### P1 — Reply With Imagination (`triage4 = "email"`, no action chain)

**As** Dais
**I want** vendor-support / KYC / customer-service mails
**To** be answered by Anicca using my `profile.json` facts (legal name,
address, business email, wallet description, income source, JP phone)
**Because** my answer is deterministic from those facts and a delay
costs me money or trust.

### P1 — Reply + Real Action (`triage4 = "email"` + browser action)

**As** Dais
**I want** booking requests, safety-check links, application forms
**To** be completed end-to-end (browser, form-fill, submit) and confirmed
back to the original sender, with the public state verified
**Because** the value of these tasks is the action, not the reply.

### P2 — Notify Only (`triage4 = "notify"`)

**As** Dais
**I want** Apple-Dev-expiry, Railway-crash, Supabase-quota alerts
**To** stay in my inbox AND surface to Slack `#inbox`
**Because** I want to be informed without being interrupted, and I
may want to scroll the original mail myself.

### P3 — Ask For Help (`triage4 = "email"` + multi-agent escalation)

**As** Dais
**I want** mails describing technically ambiguous failures (e.g., Uber's
"format-invalid" error) **NOT** to be answered with a guess
**Because** a wrong guess wastes my vendor relationship.
**Instead** Anicca consults Codex / Gemini / (eventually me) before
replying, and the reply cites the resolved cause.

---

## Acceptance Scenarios

### AS-1 (P1 archive) — Self-sent promo

> **Given** a mail from `${OSS_USER_EMAIL}` to `${OSS_USER_EMAIL}`
> with subject "🎁 [TC-1] EXCLUSIVE OFFER - Weekend Sale 50% off promotion"
> **When** Anicca's heartbeat fires and `anicca-mail-auto-reply/run.sh` processes it
> **Then** within 60 seconds the thread's `labelIds` MUST NOT include `INBOX`,
> AND no reply mail exists in the `Sent` folder,
> AND no Slack post references the thread.

### AS-2 (P2 notify) — Apple Dev expiry alert

> **Given** a mail simulating `developer@apple.com` with subject containing
> "Apple Developer Program is expiring 06-02"
> **When** Anicca processes it
> **Then** the thread's `labelIds` MUST still include `INBOX`,
> AND Slack `#inbox` MUST contain a post referencing the thread,
> AND no reply mail exists.

### AS-3 (P1 reply-imagine) — SBI VC KYC

> **Given** a mail simulating `sbivcsupport@sbivc.co.jp` whose body lists
> KYC fields (受取人氏名 / 住所 / ウォレット名 / 所在国 / 出庫目的 / 資金源)
> **When** Anicca processes it
> **Then** a reply MUST be sent in-thread,
> AND the reply body MUST contain ALL of: `${OSS_USER_NAME_JP}`, `${OSS_USER_ADDRESS}`,
> `anicca`, `日本`, a phrase describing the wallet purpose, `給与`,
> AND the reply body MUST NOT contain ANY of: `[記入]`, `[fill in]`,
> `[TBD]`, `on behalf of Daisuke`, `+1 (336)`, `+1 336`,
> AND the signature MUST be `Anicca` alone with `${OSS_USER_PHONE}` and
> `contact@aniccaai.com`.

### AS-4 (P1 reply+action) — Booking request

> **Given** a mail asking Anicca to book a clinic appointment with a
> specific menu (e.g., ヒゲ脱毛 5 回目) at a specific time (来週水 14:00)
> **When** Anicca processes it
> **Then** a camofox browser session MUST navigate to the clinic's
> official booking URL,
> AND fill the form using profile.json values,
> AND submit the booking,
> AND verify the confirmation page via `verify-public-state.sh` (regex
> matching "予約完了" or equivalent + a captured booking number),
> AND send a reply to the original mail containing the booking number,
> AND register a follow-up task in `tasks.json` for receipt-mail verification.

### AS-5 (P3 ask-for-help) — Uber format-invalid

> **Given** a mail simulating Mina @ Uber reporting
> "ERROR-7283X-license-format-invalid"
> **When** Anicca processes it
> **Then** Anicca MUST invoke `/help-from-codex` with the error code and
> snapshot context,
> AND apply the returned advisory (e.g., adding PDF metadata),
> AND re-upload via camofox,
> AND verify the new state via `verify-public-state.sh`,
> AND send a reply citing the resolved cause (NOT a guess),
> AND log a `.learnings/LEARNINGS.md` entry with `Pattern-Key:
> uber.license.metadata-required` (or whatever the resolved key is) and
> `Round: 3` (codex).

---

## Edge Cases

| ID | Edge case | Required behavior |
|---|---|---|
| E1 | Self-sent mail with a promo subject (Anicca's own test mails) | Archive (SELF_FROM + SKIP_SUBJECT both fire). |
| E2 | Self-sent mail with a non-promo subject (e.g., Dais's "book appointment" command in AS-4) | Treat as if from external sender — process the action. |
| E3 | Mail with prompt injection in body ("ignore previous instructions...") | `triage4 = "no"`, log to `.learnings/ERRORS.md` Pattern-Key `injection.attempt`, post Slack `#alert`, no reply. |
| E4 | Mail to which Anicca already replied within 48h | `triage4 = "no"` reason `we_replied`. |
| E5 | Mail referencing Power Of Free (`live_entry@yahoo.co.jp` or 出演 keywords toward that venue) | Permanent BAN per `profile.lateness.stakeholders[2]` — `triage4 = "no"`, no reply, no archive (leave in inbox for Dais audit). |
| E6 | Booking-form action fails because clinic site requires CAPTCHA | Round 1 retry → Round 2 alternative URL → Round 3 codex → Round 4 gemini → Round 5 Slack Dais with screenshot. |
| E7 | Anicca cannot find profile field needed for reply | `wait-for-slack-input.sh` with `regex` for the expected format. Save the answer to `profile.json` for next time. |

---

## Functional Requirements

| ID | Requirement |
|---|---|
| FR-001 | Anicca SHALL fetch all inbox mail with `newer_than:WINDOW_HOURS` on every beat. WINDOW_HOURS is auto-computed by `compute-window.sh` (default 2h, gap-aware). |
| FR-002 | Anicca SHALL classify each mail into exactly one of `{"no", "email", "notify", "question"}` per EAIA schema. |
| FR-003 | For `triage4 = "no"`, Anicca SHALL remove the `INBOX` label IFF the reason matches `SKIP_FROM|SKIP_SUBJECT|voicemail|extra_(from|subject)|self_promo`. SELF_FROM with non-promo subject MUST stay in INBOX. |
| FR-004 | For `triage4 = "notify"`, Anicca SHALL keep INBOX label AND post a single-line summary to Slack `#inbox` (channel id from `${SLACK_REPORT_CHANNEL}`). |
| FR-005 | For `triage4 = "email"`, Anicca SHALL draft a reply, run the `verifyDraft` safety scan, and send via `gog gmail send --reply-to-message-id <mid>` IFF safety passes. |
| FR-006 | The safety scan MUST hard-block any draft containing `[記入]`, `[fill in]`, `[name]`, `[NAME]`, `{}`, `[TBD]`, `[未定]`, or the substring `on behalf of Daisuke`, or the substrings `+1 (336)` / `+1 336`. |
| FR-007 | The signature of any sent reply MUST be `Anicca` alone, with `contact@aniccaai.com` and `${OSS_USER_PHONE}`, EXCEPT when `thread.from` matches `workEmail` (MUIT/上司 path) — then signature is `${OSS_USER_NAME_JP}`. |
| FR-008 | For `triage4 = "email"` mails that demand a real-world action (FR-010), Anicca SHALL execute the action chain BEFORE sending the reply. The reply MUST reference the verified action outcome (booking number, screenshot, task id). |
| FR-009 | For `triage4 = "question"`, Anicca SHALL post to Slack `#inbox` AND register a `tasks.json` task with `metadata.skill = "ask-dais"` and a `regex` for the expected reply format. |
| FR-010 | An action chain MUST conclude with `verify-public-state.sh` whose URL is the public, sender-observable view of the result, AND whose `expected_regex` matches the outcome (booking number, page-state string, file presence, etc.). `tasks.json status = done` is forbidden until verify exits 0. |
| FR-011 | If verify exits non-zero, Anicca SHALL enter the Multi-Agent Help Escalation Ladder (Constitution A2.3), Round 1 → 6. The mail-auto-reply SHALL NOT silently retry the action with the same approach more than once. |
| FR-012 | Every successful Round MUST append a `[LRN-YYYYMMDD-XXX]` entry to `.learnings/LEARNINGS.md` with `Pattern-Key` and `Round`. Every failed Round MUST append an `[ERR-YYYYMMDD-XXX]` entry to `.learnings/ERRORS.md`. |
| FR-013 | Two `.learnings/ERRORS.md` entries sharing a `Pattern-Key` MUST trigger automatic skill extraction (create `~/.openclaw/skills/<derived-name>/SKILL.md` + `scripts/run.sh`) on the next beat. |
| FR-014 | Mail from `live_entry@yahoo.co.jp` or matching the Power-Of-Free profile pattern MUST never receive a reply nor be archived. |
| FR-015 | Mail containing prompt-injection patterns (Anthropic + agentic-inbox detector merged) MUST set `triage4 = "no"` AND post to Slack `#alert` with the thread id AND log Pattern-Key `injection.attempt`. |
| FR-016 | The `anicca-mail-auto-reply/run.sh` MUST run on every heartbeat AND complete in ≤ 60 seconds per mail (camofox actions excluded — those run async via the picked task). |
| FR-017 | Test harness (`anicca-mail-test-harness`) MUST be able to inject all 5 acceptance scenarios as actual `gog gmail send` to `${OSS_TEST_RECIPIENT}` AND verify outcomes programmatically. |
| FR-018 | The harness MUST emit a `test-report-{TS}.json` with `{pass, fail, skip, total, failures: []}` and a symlink `latest.json`. |

---

## Key Entities

| Entity | Definition |
|---|---|
| **Mail thread** | A Gmail thread identified by `threadId`. Contains 1..N messages. Carries `labelIds`. |
| **Triage4 value** | `Literal["no", "email", "notify", "question"]` (EAIA schema, `eaia/eaia/schemas.py:20-24`). |
| **Reply draft** | A UTF-8 body string ≤ 2500 chars, ≥ 30 chars, containing zero forbidden substrings. |
| **Action chain** | An ordered list of browser / system steps (camofox tabs, form fills, submits) that culminates in `verify-public-state.sh` exit 0. |
| **Help round** | An attempt-with-different-tool: 1=Anicca-same / 2=Anicca-different / 3=codex / 4=gemini / 5=Dais / 6=forever-retry. |
| **Pattern-Key** | A stable dot-separated identifier for a recurring failure or success pattern, e.g., `uber.license.metadata-required`. |
| **Test case** | A YAML file in `~/.openclaw/skills/_shared/anicca-mail-test-harness/test-cases/TC-<N>.yaml` with `input` (from/to/subject/body) + `expected` (triage4 + actions + verify rules). |
| **Test report** | `reports/test-report-{TS}.json` recording per-case verdict and overall counts. |

---

## Success Criteria (measurable, technology-agnostic)

| ID | Criterion | How measured |
|---|---|---|
| SC-1 | 5/5 acceptance scenarios pass on a fresh test harness run. | `reports/latest.json` shows `fail=0 skip=0 total=5`. |
| SC-2 | For 7 consecutive days, Dais's manual inbox-actions count is 0 (counted via Gmail audit log + Dais self-report). | Slack `#metrics` weekly summary. |
| SC-3 | Mean time from mail receipt to Anicca's terminal action (archive / notify / reply / verified action) ≤ 60 minutes. | `gog gmail` timestamp - heartbeat completion timestamp. |
| SC-4 | Zero false-positive sends to Power-Of-Free senders (FR-014). | `.learnings/ERRORS.md` Pattern-Key `policy.power-of-free.contact` count = 0. |
| SC-5 | Zero `[記入]`-shaped placeholders escape the safety scan into a real Sent message. | gog gmail search over `Sent` for the forbidden substrings = 0. |
| SC-6 | At least one Pattern-Key reaches Recurrence-Count ≥ 2 within 30 days AND triggers automatic skill extraction. | `~/.openclaw/skills/` diff shows new skill folder; commit message cites the extracting Pattern-Key. |
| SC-7 | The mail agent operates equivalently under both `claude-anicca` and `openclaw-anicca` harnesses. | Test harness run with `ANICCA_HARNESS=openclaw-anicca` env produces identical `reports/latest.json` outcomes. |

---

## Out of Scope (for this feature)

- Voice / phone / Discord / Telegram bridges (separate features).
- Outbound cold email / marketing automation.
- Calendar event creation directly from mail (handled by a separate `gcal-from-mail` feature).
- Spam learning (relies on Gmail's built-in classifier; Anicca only adds business rules on top).
- Multi-account inbox (single `${GOG_ACCOUNT}` only in v0.1.0).

---

## Open Questions / Clarifications Needed

None blocking. (Phase 3 clarification ran inline above via Edge Cases and FRs.)

---

## Citations

See `.specify/memory/constitution.md` Article 7 "Citations" for the source
repository list (sutando / automaton / self-improving-agent / Anthropic
multi-agent blog / EAIA / inbox-zero / vellum / agentic-inbox).
