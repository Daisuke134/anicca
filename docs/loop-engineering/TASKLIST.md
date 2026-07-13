# TASKLIST — ★唯一の SSOT★（順序は Dais が決めた。勝手に入れ替えるな）

最終更新: 2026-07-13 18:40 JST / branch `feature/clip-rewards`
TaskList（会話内）と本ファイルと spec は **同じ ID・同じ順序**。3つが一致しない時は本ファイルが正。

> **このファイルが正本。** 会話は揮発する。ここに書いていないタスクは存在しない。
> earn/colony 側の T13/T15/T5-T12（`34-TODO-ORDERED.md`）は **Anicca 自身の仕事であって、私(claude-p)のタスクではない**。混ぜない。

## ★ 唯一の真実 = NET PROFIT ★
成果 = loop が自分で稼いで、渡された額より残高が増えた時のみ。
activity / applied / posted / built / test-green は成果ではない。**現在の実現 net profit = ¥0**（gig: applied 113 / won 2 / paid 0）。

## 順序の原則（Dais 決定）
1. **共有基盤(L0)を先に**（disk / session / learn-from-winners）。ここが死ぬと全ループが死ぬ。
2. **稼ぐループを1本ずつ**: gig → clip → video → life manager。金に近い順。
3. 1本が **1アカウント $1k MRR 安定** → アカウント/サイトを増やして scale。
4. 全ループは4層（BASE / self-heal / self-improve / reality-gate）を持つ。spec §2 が正本。

---

## 順序（この番号順にしかやらない。ID は会話の TaskList と一致）

| # | タスク | 状態 |
|---|---|---|
| — | 床の実測（before → after） | ✅ DONE |
| — | floor-guard を正しい測定器に作り直す | ✅ DONE |
| — | Q1: 4ループが本当に稼いでいるか実データで確定 | ✅ DONE（4本とも ¥0。詳細下記） |
| **17 / L0-1** | **disk: 予防運転を恒久化（free≥20GB 維持）** | ✅ DONE（commit 07e142e + bfac510） |
| **18 / L0-2** | **session: 永続化を全ブラウザループ共通で解決（人間の再ログインを消す）** | ✅ DONE（commit c2e9c1b2）※sticky proxy は scale #26 で |
| **19 / L0-3** | **learn-from-winners: 成功者を実際に見て学ぶ層を全ループに埋める** | pending |
| **20 / GIG-1** | earn-gig を skill 化（10KB の1行プロンプトを分解） | pending |
| **21 / GIG-2** | プロフィールを実編集して Dais に見せる（デモ） | pending |
| **22 / GIG-3** | paid=0 を殺す（納品→検収→出金→着金） | pending |
| **23 / CLIP-1** | clip: self-improve + scout を移植し投稿失敗を直す | pending |
| **24 / VIDEO-1** | video: warmup の hardcode を外し self-improve + scout 移植 | pending |
| **25 / LM-1** | life manager loop（X-1）を 1k MRR まで | pending |
| **26 / Q3** | scale: steel-browser を Docker で cloud に立て、gig/clip 1本を回す PoC + ToS 公式確認 + 経済表（調査済 → doc 45） | pending |
| **27 / OSS** | profitable-claude 公開 + dashboard 収益透明化 | pending |

Q2（ブラウザ共有の ASCII）は提出済み → spec §3 / `~/anicca/skills/browser/SKILL.md`。

### Q1 の結末（4ループの実働、実データ 2026-07-13）
| loop | tmux/launchd | 実際にやっていること | 稼ぎ |
|---|---|---|---|
| gig | ALIVE | 応募は回る（task-request 87件）。今日 ENOSPC で一度死んだ | won 2 / **paid 0 / ¥0** |
| clip | ALIVE | 投稿が3連続失敗（post_url=null）。週次 -250 | ¥0 |
| video | ALIVE | warmup を抜けられない（実視聴2件<3。hardcode） | $0 |
| reddit | Dais が停止 | — | — |
tmux 3本(anicca-2/3/4)は**ループではない**（放置された対話セッション）。本物のループは launchd。

### 各ループの3層監査（実コード確認済み。「各 earn skill=3層」は誇張だった）
| loop | BASE | self-heal | self-improve(外部学習) |
|---|---|---|---|
| gig | LLM | ✅ 286回発火 | ✅ 実在（ただし firecrawl 依存で死んでいた→crwl に交換済み。プロフィール未対象→追加済み） |
| clip | LLM | ✅ 250回発火 | ❌ 無い（記録だけ） |
| video | ❌ hardcode | ✅ 59回発火 | ❌ 無い |

---

## 1〜2 の結末（トークンの床）— 二度と同じ事故を起こさないための記録

### 測定器が壊れていた（これが最大の発見）
- **誤り**: 「jsonl の1回目 usage（input + cache_creation + cache_read）= 床」。**プロンプトキャッシュの当たり方に汚染される。**
  同一設定で A/B したら **48,959 vs 48,958 = 差ゼロ**。この数字では削減の可否を判定できない。
- **正しい器**: `claude -p "/context"`。新しいプロセスが新しい設定で床を焼き直すので、これが唯一の after。
  **床は起動時に焼き込まれる。動いているプロセスの中では絶対に変わらない。**

### 床の正体（/context 実測、2026-07-13）
```
床 ≈ 34.6k
├─ 構造（触れない）................ 23.6k
│  ├─ System tools (deferred) 15.1k   ★MCP を全部切っても減らない = Claude Code 組込み★
│  ├─ System tools ........... 5.0k
│  └─ System prompt .......... 2.7k
└─ ★我々の分（ここだけが戦場）★ ... 11k（floor-guard 実測）
   ├─ skills 6,668 / memory 4,413 / agents 2,153
```
**予算 25,000 は物理的に不可能**（構造だけで 23.6k）。予算は **我々の分だけ**を memory 9k / skills 8k / agents 3k で縛る。

### やった削減（全部 durable）
- plugin 4本を **`claude plugin disable`** で無効化（money 20skill / agent-skills 20skill+4agent / goal-setter / programming-advisor）
  → ★`settings.json` の `enabledPlugins` 手編集は Claude Code に書き戻されて無効。CLI を使え★
- MCP 3本削除（codegraph / conway / maestro — 未使用 or 接続失敗）
- agent description 3体を書き換え（`<example>` を body へ移動。trigger 語は保持）
- skill 36個に `disable-model-invocation: true`（`/名前` で今も呼べる）
- `~/.claude/scripts/floor-guard.py` を作り直し（SessionStart hook 配線済み。予算超過で exit 1 + 叫ぶ）

### 棄却済み（二度と時間を使うな）
- claude.ai の connector（Slack/Drive/Gmail/…）が床を食っている説 → **fresh session に1個も載っていない**。無関係
- MCP を切れば deferred 15.1k が減る説 → serena を外しても **15.1k のまま**
- `@import` で床が減る説 → 公式: "imported files load at launch"
- 出力削減ツール（caveman 等）で請求が減る説 → 請求の 99% は input

**恒久ルール**: 何かを CLAUDE.md / memory / skill / agent に足す前に `python3 ~/.claude/scripts/floor-guard.py` を実行し、
予算に空きが無ければ**足す前に同量を削る**。置き場所は安い順に
**skill → skill + `disable-model-invocation: true` → rules + `paths:` → memory → CLAUDE.md（最後の手段）**。

---

## 関連
- 床の物理と公式引用 → `43-floor-budget-the-permanent-rule.md` / `44-floor-minimization-best-practice.md`
- ブラウザ基盤（全ループ共通）→ `~/anicca/skills/browser/SKILL.md`
- web 取得の既定 → `docs/reference/crawl4ai-web-scraping.md`（`crwl <url> -o markdown`。firecrawl は credit 枯渇）
- earn/colony の TODO（**Anicca 自身の仕事。私のタスクではない**）→ `34-TODO-ORDERED.md`
