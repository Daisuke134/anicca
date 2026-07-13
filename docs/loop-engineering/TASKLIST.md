# TASKLIST — ★唯一の SSOT★（順序は Dais が決めた。勝手に入れ替えるな）

最終更新: 2026-07-13 17:20 JST / branch `feature/clip-rewards`

> **このファイルが正本。** 会話は揮発する。ここに書いていないタスクは存在しない。
> earn/colony 側の T13/T15/T5-T12（`34-TODO-ORDERED.md`）は **Anicca 自身の仕事であって、私(claude-p)のタスクではない**。混ぜない。

## ★ 唯一の真実 = NET PROFIT ★
成果 = loop が自分で redeem して、渡された額より wallet が増えた時のみ。
activity / build / 建玉 / test-green は成果ではない。**現在の実現 net profit = ¥0**（gig: applied 113 / won 2 / paid 0）。

---

## 順序（この番号順にしかやらない）

| # | タスク | 状態 |
|---|---|---|
| **1** | 床の実測（before → after） | ✅ DONE 2026-07-13 |
| **2** | floor-guard を正しい測定器に作り直す | ✅ DONE 2026-07-13 |
| **3** | **Q1: 4ループが本当に成果物を書いているかを実データで確定** | ★次★ |
| **4** | **Q3: スケールの現実解を調査 → PoC を1本実際に動かす** | pending |
| 5 | growth engine X-1: MoneyPrinterTurbo を実導入（spec §2。他ツールに差し替えるな） | pending |
| 6 | growth engine G0-1: 台本A（日本語・spec §5）で動画1本を生成 | pending |
| 7 | growth engine G0-2: Telegram(8547730585) へ送付 → Dais の品質OK（唯一の human gate） | pending |
| 8 | growth engine G0-3: IG 実投稿 → ★ログアウト状態で公開URLを実見★ | pending |
| 9 | growth engine G1: loop 化（launchd 朝夜2本・常駐禁止） | pending |
| 10 | metrics_fetch.py（instagrapi + daily-driver sessionid）で実 plays を funnel jsonl へ | pending |
| 11 | 毎実行 Telegram 報告 + reality gate を loop 内に埋め込む | pending |
| 12 | growth engine を3日連続で自走させる | pending |
| 13 | firecrawl → crawl4ai 一本化の後始末（残った FIRECRAWL 参照を `crwl` に置換） | pending |
| 14 | TODO 正本の衝突を解消（このファイルを正本にし、他は「→参照」1行にする） | 進行中（本ファイルがその第一歩） |
| 15 | article cron の修復（全 enabled:false + 実在しないパス。gateway cron CLI 経由で直す） | pending |

Q2（各ブラウザ使用ループの ASCII 図）は 2026-07-13 に提出済み → `~/anicca/skills/browser/SKILL.md` の構成そのもの。

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
