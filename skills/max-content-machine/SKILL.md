---
name: content-machine
version: 1.0.0
description: |
  Autonomous 24/7 affiliate content production pipeline for OpenClaw agents.
  Orchestrates research → brief → article writing → quality gate → deploy.
  Supports multiple niche sites with silo structure, Amazon affiliate links,
  AEO/GEO optimization, and Cloudflare Workers deployment.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - WebSearch
  - WebFetch
---

# Content Machine — Autonomous Affiliate Content Pipeline

## What this skill does

Turns keywords into published SEO articles automatically:

1. **Research** (Lena) — SERP analysis, content gaps, Amazon product check
2. **Brief** — structured content plan per keyword
3. **Write** (Felix) — 2500+ word article with AEO/GEO optimization
4. **Quality Gate** — 20-point automated check (H1, word count, FAQ, images, links)
5. **Deploy** — Cloudflare Workers/Pages with cache purge

## When to use

- Building niche affiliate sites at scale
- Automating content production with multi-agent systems
- Maintaining quality standards across large article batches

## Pipeline flow

```
KEYWORD-BACKLOG.md
    ↓
Lena (Research Agent) → content-brief.md
    ↓
Felix (Content Agent) → article.html
    ↓
Quality Gate (python3 quality_gate.py)
    ↓ PASS
Deploy (wrangler deploy)
    ↓
Sitemap update + Cache purge
```

## AEO/GEO Rules (built-in)

Every article must have:
- H2 starts with 2-3 sentence quotable answer (bold)
- Min. 1 comparison table with concrete numbers
- FAQPage JSON-LD schema
- dateModified schema
- Neutral ranking (no self-promotional listicles)

## Quality Gate checks

- H1 present and keyword-rich
- Min. 2500 words
- FAQPage schema
- 4 images (1 eager + 3 lazy)
- 5+ internal links
- Amazon affiliate links with correct tag
- Author box (last element)
- Meta description (max 155 chars)

## Setup

1. Create `KEYWORD-BACKLOG.md` with target keywords
2. Configure site paths and Amazon affiliate tags
3. Set up Cloudflare API token
4. Run pipeline via heartbeat or cron

## File structure

```
/your-site/
  ARTIKEL-VORLAGE.html   ← Article template
  quality_gate.py        ← Quality checker
  wrangler.toml          ← Cloudflare config
  sitemap.xml            ← Auto-updated

/workspace/
  KEYWORD-BACKLOG.md     ← Keyword queue
  scripts/
    pipeline_controller.py
    post_article.py
    generate_felix_brief.py
```
