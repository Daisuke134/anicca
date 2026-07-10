# Citation URL SSOT — Loop Engineering article (verified 2026-07-11)

Purpose: canonical, verified primary-source URLs for every citation used in the
"Loop Engineering" article. Each entry was checked live in this session with
`firecrawl scrape <url> markdown` and/or `gh api repos/<org>/<repo>` and/or
`curl -sI`/`curl -s -o /dev/null -w "%{http_code}"`. No URL below was invented —
anything not found after search is marked NOT FOUND. Do not reuse an item's URL
elsewhere without re-checking; primary URLs for evolving repos (e.g. OpenEvolve)
can move.

## Summary table

| # | Name | Verified URL(s) | Status |
|---|---|---|---|
| 1 | DGM (Darwin Gödel Machine) | https://github.com/jennyzzt/dgm · https://arxiv.org/abs/2505.22954 · https://sakana.ai/dgm/ | FOUND |
| 2 | OpenEvolve | https://github.com/algorithmicsuperintelligence/openevolve (canonical; `codelion/openevolve` 301-redirects here) | FOUND |
| 3 | ADAS | https://github.com/ShengranHu/ADAS · https://arxiv.org/abs/2408.08435 | FOUND |
| 4a | MAP-Elites (original) | https://arxiv.org/abs/1504.04909 | FOUND |
| 4b | Diverse Prompts (Santos et al., prompt-evolution MAP-Elites) | https://arxiv.org/abs/2504.14367 | FOUND |
| 5 | GEPA (genetic-pareto prompt evolution) | https://arxiv.org/abs/2507.19457 · https://github.com/gepa-ai/gepa | FOUND |
| 6 | HGM (Huxley-Gödel Machine, Wang et al.) | https://arxiv.org/abs/2510.21614 · repo https://github.com/metauto-ai/HGM (cited in paper) | FOUND |
| 7 | Reflexion (Shinn et al.) | https://arxiv.org/abs/2303.11366 | FOUND |
| 8 | Multi-Agent Debate / Degeneration-of-Thought (Liang et al.) | https://arxiv.org/abs/2305.19118 | FOUND |
| 9a | LayerX Zenn article 1 | https://zenn.dev/layerx/articles/b36ceffe6b5e20 | FOUND |
| 9b | LayerX Zenn article 2 | https://zenn.dev/layerx/articles/9f25ec86a31730 | FOUND |
| 10 | Anthropic "Building Effective Agents" | https://www.anthropic.com/engineering/building-effective-agents | FOUND |
| 11 | Lilian Weng — Harness Engineering for Self-Improvement | https://lilianweng.github.io/posts/2026-07-04-harness/ | FOUND |
| 12 | QuantEvolve | https://github.com/tarsyang/quantevolve | FOUND |
| 13 | PolyEvolve | https://github.com/mq545/polyevolve | FOUND |

All 13 items (14 counting the MAP-Elites/Diverse Prompts split) resolved. Zero NOT FOUND.

---

## Per-item detail

### 1. DGM (Darwin Gödel Machine)
- Repo: `https://github.com/jennyzzt/dgm` — GitHub description: "Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents". Verified via `gh api repos/jennyzzt/dgm --jq '.full_name, .html_url, .description'` → `jennyzzt/dgm`.
- Paper: `https://arxiv.org/abs/2505.22954` (submitted 29 May 2025, v3 12 Mar 2026). Title: "Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents" (Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, Jeff Clune).
- Sakana AI blog: `https://sakana.ai/dgm/`, dated May 30, 2025, HTTP 200.
- Core quote (arXiv abstract, exact figures for the SWE-bench claim): "increasing performance on SWE-bench from 20.0% to 50.0%, and on Polyglot from 14.2% to 30.7%."
- Evidence: `curl -sI` → HTTP/2 200 on all three URLs; `firecrawl scrape` on the arXiv page returned the exact title/authors/abstract; `firecrawl scrape` on the Sakana blog returned the May 30, 2025 post with link to the arXiv report and `github.com/jennyzzt/dgm`.

### 2. OpenEvolve
- Canonical repo (now): `https://github.com/algorithmicsuperintelligence/openevolve` — `gh api repos/algorithmicsuperintelligence/openevolve --jq '.full_name, .html_url, .description, .stargazers_count'` → `algorithmicsuperintelligence/openevolve`, description "Open-source implementation of AlphaEvolve", 6673 stars.
- `codelion/openevolve` still resolves but is a redirect, not the canonical location: `curl -sI https://github.com/codelion/openevolve` → `HTTP/2 301` with `location: https://github.com/algorithmicsuperintelligence/openevolve`. Use the `algorithmicsuperintelligence` org as the citation target.
- Evidence: gh api JSON + curl redirect header captured live.

### 3. ADAS (Automated Design of Agentic Systems)
- Repo: `https://github.com/ShengranHu/ADAS` — description "[ICLR 2025] Automated Design of Agentic Systems" via `gh api repos/ShengranHu/ADAS`.
- Paper: `https://arxiv.org/abs/2408.08435` (submitted 15 Aug 2024, v2 2 Mar 2025). Title: "Automated Design of Agentic Systems" (Shengran Hu, Cong Lu, Jeff Clune).
- Core quote: "We describe a newly forming research area, Automated Design of Agentic Systems (ADAS), which aims to automatically create powerful agentic system designs, including inventing novel building blocks and/or combining them in new ways."
- Evidence: `gh api` JSON + `firecrawl scrape` of the arXiv abstract page (title/authors/abstract matched exactly).

### 4a. MAP-Elites (original, Mouret & Clune)
- Paper: `https://arxiv.org/abs/1504.04909` (submitted 20 Apr 2015). Title: "Illuminating search spaces by mapping elites" (Jean-Baptiste Mouret, Jeff Clune).
- Core quote: "This Multi-dimensional Archive of Phenotypic Elites (MAP-Elites) algorithm illuminates search spaces, allowing researchers to understand how interesting attributes of solutions combine to affect performance."
- Evidence: `firecrawl scrape` returned exact title/authors/abstract matching the request.

### 4b. Diverse Prompts (Santos et al., prompt-evolution paper)
- Paper: `https://arxiv.org/abs/2504.14367` (submitted 19 Apr 2025). Title: "Diverse Prompts: Illuminating the Prompt Space of Large Language Models with MAP-Elites" (Gabriel Machado Santos, Rita Maria da Silva Julia, Marcelo Zanchetta do Nascimento). Accepted IEEE CEC 2025.
- Core quote: "This work introduces an evolutionary approach that combines context-free grammar (CFG) with the MAP-Elites algorithm to systematically explore the prompt space."
- Found via Google search result page scrape (`by GM Santos · 2025 · Cited by 4 — Diverse Prompts: Illuminating the Prompt Space of Large Language Models with MAP-Elites`), then verified directly on the arXiv abstract page.

### 5. GEPA (Genetic-Pareto prompt evolution)
- Paper: `https://arxiv.org/abs/2507.19457` (submitted 25 Jul 2025, v2 14 Feb 2026, accepted ICLR 2026 Oral). Title: "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning" (Lakshya A Agrawal et al., 17 authors incl. Omar Khattab, Matei Zaharia).
- Repo: `https://github.com/gepa-ai/gepa` — `gh api repos/gepa-ai/gepa` description: "Optimize prompts, code, and more with AI-powered Reflective Text Evolution". Also cited directly in the arXiv abstract: "We release our code at https://github.com/gepa-ai/gepa."
- Core quote: "GEPA outperforms GRPO by 6% on average and by up to 20%, while using up to 35x fewer rollouts."
- Evidence: `firecrawl scrape` of arXiv abstract + `gh api` on the repo.

### 6. HGM (Huxley-Gödel Machine, Wang et al.)
- Paper: `https://arxiv.org/abs/2510.21614` (submitted 24 Oct 2025, v3 29 Oct 2025). Title: "Huxley-Gödel Machine: Human-Level Coding Agent Development by an Approximation of the Optimal Self-Improving Machine" (Wenyi Wang, Piotr Piękos, Li Nanbo, Firas Laakom, Yimeng Chen, Mateusz Ostaszewski, Mingchen Zhuge, Jürgen Schmidhuber).
- Code (cited in the abstract, not independently gh-api-verified beyond the arXiv link text): `https://github.com/metauto-ai/HGM`.
- Core quote: "On SWE-bench Verified and Polyglot, HGM outperforms prior self-improving coding agent development methods while using fewer allocated CPU hours... achieves human-level performance, matching the best officially checked results of human-engineered coding agents."
- Evidence: `firecrawl scrape` of arXiv abstract page (title/authors/abstract matched exactly).

### 7. Reflexion (Shinn et al.)
- Paper: `https://arxiv.org/abs/2303.11366` (submitted 20 Mar 2023, v4 10 Oct 2023). Title: "Reflexion: Language Agents with Verbal Reinforcement Learning" (Noah Shinn, Federico Cassano, Edward Berman, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao).
- Core quote: "Reflexion agents verbally reflect on task feedback signals, then maintain their own reflective text in an episodic memory buffer to induce better decision-making in subsequent trials... Reflexion achieves a 91% pass@1 accuracy on the HumanEval coding benchmark, surpassing the previous state-of-the-art GPT-4 that achieves 80%."
- Evidence: `firecrawl scrape` of arXiv abstract page.

### 8. Multi-Agent Debate / Degeneration-of-Thought (Liang et al.)
- Paper: `https://arxiv.org/abs/2305.19118` (submitted 30 May 2023, v4 9 Oct 2024, EMNLP 2024 main conference). Title: "Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate" (Tian Liang, Zhiwei He, Wenxiang Jiao, Xing Wang, Yan Wang, Rui Wang, Yujiu Yang, Shuming Shi, Zhaopeng Tu).
- Core quote (defines the exact term used in the article): "our study shows that such reflection-style methods suffer from the Degeneration-of-Thought (DoT) problem: once the LLM has established confidence in its solutions, it is unable to generate novel thoughts later through reflection even if its initial stance is incorrect. To address the DoT problem, we propose a Multi-Agent Debate (MAD) framework."
- Repo cited in abstract: `https://github.com/Skytliang/Multi-Agents-Debate`.
- Evidence: `firecrawl scrape` of arXiv abstract page.

### 9. LayerX Zenn articles
- `https://zenn.dev/layerx/articles/b36ceffe6b5e20` — HTTP 200. Title: "自己改善エージェントはなぜ前提を覆せないのか ― 局所最適とハーネスでの脱出" (published 2026/06/17, publication: LayerX, author ozro).
- `https://zenn.dev/layerx/articles/9f25ec86a31730` — HTTP 200. Title: "Agent Skills自動最適化の研究、中身はほぼ深層学習の訓練ループだった" (published 2026/07/08, publication: LayerX, author ozro).
- Evidence: `firecrawl scrape` on both URLs returned the LayerX publication header, title, author, and publish date; `curl -sI`/status-code check confirmed HTTP 200 on both.

### 10. Anthropic "Building Effective Agents"
- URL: `https://www.anthropic.com/engineering/building-effective-agents` — HTTP 200.
- Core quote (exact, as requested): "Agents can handle sophisticated tasks, but their implementation is often straightforward. They are typically just LLMs using tools based on environmental feedback in a loop. It is therefore crucial to design toolsets and their documentation clearly and thoughtfully."
- Evidence: `firecrawl scrape` returned the exact sentence; `curl -s -o /dev/null -w "%{http_code}"` → 200.

### 11. Lilian Weng — harness/self-improvement post
- URL: `https://lilianweng.github.io/posts/2026-07-04-harness/` — HTTP 200. Title: "Harness Engineering for Self-Improvement". Date: July 4, 2026. Author: Lilian Weng. Estimated reading time: 28 min.
- Found by listing `https://lilianweng.github.io/` posts (front page shows it as the newest post, ahead of "Scaling Laws, Carefully" and "Why We Think"), then fetched the post page directly to confirm title/date/TOC (sections include "Harness Design Patterns", "Harness Optimization", "Self-Improving Harness", "Evolutionary Search", "Joint Optimization with Model Weights").
- Core quote (opening paragraph): "The concept of recursive self-improvement (RSI) dates back to I. J. Good (1965), where he defined an 'ultraintelligent machine' as a system that can surpass humans in all intellectual activities and design better machines to improve itself."
- Note: this is the exact post already referenced in this repo's own `docs/loop-engineering/06-harness-engineering-weng.md` — this entry corroborates that citation with a fresh live check.

### 12. QuantEvolve
- Repo: `https://github.com/tarsyang/quantevolve` — `gh api repos/tarsyang/quantevolve --jq '.description, .html_url'` → description: "Evolutionary Quantitative Trading Strategy Development System. Fork of OpenEvolve".
- Evidence: `gh api` JSON confirms repo exists and its stated lineage (fork of OpenEvolve).

### 13. PolyEvolve
- Repo: `https://github.com/mq545/polyevolve` — `gh api repos/mq545/polyevolve --jq '.description, .html_url'` → description: "Evolve trading strategies for prediction markets - and measure the edge against the crowd."
- Evidence: `gh api` JSON confirms repo exists and its description.

---

## Verification methods used (for reproducibility)

| Method | Used for |
|---|---|
| `gh api repos/<org>/<repo> --jq '.full_name, .html_url, .description'` | All GitHub repos (1, 2, 3, 5, 12, 13) |
| `curl -sI <url>` / `curl -s -o /dev/null -w "%{http_code}"` | HTTP existence check on all arXiv/blog/Zenn/Anthropic/Weng URLs |
| `/opt/homebrew/bin/firecrawl scrape <url> markdown` | Title/author/abstract extraction for all arXiv papers (1, 3, 4a, 4b, 5, 6, 7, 8), the Sakana AI blog (1), the Anthropic engineering post (10), both LayerX Zenn articles (9), and the Lilian Weng blog index + post (11) |
| Google search-result-page scrape via `firecrawl scrape` | Locating the Santos et al. "Diverse Prompts" arXiv ID (4b) before direct verification |

No URL in this file was invented. Every entry above was independently confirmed live in this session (2026-07-11) via at least one HTTP existence check plus one content-match check against the requested name/claim.
