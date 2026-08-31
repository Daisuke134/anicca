# Title

Mr.bot

## One-line Summary

An open-source, 24/7 AI money printer that finds paid opportunities, performs bounded work, and asks only for the human 1%.

## Problem

People share many isolated ways to use Claude, Codex, and other AI systems to make money through bounties, gigs, apps, content, and online work. What is missing is a public, reproducible end-to-end agent system that continuously discovers opportunities, evaluates them, performs bounded work, pauses only at a genuine human boundary, resumes after an answer, submits or delivers once, and follows the result to an official receipt.

## Solution

Mr.bot turns paid opportunities into persistent, isolated workrooms. Its provider-neutral architecture can expand across the public Web, X, GitHub, mail, Lancers, Mercor, and other marketplace URLs; the currently verified scout path is the public Web. Citation-backed public URLs enter a durable Railway Postgres queue, where the dedicated `money-printer-worker` qualifies them.

The person does not supervise ordinary agent turns. When identity, authority, private payment information, judgment, or a real-world action is genuinely required, the workroom contract defines one prepared `Needs You` task. The intended flow is a versioned answer in the same Dashboard followed by continuation from that workroom; live creation/answer/resume E2E is pending.

The currently verified Lancers evidence is an application receipt for project `5593484` / proposal `27863414`, not revenue. `Paid & verified` remains zero until an independently verified payment receipt exists.

## Why This Matters

AI earning advice is easy to publish but difficult to reproduce. Mr.bot makes the process inspectable and open source: opportunity source, requirements, agent work, human handoff, external effect, cost, and provider receipt are visible in one system. Applications, offers, opportunity value, and model claims are not counted as revenue; only official payment evidence is.

## Official WebMCP Questions

### Why this use case is a strong fit for WebMCP

Money Printer is a strong WebMCP fit because earning work spans many turns while still containing moments when a person and an agent must share exact context: approving a consequential public delivery, providing identity-bound or payout information, making a genuine judgment, or performing a physical action. WebMCP turns the live Dashboard into a shared control surface for that work.

The page exposes typed tools for the current board and workrooms: `inspect_money_printer`, `add_opportunity`, `inspect_workroom`, `inspect_next_human_task`, and the state-dependent `record_human_answer`. These tools complement the 24/7 Railway worker; they do not replace the backend runtime. The same durable state is rendered for the person and read or updated by the site tools.

### How it creates a better user experience

Without WebMCP, an agent must infer Mr.bot's interface from pixels and DOM controls, while the person has to translate state between a dashboard, chat, and external opportunity sites. With WebMCP, the intended flow is a typed read of the board, a visible workroom inspection, and a versioned human answer only when a genuine boundary is open. The person can inspect the same state and evidence instead of supervising every ordinary turn.

The deployed judge tenant is isolated and blocks external application, delivery, payment, and money effects. Its current Lancers receipt is read-only, and an application is never presented as payment. Live ChatGPT/Chrome discovery and live creation/answer/resume E2E are pending rather than being implied by the UI contract.

### What people and agents can do together that was difficult before

Mr.bot divides real earning work according to what each side does best. The agent handles discovery, qualification, research, planning, creation, execution, recovery, submission, and receipt reconciliation when the relevant capability and authority are available. The person contributes identity, authority, judgment, payment information, or physical action when one of those is genuinely required.

Both sides work from the same durable workroom state. In the verified current slice, a cited Web scout cycle completed on retry, state survived a worker restart, and the system preserves a read-only Lancers application receipt with replay duplicate count zero. The broader external-submit and human-resume path remains evidence to collect.

### How WebMCP was implemented

The top-level `/money-printer` page registers focused tools with `document.modelContext.registerTool()`. The currently registered set is:

- `inspect_money_printer` — read metrics, board columns, and safe recent activity
- `add_opportunity` — add one public HTTPS opportunity to the durable queue with an idempotency fence
- `inspect_workroom` — read the selected opportunity, job, and receipt timeline
- `inspect_next_human_task` — read the oldest exact open human task
- `record_human_answer` — record a versioned answer and resume the same job when a task is open

Each tool uses the same server-validated state as the visible UI. Revision checks, tenant boundaries, idempotency, and effect fences protect internal writes; the zero-login judge tenant has no external-effect authority. No separate receipt-writing tool is registered; receipt evidence is read through the workroom projection.

## How We Used AI

- Model-led opportunity qualification using reward, deadline, eligibility, required work, cost, and risk
- A provider-neutral capability worker that selects browser, web, GitHub, code, file, and media actions from environmental feedback
- Durable state and worker restart recovery for continuation across turns; live creation/answer/resume E2E and three-cycle proof remain pending
- Minimal-human task generation at genuine identity, authority, private-fact, judgment, or real-world boundaries
- Failure recovery and receipt reconciliation without blindly repeating uncertain external effects

## How We Used Codex

Codex was used to research WebMCP and the official challenge contract, inspect and extend the existing Mr.bot codebase, design the WebMCP tool surface, implement the Dashboard and runtime integration, and prepare the public repository and submission materials. ChatGPT and Chrome client-discovery E2E tests are still pending, so this draft does not claim that those tests are complete.

## Key Features

- Citation-grounded public-Web scouting and a durable opportunity queue (verified current path)
- Provider-neutral expansion path for X, GitHub, mail, Lancers, Mercor, and other public marketplace URLs (architecture, not current live-discovery proof)
- Bounded agent workrooms and one durable board for opportunities, agents, artifacts, human tasks, effects, and receipts
- `Needs You` questions issued one at a time at genuine human boundaries; live creation/answer/resume E2E is pending
- Effect fences, idempotency, uncertain-effect quarantine, and official readback
- Verified-money ledger that distinguishes activity, applications, and opportunity value from received money
- Five top-level WebMCP tools backed by the same domain state as the human UI

## Architecture

- Netlify: responsive Mr.bot Dashboard at `/money-printer` and top-level WebMCP registration
- Railway `money-printer-worker`: running cloud scout/worker process with durable queue and restart-stable state
- Durable state: opportunities, workrooms, agent events, human tasks, effects, and receipts
- Existing agent runner: provider-neutral model execution with browser, web, GitHub, code, file, and media tools
- Provider adapters: read-only Lancers application receipt readback; Mercor and additional marketplace adapters are expansion paths, not current live-discovery proof

## Testing Instructions

This is the safe judge path for the live guest tenant; no login, payment, API key, or private Mr.bot account is required.

1. Open `https://aniccaai.com/money-printer` in ChatGPT's desktop in-app browser.
2. Confirm the banner says `Judge guest — external effects disabled`.
3. Ask: `List the Site tools exposed by this page. Call inspect_money_printer, summarize the board and money truth, then inspect one qualified workroom. Do not perform an external application, delivery, payment, or money effect.`
4. Confirm the structured response matches the visible board. `Paid & verified` may be empty even when the read-only Lancers application receipt exists.
5. Optional internal write: ask the agent to use `add_opportunity` for one public paid-opportunity URL, then inspect its workroom and show the visible state change. Stop at qualification.

Chrome fallback: use Chrome 149 or newer, enable `chrome://flags/#enable-webmcp-testing`, relaunch Chrome, and open the same URL. The implementation is top-level imperative `document.modelContext.registerTool()` and does not depend on an iframe or declarative markup.

Evidence status: ChatGPT tool discovery E2E: pending; Chrome tool discovery E2E: pending; live creation/answer/resume E2E: pending.

## Public Demo Link

`https://aniccaai.com/money-printer`

Status: the Netlify page is live and this is the canonical URL. Railway `money-printer-worker` is running. One manual cited Web scout cycle completed on retry, and a worker restart preserved jobs, opportunities, and receipts. Immutable final tag/deploy binding remains pending.

## Public Repository Link

`https://github.com/Daisuke134/life-manager`

License: MIT, visible in the public repository.

## Demo Video

Title: `Mr.bot — The 24/7 AI Money Printer`

Public YouTube URL: Pending — no public video URL exists yet.

Recording status: pending. The video must be under three minutes, use English audio or captions, and show the live product rather than the static mockup.

Planned proof sequence (not yet recorded):

1. Show the problem and the running Money Printer Dashboard.
2. Show a compatible client inspecting the page's registered WebMCP tools.
3. Show the cited Web scout and one workroom with durable state.
4. Show the safe internal opportunity mutation and visible state change.
5. Show one genuine `Needs You` task and, once live E2E is verified, the same workroom continuing after the answer.
6. Show the read-only Lancers application receipt for project `5593484` / proposal `27863414`, replay duplicate count zero, and `Paid & verified = 0`.

## Screenshot Shot List

All five real screenshots are pending; the static mockup is not evidence:

1. Full Money Printer Dashboard with multiple workrooms in different states
2. Compatible client's WebMCP Site tools and recent-call activity
3. Selected workroom with agent events and a real artifact
4. `Needs You` task with prepared context and one exact action
5. Provider receipt, duplicate count, cost, and verified-money view

## Submission Readiness Notes

Current status: the existing Mr.bot project is registered for the WebMCP Challenge. The canonical Netlify page is live, Railway `money-printer-worker` is running, the five-tool WebMCP registration is present, one manual cited Web scout cycle completed on retry, and restart preserved jobs, opportunities, and receipts. The verified provider evidence is Lancers project `5593484` / proposal `27863414` with replay duplicate count zero; it is an application, not revenue, and `Paid & verified` remains zero.

The four official criteria are WebMCP Leverage, Execution, Potential Impact, and Creativity & Ambition. Remaining evidence gaps are ChatGPT/Chrome tool discovery E2E, live creation/answer/resume E2E, two concurrent workrooms, three natural scout cycles, five real screenshots, a public under-three-minute video, and immutable final tag/deploy binding.

Devpost draft project: `https://devpost.com/software/life-manager-uny729` (project ID `1404362`). Live readback: registered for `webmcp`, `submitted_at: null`, `video_url: null`; the final Hackathon submission has not been sent.

## Known Limitations

- The `/money-printer` page is live, but ChatGPT and Chrome tool-discovery evidence has not been recorded.
- Live creation/answer/resume E2E, two concurrent workrooms, and three natural scout cycles remain unverified.
- The judge tenant cannot perform external application, delivery, payment, or money effects. The Lancers application receipt is read-only; `Paid & verified` remains zero without an independent payment receipt.
- No public demo video or screenshot packet exists yet, and immutable final tag/deploy binding is not verified.
- WebMCP tools are page/session-local; the hosted Mr.bot worker provides 24/7 continuation after the page closes.

## TODO Official Form Fields

- `28249` Submitter Type: Individual
- `28250` Country of residence: Japan
- `28252` App Status: Existing
- Existing update: Added the `/money-printer` guest route, provider-neutral projection, five top-level imperative WebMCP tools, durable workroom and human-task contracts, Railway worker/scout path, safe receipt projection, and tenant isolation during the challenge period. Current evidence is one cited Web scout cycle, restart-stable state, and a read-only Lancers application receipt; client, screenshot, video, and longer-run evidence remain pending.
- `28254` Live URL: `https://aniccaai.com/money-printer`
- Judge testing instructions: use the no-login read-only prompt in the Testing Instructions section; do not request external effects.
- `28256` Public Code Repo: `https://github.com/Daisuke134/life-manager`
- `28257` Tested WebMCP agents/clients: Pending — ChatGPT in-app browser E2E and Chrome WebMCP E2E.
- `28258` AI tools used: Codex and ChatGPT.
- `28259` Level of learning: Significant
- `28260` Career AI value: Yes
- Public YouTube URL: Pending — no public video URL exists yet.
