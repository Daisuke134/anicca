---
name: tiktok-content-creation-compliance
description: Review TikTok Shop seller and creator promotional content compliance using official TikTok Shop Seller University guidance. Use when an AI agent needs to check or revise a TikTok Shop video, LIVE, script, caption, hook, storyboard, exported video file, listing image, product claim, giveaway language, or AI-generated ad; decide whether content is permitted, risky, or prohibited; and catch misleading claims, product-listing mismatch, originality problems, AI disclosure issues, prohibited editing tactics, health or wellness claims, giveaway or gambling issues, IP risks, platform-safety issues, or affiliate creator eligibility limits.
---

# TikTok Content Creation Compliance

## Overview

Classify TikTok Shop promotional content as `Permitted`, `Risky - revise`, `Prohibited`, or `Unclear - verify live policy`. This skill applies to both sellers promoting their own products and creators promoting products for others, including affiliate creator workflows.

Use the official policy summary in [references/policy-summary.md](references/policy-summary.md) as the starting point, and stay conservative when a claim, visual, product anchor, promotion mechanic, or edit could mislead users.

If the user asks for the latest or current rule, reopen the official URLs in the reference file before giving a final answer. TikTok Shop policy guidance changes over time.

## Source hierarchy and dedupe

Use [references/policy-summary.md](references/policy-summary.md) as the canonical rule map, not as a page-by-page dump.

When multiple TikTok Shop pages repeat the same idea:
- prefer the most specific policy page as the primary source
- use broader "best practices" or "policy pro" pages as reinforcement, examples, or clarifications
- summarize repeated rules once instead of restating them under multiple headings
- if two pages appear to conflict, prefer the newer and more specific page, then mark the case `Unclear - verify live policy` if the conflict is still unresolved

Practical order of authority:
1. Product-category, health, AI, giveaway, gambling, platform-safety, and affiliate-eligibility pages
2. Core content-policy and enforcement pages
3. "Best Practices", "Creating with Impact", "Avoid Misleading Content", beauty and skincare guidance, and other "Become a Policy Pro" explainer pages

## Review Workflow

### 1. Identify the artifact

Determine what you are reviewing:
- video concept
- script
- shot list
- caption
- product claims
- editing plan
- finished video description
- exported video file
- product listing image or PDP image

Also determine the promotion context:
- seller promoting own product
- creator promoting own shop product
- affiliate creator promoting another seller's product
- creator asking whether they are even eligible to promote the selected category

If the user only provides a rough idea, infer the missing structure and review the idea anyway.

If the user provides a video file, inspect the actual media instead of relying only on the script or filename. Prefer:
- video metadata such as duration, aspect ratio, and subtitle tracks
- sampled frames across the full runtime
- on-screen text or subtitle extraction when available
- comparison against the linked product image or listing media

### 2. Check the highest-risk areas first

Review in this order:
1. Product-category or affiliate eligibility limits
2. Health, wellness, medical, fertility, pregnancy, sexual wellness, weight-loss, or muscle-gain claims
3. AI-generated or AI-edited people, product visuals, disclosures, or expert personas
4. Misleading product presentation, unrealistic effects, before-and-after logic, or exaggerated promises
5. Still-frame, low-quality, pre-recorded, or non-interactive video or LIVE formats
6. Gambling, giveaway, or purchase-incentive mechanics
7. Off-platform traffic redirects, IP, counterfeit, knockoff, or unoriginal-content risks
8. Nudity, sexualized behavior, minors, violence, harassment, or shocking-content issues

Load [references/policy-summary.md](references/policy-summary.md) before deciding.

If the user is working from a creator education page, treat that page as a shortcut into the relevant canonical rule. Do not overcount duplicate warnings just because the same issue appears in several training pages.

When reviewing a finished video, explicitly check:
- whether the shown package, bottle count, size, colorway, or bundle format matches the listing image
- whether watermarks from external tools, stock platforms, or AI systems are visible
- whether the edit appears fully AI-generated or significantly AI-edited, triggering disclosure review
- whether subtitles or dialogue add claims that are weaker or stronger than the visuals

### 3. Produce a policy verdict

Use exactly one primary verdict:
- `Permitted`
- `Risky - revise`
- `Prohibited`
- `Unclear - verify live policy`

For every flagged issue, name:
- the risky claim, visual, or edit
- why it is risky
- the matching policy section from the reference file
- the official source URL

### 4. Rewrite toward compliance

When revising content:
- replace hard promises with neutral, support-style wording
- align every claim with the actual listing, packaging, and product capabilities
- remove any fake authority signals, miracle framing, or fear tactics
- suggest AI disclosure when content is fully AI-generated or significantly AI-edited
- remove off-platform redirects, random-chance mechanics, or fake scarcity hooks
- ensure the product anchor actually matches the shown product
- keep product demos factual and product-focused

Do not claim content is safe if the policy signal is mixed. Mark it `Risky - revise` or `Unclear - verify live policy`.

## Output Format

Return reviews in this structure:

```text
Verdict: <Permitted | Risky - revise | Prohibited | Unclear - verify live policy>

Why:
- <plain-English summary>

Flags:
- <issue> -> <policy reason + source>

Safer rewrite:
- <replacement wording or scene direction>

Open questions:
- <only if something cannot be resolved from the supplied content>
```

## Boundaries

- Treat this skill as TikTok Shop guidance, not universal advice for all TikTok content.
- Treat the official Seller University pages as the source of truth for this skill.
- Distinguish between pages that explicitly apply to both sellers and creators and pages that are creator-specific but still relevant to creator-side promotions.
- Do not give {{profile.lateness.stakeholders.senderType}} or regulatory advice; flag when FDA, FTC, or similar review may be needed.
- If the user asks about non-TikTok-Shop platform rules, verify a broader official TikTok source before answering.
