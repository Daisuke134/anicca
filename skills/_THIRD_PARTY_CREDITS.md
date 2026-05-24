# Third-Party Skill Credits

This file documents skills installed in `~/.openclaw/skills/` that come from external,
upstream sources. Local Anicca / OpenClaw skills are not listed here.

## K-Dense AI — scientific-agent-skills

- **Source repo**: https://github.com/K-Dense-AI/scientific-agent-skills
- **License**: MIT
- **Copyright**: © 2025 K-Dense Inc.
- **Upstream layout**: `scientific-skills/<name>/SKILL.md`
- **Date installed**: 2026-05-07
- **Upstream commit at install time**: `7a1d69cc3feb50b20f4b4bbe275316d39a5a7ba7`
  (Merge PR #143 — exa-search-skill, dated 2026-05-06)
- **Install method**: sparse-checkout into `/tmp/kdense-skills`, then `cp -r` per skill
  (only the 14 listed below were copied — the remaining ~120 K-Dense skills were not
  installed). Existing local skills were never overwritten.

### Installed skills (14)

| # | Skill (as installed) | Upstream name | Purpose | SKILL.md size |
|---|----------------------|---------------|---------|----------------|
| 1 | `paper-lookup` | `paper-lookup` | Multi-database academic paper search (PubMed, arXiv, OpenAlex, Crossref, Semantic Scholar, etc.) | 9 635 B |
| 2 | `bgpt-paper-search` | `bgpt-paper-search` | Bio-domain GPT-style paper search | 2 479 B |
| 3 | `literature-review` | `literature-review` | PRISMA-style systematic literature review with PDF generation + citation verification | 28 057 B |
| 4 | `parallel-web` | `parallel-web` | Parallel web-search execution (was requested as `parallel-web-search` — repo name is `parallel-web`) | 6 013 B |
| 5 | `database-lookup` | `database-lookup` | Structured DB lookup helpers | 28 231 B |
| 6 | `hypothesis-generation` | `hypothesis-generation` | Generates testable scientific hypotheses from prior literature | 13 847 B |
| 7 | `scientific-writing` | `scientific-writing` | Manuscript drafting (intro, methods, results, discussion) | 33 740 B |
| 8 | `peer-review` | `peer-review` | Peer-review checklist + critique generation | 23 120 B |
| 9 | `matplotlib` | `matplotlib` | Plot templates + style configurator | 11 454 B |
| 10 | `seaborn` | `seaborn` | Seaborn statistical visualisation guidance | 19 601 B |
| 11 | `infographics` | `infographics` | Infographic generation (uses Nano Banana Pro) | 18 071 B |
| 12 | `markdown-mermaid-writing` | `markdown-mermaid-writing` | Mermaid + markdown technical writing | 14 887 B |
| 13 | `pytorch-lightning` | `pytorch-lightning` | LightningModule + DataModule templates | 6 675 B |
| 14 | `transformers` | `transformers` | Hugging Face transformers usage | 5 084 B |

### Not installed

- **`document-skills`** — was requested in the rollout brief but does NOT exist as a single
  skill in the K-Dense repo (commit `7a1d69c`). The closest analogues in K-Dense are the
  individual file-format skills `docx`, `pptx`, `pdf`, `xlsx`, `markitdown`. The first four
  collide with already-installed Anthropic skills, so we deferred. Decision: leave for the
  user to confirm intent. See `INTEGRATION_LOG.md`.

### Runtime dependencies introduced

Several K-Dense skills shell out to external services or Python packages. They are not
required for skill discovery / agent invocation, but they ARE required for any script
inside the skill to actually run end-to-end:

- **OpenRouter API key** — `scientific-writing/scripts/generate_image.py` reads
  `OPENROUTER_API_KEY` from env.
- **Nano Banana 2 / Nano Banana Pro** (Google image-gen) — used by
  `literature-review/scripts/generate_schematic*.py`, `hypothesis-generation`,
  `scientific-writing`, `peer-review`, and `infographics`.
- **Python**: `matplotlib`, `seaborn`, `pytorch_lightning`, `transformers` — only required
  if the agent decides to execute the skill's example code.

These will fail loudly at runtime if missing; the skill files themselves load fine.

### Attribution requirement (MIT)

Per MIT, the upstream copyright notice must accompany any redistribution. The original
LICENSE.md is preserved at `/tmp/kdense-skills/LICENSE.md` after clone, and the K-Dense
copyright line is included verbatim above. Each installed skill folder retains its
original `metadata.skill-author: K-Dense Inc.` frontmatter line.

---

*Last updated: 2026-05-07*

---

## Sakana AI-Scientist-v2 — BFTS, multi-{{profile.lateness.stakeholders.senderType}} writeup, gather_citations

- **Repo:** https://github.com/SakanaAI/AI-Scientist-v2
- **Commit installed:** `96bd51617cfdbb494a9fc283af00fe090edfae48` (2025-12-19)
- **License:** **The AI Scientist Source Code License v1.0** (Sakana AI, December 2025).
  Based on the Responsible AI Source Code License v1.1 (http://licenses.ai/).
  © 2024–2025 Sakana AI. **NOT Apache 2.0** — Sakana relicensed on 2025-12-19.
- **License text:** preserved at `/tmp/sakana-ai-scientist/LICENSE` after clone;
  also reachable at https://github.com/SakanaAI/AI-Scientist-v2/blob/main/LICENSE.

### Files adapted into ResearchClaw

| Sakana source file | ResearchClaw destination | Status |
|---|---|---|
| `ai_scientist/treesearch/perform_experiments_bfts_with_agentmanager.py` | `researchclaw/treesearch/bfts_manager.py` | concept port (BFTSConfig/BFTSScorer/BFTSNode); full orchestrator left as a documented stub |
| `ai_scientist/perform_writeup.py`, `ai_scientist/perform_icbinb_writeup.py` | `researchclaw/paper_generation/multi_{{profile.lateness.stakeholders.senderType}}_writeup.py` | section-by-section draft → polish loop |
| `ai_scientist/perform_icbinb_writeup.py::gather_citations` | `researchclaw/paper_generation/citation_manager.py` | multi-round Semantic Scholar lookup + dedupe |

### Use restrictions you must comply with (clause 3.2)

The Sakana license PROHIBITS any use of code derived from this work — including the
ResearchClaw ports — to:

- **a. Surveillance** — detect/infer protected classes or identity features.
- **b. Computer Generated Media** — audio/video deepfakes without watermark/caption.
- **c. Health Care** — predict insurance-claim likelihood; diagnose conditions
  without human oversight.
- **d. Criminal** — predict crime likelihood from facial / personal data.
- **e. Scientific Manuscripts (THE "AI SCIENTIST" CLAUSE)** — generate or
  disseminate manuscripts without **prominently disclosing** AI authorship
  (e.g. Abstract or Methods/Disclosure section).

The Stage 17 hook (`use_sakana_writeup`) auto-injects `[AI-GENERATED]` into the
abstract when `require_ai_disclosure: true`. Operators are still responsible for
clauses a–d; downstream consumers of Stage 17 output must keep the disclosure.

### Distribution requirement (clause 3.1)

If you redistribute ResearchClaw with the Sakana port enabled, you MUST include
the full Sakana license text. Keep this credits file alongside any release.

---

## Karpathy autoresearch — iterative-refine pattern

- **Repo:** https://github.com/karpathy/autoresearch
- **Commit referenced:** master HEAD as of 2026-05-07 (see GitHub for SHA).
- **License:** README states `## License\nMIT`. **No `LICENSE` file is shipped
  in the repository.** Out of caution, ResearchClaw implements the *pattern*
  described in `program.md` from scratch and does NOT copy upstream source code.
- **Attribution:** © Andrej Karpathy.

### Files adapted into ResearchClaw

| Karpathy source | ResearchClaw destination | Status |
|---|---|---|
| `program.md`, `README.md` (loop description) | `researchclaw/pipeline/karpathy_refine.py` | pattern reimplemented from scratch — single mutable file, fixed time budget (300s default), regex-extracted vocab-independent metric, TSV log, git keep-or-reset semantics |

If Karpathy adds a formal LICENSE file, this section should be revisited.

---

## remotion-dev — remotion-best-practices

- **Source repo:** https://github.com/remotion-dev/skills
- **Upstream path:** `skills/remotion/SKILL.md` (the SKILL declares `name: remotion-best-practices`)
- **Installed at:** `~/.openclaw/skills/remotion-best-practices/`
- **Install date:** 2026-05-07
- **Install commit:** `277510e78245ac0fa275d7cb6520d52e0ac2e212` ("Update template")
- **Install method:** `git clone --depth 1` then `cp -r skills/remotion → ~/.openclaw/skills/remotion-best-practices/` (the `npx skills add remotion-dev/skills/remotion-best-practices` form mismatched the upstream layout — the upstream directory is `skills/remotion/`, not `skills/remotion-best-practices/`)
- **License:** **Not declared** in the upstream repo. The parent Remotion product is licensed under SUL-1.0 (https://remotion.dev/license); this skills repo carries no separate LICENSE file. Treat this skill as documentation/best-practices guidance for in-org use only — see `~/.openclaw/skills/remotion-best-practices/NOTICE.md`. Do not redistribute without checking upstream license terms.

## vercel-labs — find-skills

- **Source repo:** https://github.com/vercel-labs/skills
- **Upstream path:** `skills/find-skills/SKILL.md`
- **Installed at:** `~/.openclaw/skills/find-skills/`
- **Install date:** 2026-05-07
- **Install commit:** `eec87fd44fca572d5275a472ea13c31aaceb65d0`
- **Install method:** `git clone --depth 1` then `cp -r skills/find-skills → ~/.openclaw/skills/find-skills/`
- **License:** MIT (per upstream `package.json` `"license": "MIT"`; see also `~/.openclaw/skills/find-skills/NOTICE.md`).
- **Copyright:** © Vercel Labs.

## anthropics — frontend-design

- **Source repo:** https://github.com/anthropics/skills
- **Upstream path:** `skills/frontend-design/SKILL.md` (with per-skill `LICENSE.txt`)
- **Installed at:** `~/.openclaw/skills/frontend-design/`
- **Install date:** 2026-05-07
- **Install commit:** `d211d437443a7b2496a3dad9575e7dddd724c585`
- **Install method:** `git clone --depth 1` then `cp -r skills/frontend-design → ~/.openclaw/skills/frontend-design/` (LICENSE.txt was copied alongside SKILL.md).
- **License:** Apache License 2.0 (file: `~/.openclaw/skills/frontend-design/LICENSE.txt`).
- **Copyright:** © Anthropic, PBC.

> **Install fallback note (2026-05-07):** the brief instructed `npx skills add <owner>/skills/<name>`, which clones and looks for `<name>/SKILL.md`. For remotion-dev/skills the upstream actual path is `skills/remotion/`, so `npx skills add` reported "No skills found"; we fell back to git sparse-clone + `cp -r`, which is the same pattern used for K-Dense earlier.

---

*Last updated: 2026-05-07 (Phase 2a/3/4 rollout + Postiz migration third-party adds)*
