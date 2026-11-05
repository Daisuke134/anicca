# Observability for Agent Loops — Langfuse Phase 0 Guide

Why: a loop that cannot observe its own output and state is broken by
definition. Evaluation turns "seems fine" into a binary fact: did the
expected artifact arrive, or not? This guide is the generalized Phase 0 of
a researched adoption plan (tool comparison of Langfuse, Opik, LangSmith,
Phoenix, Helicone and others, from official documentation, November 2026).

**Status honesty**: the *research and plan* are complete; the *adoption* is
in progress. Treat this guide as a verified plan, not a completed install.
The trace-design rules below are from Langfuse's official best-practices
documentation.

## Why Langfuse (one recommendation, with reasons)

- Core is MIT-licensed; the vendor states all core features and APIs are
  unlimited in the self-hosted OSS build, so the steady state costs $0.
- Framework-agnostic ingestion — Python/JS SDK, OpenTelemetry endpoint, and
  a REST API — so hand-rolled cron loops can emit "one run = one trace"
  without adopting a framework.
- Evaluations run against production traces (LLM-as-a-judge, code
  evaluators, human annotation queues, dataset experiments) in the OSS
  build.
- Threshold alerts on observations and scores, including *no-data*
  detection, to Slack / PagerDuty / Webhook / GitHub Actions; unlimited in
  the self-hosted build.
- Per-generation cost tracking (model + token usage → automatic cost), so
  "cost per loop" and "revenue per loop" can be joined — the tokens-to-money
  ratio per loop.
- An official MCP server, CLI, and agent skill, so agents can query their
  own observability data programmatically.

Runner-up: Opik (Apache-2.0, full self-host). Langfuse won on the lighter
single-machine Docker Compose path and the cost/Metrics API fit.

## Phase 0 — prove it on the free cloud tier (days, not weeks)

Goal: one loop instrumented end-to-end — traces visible, a binary
artifact-arrival evaluation scoring production runs, alerts firing on
failure and on silence — before any self-hosting.

1. Sign up at the vendor's cloud with an **agent-owned email + password**
   (not a human's SSO identity). Generate the password agent-side; store it
   in the shared vault only. Complete email verification from the agent
   inbox.
2. Create one organization and one project (start with a single project for
   your highest-value loop family, e.g. `distribution`).
3. Issue project API keys; store them in the vault. On the worker side,
   reference them only via environment variables: `LANGFUSE_HOST`,
   `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`. Variable names go in
   runbooks; values never go in files or chats.
4. Instrument ONE loop (design rules below) and confirm a test trace renders
   in the UI.
5. Add the binary code evaluator `artifact_delivered` (score 1 iff the
   run's expected artifact — public URL, ledger row, listing — verifiably
   exists at scoring time; else 0) and the free tier's alert slots:
   (a) `artifact_delivered` mean below threshold, (b) no-data alert on the
   loop's trace name (silence is a failure, not an absence of one).
   Deliberately fail a run and confirm the alert arrives.
6. Run 1–2 weeks and *measure* unit consumption per day. That measurement
   — not an estimate — decides Phase 1 timing.

## Trace design rules (vendor's official best practices)

- **One run = one trace**, and trace/observation names are a stable API:
  evaluators, dashboards, and saved filters reference them, so renaming
  silently detaches everything. Dynamic values (order IDs, retry counts)
  go in metadata, never in names.
- Record LLM calls as `generation` (always with model name and token usage
  — the precondition for automatic cost) and tool calls as `tool`. Do not
  collapse a whole agent loop into a single generation, or per-step
  decisions, tokens, and cost become invisible.
- Score the outcome, not the effort: the primary score is artifact arrival
  (binary), with cost and latency as secondary series.

## Phase 1 — self-host the steady state (plan, unverified)

When measured consumption approaches the free cloud cap (50,000
units/month on the Hobby tier at research time), move to the official
Docker Compose self-host on your own VM: same organization/project/key
shape, unlimited usage and alerts, reachability limited to your private
network, backups and pinned-version upgrades in the runbook. Check the
machine's free CPU/RAM/disk against the vendor's documented footprint
first; if it does not fit, stay on cloud rather than squeezing production
loops. Full official procedure:
https://langfuse.com/self-hosting/deployment/docker-compose

## Sources

- Langfuse README — https://github.com/langfuse/langfuse
- Trace design best practices — https://langfuse.com/docs/observability/best-practices.md
- Alerts — https://langfuse.com/docs/observability/features/alerts
- Licensing clarifications — https://langfuse.com/resources/engineering/clarifications
- Self-hosting (Docker Compose) — https://langfuse.com/self-hosting/deployment/docker-compose
