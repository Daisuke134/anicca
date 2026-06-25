# Frank 記事 — Tasklist (SSOT for series #2)

> **役割**: AI-entities シリーズ #2 = Franklin (BlockRun) を解説 + 実走 + 公開。 1 つの canonical 進捗 file。 TaskCreate/TaskUpdate と同期。
> **記事 path**: `docs/articles/2026-06-15-frank-jp.md` (current branch: `feature/frank-run`、 base: `origin/docs/frank-article` HEAD 62405758)
> **Anti-rule (記事用)**: Anicca を一切登場させない、 em-dash「——」禁止、 verdict in sentence 1、 founder voice borrow 「Other agents write code. Franklin writes code AND spends money」、 cite everything inline。

---

## Phase A — 記事 (= 最優先、 シリーズ確立)

| # | やる事 | 状態 | 出力 |
|---|---|---|---|
| **A1** | Franklin 純粋実走 (free → paid → 5 タスク) | 🟡 進行中 | `docs/articles/research/2026-06-25-franklin-pure-run.md` |
| A2 | Block [1] (hook: bottleneck) — 「世界一賢いAIが、 $0.01 のサーバー代を払えない」 | ⬜ | 記事 [1] |
| A3 | Block [2] (Franklin の正体: YOPO + Economic Agent + wallet=identity) | ⬜ | 記事 [2] |
| A4 | Block [3] (BlockRun stack 全体: ClawRouter + blockrun-mcp + Franklin + Money-Maker) | ⬜ | 記事 [3] |
| A5 | Block [4] (仕組み: x402 1 往復 + Smart Router + 55+ models) | ⬜ | 記事 [4] |
| A6 | Block [5] (WE RAN IT、 A1 のログを fold) | ⬜ | 記事 [5] |
| A7 | Block [6] (verdict expanded: 誰が今日使うべき / 待つべき / 見送るべき) | ⬜ | 記事 [6] |
| A8 | Block [7] (次回予告 + manifesto close) | ⬜ | 記事 [7] |
| A9 | Block [8] (出典 11 件) | ⬜ | 記事 [8] |
| A10 | 全文 self-review (Playbook 54 rules diff) | ⬜ | review log |
| A11 | JP 公開: note + Zenn + Substack(JP) + X Articles + TikTok JP | ⬜ | 5 URL |
| A12 | EN 翻訳 + 公開: dev.to + Substack(EN) + X Articles + TikTok EN | ⬜ | 4 URL |

---

## Phase B — 学び固定

| # | やる事 | 状態 |
|---|---|---|
| B1 | A1〜A12 の learnings を `~/.openclaw/skills/ai-entity-article-writer/SKILL.md` に焼く | ⬜ |
| B2 | 次の AI-entity (Felix / ZHC / AutoHedge / Manus) spec | ⬜ |

---

## Phase C — Anicca 強化 (= 記事 ship 後、 別 task で実行)

| # | やる事 | 関連 task |
|---|---|---|
| C1 | Franklin Smart Router (15 次元) を `~/anicca/runtime/loop/brain.mjs` に移植 | TaskList #13 |
| C2 | blockrun-mcp 19 ツールを `~/anicca/skills/_shared/blockrun-mcp/` に配線 | TaskList #14 |
| C3 | `npx @anicca/loop` 1 行設置形 | TaskList #15 |
| C4 | compute-proxy stability (proxy_down 除去) | TaskList #10 |
| C5 | release tweet (YOPO borrow) JP + EN | TaskList #17 |

---

## Phase D — 別 CC 並行 (= 私は触らない、 monitor のみ)

| # | やる事 |
|---|---|
| D1 | self/spawn slot live flip + 雲 (DO/Akash) 上の最初の子 |
| D2 | UBI 分配 path 配線 (`~/anicca/skills/economy/ubi/`) |
| D3 | 全個体 dashboard 公開 (`aniccaai.com/dashboard`) |

---

## Research source pool (再利用)

| 種類 | URL |
|---|---|
| BlockRun get-started | https://blockrun.ai/get-started |
| BlockRun docs | https://blockrun.ai/docs |
| Franklin repo (627★) | https://github.com/BlockRunAI/Franklin |
| blockrun-mcp (466★) | https://github.com/BlockRunAI/blockrun-mcp |
| awesome-blockrun (15★) | https://github.com/BlockRunAI/awesome-blockrun |
| awesome-OpenClaw-Money-Maker (270★) | https://github.com/BlockRunAI/awesome-OpenClaw-Money-Maker |
| Founder | https://x.com/bc1beat |
| ClawRouter docs | https://blockrun.ai/docs/products/routing/clawrouter |
| x402 how-it-works | https://blockrun.ai/docs/x402/how-it-works |
| Intelligence Pricing | https://blockrun.ai/docs/products/intelligence/pricing |
| x402 protocol | https://x402.org |

---

## 進捗 update ルール

- 1 task 完了の瞬間 ☑ + commit + push (HARD 0.32 / 0.33)
- 新 task 出現の瞬間 ⬜ で追記 + 即着手 or 上位 task の blockedBy に連結
- 既存 task の状態変化 = 即 ☑/🟡/⬜ flip + commit
- branch: `feature/frank-run` (base `origin/docs/frank-article`)、 最終 merge は記事公開後に Dais 判断
