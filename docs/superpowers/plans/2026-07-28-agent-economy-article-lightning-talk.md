# Agent Economy Article and Japanese Lightning Talk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a beginner-first Japanese lightning-talk deck and article that explain how to build a financially independent AI without overstating the current external revenue.

**Architecture:** The Agent Economy live snapshot in `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` is the only claim source. The slide storyboard compresses that contract into ten claims; the article expands the same claims into twelve chapters. A final cross-artifact audit blocks publication when numbers or achieved levels diverge.

**Tech Stack:** Markdown, PowerPoint 16:9, Superpowers `pptx` workflow, local image/PDF visual QA, Agent Economy receipt and ledger evidence.

## Global Constraints

- The title is `AIを経済的に自立させる方法`.
- The subtitle is `自分で稼ぎ、自分の計算資源とクラウド代を払うAIの作り方`.
- The homeless/provider failure anecdote is limited to one slide and one article subsection.
- The current verified external revenue remains `$0.00` until §0.4 changes.
- Seed, bridge, self-pay, internal transfer, and recovered principal are not revenue.
- No secret, private key, personal identifier, or private runtime path appears in a public artifact.
- Japanese is the primary narrative; English adaptation starts only after the Japanese deck and article pass the claim audit.

---

### Task 1: Build the Japanese lightning-talk source

**Files:**
- Create: `docs/presentations/how-to-make-a-financially-independent-ai-ja.md`
- Reference: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

**Interfaces:**
- Consumes: §0.4.3a ten-slide contract and §0.4.3 live snapshot.
- Produces: Ten ordered slide records with title, on-slide copy, visual direction, speaker notes, evidence link, and estimated speaking seconds.

- [ ] **Step 1: Write all ten slide records**

Each record contains `title`, `claim`, `visual`, `speaker_notes`, `evidence`, and `seconds`. Total `seconds` must be at most 420.

- [ ] **Step 2: Check beginner language**

Define `wallet`, `USDC`, `receipt`, `ledger`, `compute`, and `reserve` in one Japanese sentence at first use. Remove unexplained protocol names from on-slide copy.

- [ ] **Step 3: Check the story spine**

Run:

```bash
rg -n '^## Slide ' docs/presentations/how-to-make-a-financially-independent-ai-ja.md
rg -n '自律|経済的自立|SELL|WORK|CAPITAL|external revenue|\\$0\\.00' docs/presentations/how-to-make-a-financially-independent-ai-ja.md
```

Expected: exactly ten slide headings and all required concepts present.

- [ ] **Step 4: Commit**

```bash
git add docs/presentations/how-to-make-a-financially-independent-ai-ja.md
git commit -m "docs(agent-economy): storyboard Japanese financial independence talk"
```

### Task 2: Render and visually verify the deck

**Files:**
- Create: `docs/presentations/how-to-make-a-financially-independent-ai-ja.pptx`
- Create: `docs/presentations/how-to-make-a-financially-independent-ai-ja.pdf`
- Modify: `docs/presentations/how-to-make-a-financially-independent-ai-ja.md`

**Interfaces:**
- Consumes: Task 1 slide records.
- Produces: A 16:9 ten-slide deck and PDF with matching claims and complete speaker notes.

- [ ] **Step 1: Read the `pptx` skill**

Use the available `pptx` skill before generating the presentation. Follow its rendering and validation requirements.

- [ ] **Step 2: Generate the ten-slide deck**

Use one claim per slide, body text at least 28pt, no stock AI-robot imagery, and simple wallet/receipt/ledger/cloud diagrams. Put evidence URLs in speaker notes or a compact source footer.

- [ ] **Step 3: Render to PDF and images**

Render every slide and inspect the montage plus each slide at full size.

- [ ] **Step 4: Correct visual defects**

Fix every clipped object, overflow, illegible footer, accidental overlap, low-contrast label, and inconsistent alignment. Re-render until all ten slides pass.

- [ ] **Step 5: Verify count and duration**

Expected: 10 slides, 16:9, total notes at most 420 seconds, no slide devoted primarily to the homeless anecdote.

- [ ] **Step 6: Commit**

```bash
git add docs/presentations/how-to-make-a-financially-independent-ai-ja.*
git commit -m "docs(agent-economy): add Japanese financial independence deck"
```

### Task 3: Write the Japanese article

**Files:**
- Create: `docs/articles/how-to-make-a-financially-independent-ai-ja.md`
- Reference: `docs/presentations/how-to-make-a-financially-independent-ai-ja.md`
- Reference: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

**Interfaces:**
- Consumes: The approved slide story spine and §0.4 evidence contract.
- Produces: A twelve-chapter beginner article with primary-source citations and real Agent Economy evidence.

- [ ] **Step 1: Write the twelve chapter headings**

Use the exact chapter order in §0.4.3a. Start with the definition of financial independence, not the failure anecdote.

- [ ] **Step 2: Expand each chapter**

Explain one concept per section, connect it to the end-to-end money flow, and label current evidence separately from the target architecture.

- [ ] **Step 3: Add evidence**

Link wallet-native payment claims to primary documentation and operational claims to repository evidence. Label `$0.00` as verified external revenue and distinguish PM wallet P&L.

- [ ] **Step 4: Run truth scans**

```bash
rg -n '完全に自立|必ず稼|初日から利益|\\$1,000.*稼げる|ホームレス' docs/articles/how-to-make-a-financially-independent-ai-ja.md
rg -n 'external revenue|\\$0\\.00|bootstrap|reserve|receipt|ledger' docs/articles/how-to-make-a-financially-independent-ai-ja.md
```

Expected: no forbidden claim; `ホームレス` appears at most once; all required truth concepts are present.

- [ ] **Step 5: Commit**

```bash
git add docs/articles/how-to-make-a-financially-independent-ai-ja.md
git commit -m "docs(agent-economy): write Japanese financial independence article"
```

### Task 4: Cross-artifact publication audit

**Files:**
- Modify: `docs/presentations/how-to-make-a-financially-independent-ai-ja.md`
- Modify: `docs/presentations/how-to-make-a-financially-independent-ai-ja.pptx`
- Modify: `docs/presentations/how-to-make-a-financially-independent-ai-ja.pdf`
- Modify: `docs/articles/how-to-make-a-financially-independent-ai-ja.md`
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

**Interfaces:**
- Consumes: The rendered deck, article, and fresh §0.4 snapshot.
- Produces: Claim parity and a spec status update for `AE-SLIDES-JP-1`, `AE-ARTICLE-JP-1`, and `AE-PUBLICATION-AUDIT-1`.

- [ ] **Step 1: Refresh the live snapshot**

Read the authoritative balances, external revenue, runtime cost, and current financial-independence level. Do not copy a stale value from the article or slides.

- [ ] **Step 2: Compare the artifacts**

Check title, definition, level ladder, revenue classification, current `$0.00`, monthly survival range, and achieved/unachieved labels across all three sources.

- [ ] **Step 3: Scan for secrets and private identifiers**

Run the repository secret scanner plus a targeted scan for private keys, seed phrases, bearer tokens, private email, and unredacted personal identifiers.

- [ ] **Step 4: Re-render after corrections**

Any slide text correction requires a fresh PPTX/PDF render and complete ten-slide visual inspection.

- [ ] **Step 5: Update the SSOT statuses**

Mark the three publication IDs complete only when the artifact files exist, the visual inspection passes, and the cross-check reports zero differences.

- [ ] **Step 6: Commit**

```bash
git add docs/presentations docs/articles docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
git commit -m "docs(agent-economy): verify financial independence publication bundle"
```
