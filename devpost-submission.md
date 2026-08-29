# Title

Life Manager

## One-line Summary

An open-source, 24/7 AI money printer that finds paid opportunities, does the work, and asks you only for the human 1%.

## Problem

People share many isolated ways to use Claude, Codex, and other AI systems to make money through bounties, gigs, apps, content, and online work. What is missing is a public, reproducible end-to-end agent system that continuously discovers those opportunities, evaluates them, performs the work, pauses only at a genuine human boundary, resumes after the answer, submits or delivers once, and follows the result to an official receipt.

## Solution

Life Manager turns paid opportunities into persistent, isolated workrooms. A 24/7 entrepreneur agent searches X, the Web, GitHub, mail, and marketplaces, discovers freelance projects on Lancers and high-value AI roles on Mercor, and accepts any public bounty or marketplace URL. A bounded fleet of earning agents qualifies them, performs the work, recovers from transient failures, and continues until there is an externally verifiable outcome.

The person does not supervise agent turns. When identity, authority, private payment information, judgment, or a real-world action is genuinely required, Life Manager creates one prepared `Needs You` task. The person answers in the same WebMCP-enabled Dashboard, and the same workroom resumes automatically.

## Why This Matters

AI earning advice is easy to publish but difficult to reproduce. Life Manager makes the process inspectable and open source: opportunity source, requirements, agent work, human handoff, external effect, cost, and provider receipt are all visible in one system. Applications, offers, and model claims are not counted as revenue; only official payment evidence is.

## Official WebMCP Questions

### Why this use case is a strong fit for WebMCP

Money Printer runs autonomously across many turns, but real earning work still contains moments when a person and an agent must share exact context: approving a consequential public delivery, providing identity-bound or payout information, making a genuine judgment, or performing a physical action. WebMCP turns Life Manager's live Dashboard into a shared control surface. A compatible agent can inspect opportunities, open a workroom, revise a visible artifact, record one human answer, resume the work, and verify provider receipts through typed site tools instead of guessing at dashboard controls.

Every WebMCP action updates the same versioned state that the person sees. The page becomes the shared control plane for an autonomous earning system rather than a passive monitoring dashboard.

### How it creates a better user experience

Without WebMCP, an agent must infer Life Manager's interface from pixels and DOM controls, while the person has to translate state between a dashboard, chat, and external opportunity sites. With WebMCP, the agent uses typed tools to read and update the same visible workroom the person sees. The person receives one prepared `Needs You` card instead of supervising every turn, supplies the missing approval, identity, payout detail, or real-world action, and the earning agent resumes from the exact same state. This removes repeated navigation and context reconstruction, makes every handoff visible, and lets both sides verify the same delivery and payment evidence.

### What people and agents can do together that was difficult before

Life Manager lets people and agents divide real earning work according to what each does best. The agent handles discovery, qualification, research, planning, creation, execution, recovery, submission, and receipt reconciliation. The person contributes only identity, authority, judgment, payment information, or physical action when one of those is truly required. Both work from the same visible workroom, so the handoff is not a context-losing message; it is part of the durable work state.

Together they can pursue paid opportunities continuously with minimal human involvement while keeping human control at the moments that must remain human.

### How WebMCP was implemented

The top-level page registers focused tools with `document.modelContext.registerTool()`. The planned tool surface lets a compatible agent inspect the Money Printer, add an opportunity, inspect a workroom, revise an artifact, inspect the next human task, record an exact human answer, continue or pause work, and inspect the final receipt. Each tool calls the same server-validated domain functions as the visible UI, so every successful agent action immediately appears on the Dashboard. Server-side revision checks, spend limits, effect fences, and idempotency prevent stale updates, unauthorized effects, and duplicate submissions.

Final submission copy will name only tools and behavior verified in the deployed app.

## How We Used AI

- Model-led opportunity qualification based on reward, deadline, eligibility, required work, cost, and risk
- Tool-using earning agents that choose browser, web, GitHub, code, file, and media actions from environmental feedback
- Persistent continuation across multiple turns without human supervision
- Minimal-human task generation only at genuine identity, authority, private-fact, or real-world boundaries
- Failure recovery and receipt reconciliation without blindly repeating uncertain external effects

## How We Used Codex

Codex is used to research WebMCP and the official challenge contract, inspect and extend the existing Life Manager codebase, design the WebMCP tool surface, implement the Dashboard and runtime integration, test the deployed app in ChatGPT's in-app browser and Chrome, and prepare the public repository, demo, and submission materials. The final write-up will retain only build and test claims supported by repository history and runtime evidence.

## Key Features

- 24/7 general opportunity discovery across X, Web, GitHub, mail, Lancers, Mercor, and arbitrary marketplace URLs
- Bounded concurrent agent workrooms inspired by OpenAI Symphony
- One durable board for agents, people, artifacts, human tasks, effects, and receipts
- `Needs You` questions issued one at a time and only when human input is genuinely required
- Automatic continuation from the same workroom after an answer
- Effect fences, idempotency, uncertain-effect quarantine, and official readback
- Verified-money ledger that distinguishes activity from received money
- WebMCP tools backed by the same domain functions as the human UI

## Architecture

- Netlify: responsive Life Manager Dashboard and top-level WebMCP registration
- Existing Railway Node service: 24/7 scout, orchestration, claims, continuation, retry, and reconciliation
- Durable state: opportunities, workrooms, agent events, human tasks, effects, and receipts
- Existing agent runner: provider-neutral model execution with browser, web, GitHub, code, file, and media tools
- Provider adapters: Lancers application readback, Mercor application-step/human-interview state, and thin mechanical adapters for unfamiliar marketplaces when required

## Testing Instructions

Current target flow; replace each item with verified final instructions before submission:

1. Open `https://aniccaai.com/money-printer` in the latest ChatGPT desktop in-app browser.
2. Use GPT-5.6 Sol or Terra with Site tools enabled.
3. Ask: `Turn on my Money Printer. Do everything you can autonomously and ask me only when you genuinely need human input.`
4. Inspect the available Site tools and recent calls.
5. Follow one opportunity from discovery to workroom execution.
6. Answer one real `Needs You` task and verify automatic continuation.
7. Inspect the external-effect receipt and duplicate count.

Secondary test: Chrome 149+ with `chrome://flags/#enable-webmcp-testing` enabled.

## Public Demo Link

`https://aniccaai.com/money-printer`

Status: reachable existing Life Manager landing page. TODO: deploy the WebMCP Money Printer Dashboard and record immutable deploy SHA.

## Public Repository Link

`https://github.com/Daisuke134/life-manager`

License: MIT, visible in the public repository.

## Demo Video

Title: `Life Manager — The 24/7 AI Money Printer`

Public YouTube URL: TODO after verified recording and upload.

Outline, under three minutes:

1. Show the non-reproducible AI-money problem and running Dashboard.
2. Show ChatGPT discovering Life Manager's WebMCP Site tools.
3. Trace one real Lancers project from its public listing inside the recurring 24/7 product.
4. Show the earning agent complete the work.
5. Complete one genuine `Needs You` task.
6. Show automatic continuation, one fenced application, and official readback.
7. Show provider readback, duplicate zero, and verified-money truth.

## Screenshot Shot List

1. Full Money Printer Dashboard with multiple workrooms in different states
2. ChatGPT Site tools and recent-call activity
3. Selected workroom with agent events and a real artifact
4. `Needs You` task with prepared context and one exact action
5. Provider receipt, duplicate count, cost, and verified-money view

## Submission Readiness Notes

Current status: existing Life Manager project, registered for The WebMCP Challenge, with the WebMCP winning contract and submission draft prepared. Product implementation, final deployment, WebMCP E2E evidence, screenshots, and video remain incomplete. The final Devpost copy must be reconciled to the behavior of the submitted release.

Devpost draft project: `https://devpost.com/software/life-manager-uny729` (project ID `1404362`). Live readback confirms `submitted_at: null`; the final Hackathon submission has not been sent.

## Known Limitations

- The deployed `/lm` route does not yet contain the WebMCP Money Printer Dashboard.
- No final ChatGPT or Chrome WebMCP E2E receipt exists yet.
- No public demo video exists yet.
- No external earning result may be claimed until an official provider readback exists.
- WebMCP Site tools are page-local; the hosted Life Manager runtime provides 24/7 continuation after the page closes.

## TODO Official Form Fields

- Submitter Type: Individual
- Country: Japan
- App Status: Existing
- Existing update: TODO final verified summary of WebMCP work added during the challenge period
- Live URL: `https://aniccaai.com/money-printer` after verified WebMCP deployment
- Judge testing instructions: TODO final clean-browser steps and any credentials
- Public repo: `https://github.com/Daisuke134/life-manager`
- Tested clients: TODO final verified ChatGPT in-app browser and Chrome entries
- AI tools used: Codex and ChatGPT; add only other tools actually used
- Learning level: Significant
- Career AI value: Yes
- Public YouTube URL: TODO
