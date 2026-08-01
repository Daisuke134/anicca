---
name: apply-to-funder
description: Use when preparing, previewing, submitting, or tracking an accelerator, grant, VC, angel, or fundraising application for Life Manager.
---

# Apply to Funder

## Core principle

Every new application is a projection of the repository-owned Life Manager context, the funder's fresh
official evidence, and the exact preview digest. Old OpenClaw application kits are migration input or
submission history, never authority.

**REQUIRED BACKGROUND:** Use `building-agents` for semantic agent decisions and deterministic bookkeeping.

## Required sources

Read these before preparing an answer:

1. `.agents/startup-context.json` for product, company, links, claims, freshness, and forbidden values.
2. `.agents/product-marketing-context.md` for audience, pain, positioning, and voice.
3. `fundraising/application-kit/` for the generated canonical narrative.
4. `fundraising/funders/<id>.json` for program-only facts and official sources.

Do not take current facts from `~/.openclaw/identity/application-kit`, old `yc-w26.json`, submitted
history, dashboards, or remembered answers.

## Workflow

1. Verify the program's official page, deadline, eligibility, terms, and requested media today.
2. Update only program evidence in `fundraising/funders/<id>.json`; never duplicate product/company facts.
3. Run `npm run audit:startup-context`.
4. Run `npm run build:fundraising-kit` and require a clean second build.
5. Use the model to adapt answers to the actual questions and limits. Preserve exact facts and evidence.
6. Run `npm run preview:funder -- --funder <id>`.
7. Resolve every blocker. Bind any submit payload to both `context_digest` and `application_digest`.
8. Submit through the existing CloakBrowser daily-driver only when a repository submit command exists and
   all gates pass. Capture the completion page, confirmation message, ledger entry, and Telegram report.

## Fail-closed gates

Stop before browser mutation when any of these is true:

- context or program evidence is stale;
- product is not Life Manager, or an old product/homepage/repository appears;
- a claim lacks current evidence;
- requested demo or founder video is unverified, missing, or violates the program's instructions;
- preview and submit digests differ;
- the artifact contains private email, phone, address, credential, or an unresolved placeholder.

Company name `Anicca` is allowed only for a question whose purpose is `company_legal_name`.

## Current implementation boundary

This repository currently provides audit, kit build, and preview. It does **not** yet provide a submit
command. `submit_allowed: false` means do not improvise with an old external submit script. The submit
adapter is completed later in the ordered master spec, after media and field-level evidence are verified.

## Quick reference

| Need | Command / source |
|---|---|
| Verify startup facts | `npm run audit:startup-context` |
| Rebuild canonical kit | `npm run build:fundraising-kit` |
| Preview one program | `npm run preview:funder -- --funder <id>` |
| Product truth | `.agents/startup-context.json` |
| Program truth | official page + `fundraising/funders/<id>.json` |

## Common mistakes

- HTTP 200 alone does not prove the page is Life Manager; verify identity text.
- A signed browser payload can still contain the wrong product; semantic context binding remains required.
- A historical successful submission is evidence of that submission, not permission to reuse stale answers.
- Missing media must stay a blocker; never substitute an old Anicca video.
