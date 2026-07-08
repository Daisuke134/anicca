# claude-p Loop Verification + Evidence + Self-Improve Design（2026-07-08）

## 開発環境

- 実装 repo: `~/anicca`（skills/earn, skills/self, skills/report）+ 一部 `~/profitable-claude`
- spec 正本: 本ファイル（anicca-project/docs/superpowers/specs/）
- VCSDD feature: `claude-p-loop-verification`（mode: lean、全フェーズ実施）
- 境界: `~/anicca/skills/report/loop-report.sh`, `~/anicca/skills/earn/{clip,clip-promote,video}/`, `~/anicca/skills/self/{verify-loops*.sh,healthcheck-runtime-loop.sh,founder-loop/}`, `~/profitable-claude/skills/human-funded/{gig,affiliate,bounty}/`。他 instance（automaton/Franklin）の body には触れない。

## Goal（done 条件、全て MUST）

1. claude-p の全 earn loop（clip / clip-promote / video / affiliate / gig / bounty / pm-earner / founder-loop）は、pass ごとに **機械検証済み evidence**（実 URL・実数値・実 tx）を含む mail 報告を keiodaisuke@gmail.com に送る。evidence が無い場合は `none: <理由>` を明記する（空欄は禁止）。
2. 各 loop は自分の output を**自分で検証できる**（下表の検証手段が実装され、検証結果が metrics ledger に記録される）。
3. 各 loop は metrics（views/engagement/応募数/受注/入金/PnL）を JSONL ledger に追跡し、self-improve がその ledger を入力に改善提案→実行する。
4. 失敗は lessons ledger（`state/lessons.jsonl`）に記録され、次 pass の判断に読み込まれる。
5. verify-loops-audit が全 earn loop をカバーし、6h ごとに scorecard mail を送る。stale/broken 検知時は self-fix.sh に自動 escalate する。
6. E2E 完了判定: 各 loop で「実行→投稿/応募→検証→mail（evidence 入り）」の1サイクルが fresh evidence 付きで確認され、fresh-context adversary（Opus 4.8）が PASS を出す。

## 検証アーキテクチャ（loop 別、リサーチ実証済みの手段のみ）

| loop | artifact | 検証手段（実証済み） | metrics ledger | mail evidence（MUST） |
|---|---|---|---|---|
| clip | IG reel URL（`~/.openclaw/state/clip-earn-ledger.jsonl`） | 既存 `self_heal.py` の IG 実ページ読み（維持）+ view/like は browser 実測 | `clip-metrics.jsonl`（新設: reel_url, views, likes, ts） | reel URL + 実測 views |
| clip-promote | campaign 投稿 + Solana payout | 既存 `record-payout.mjs` の on-chain confirmed 検証（維持） | 既存 ledger | 投稿 URL + payout tx |
| video | IG/TikTok 投稿 mp4 + URL | TikTok: `yt-dlp --dump-json --skip-download <url>` で view_count/like_count（無認証実証済み）。IG: 既存 `metrics.py` browser 実測 | 既存 `earn-video-metrics-*.jsonl`（投稿到達で稼働開始） | 投稿 URL + mp4 path + 実測 views |
| affiliate (slideshow) | TikTok slideshow URL + commission | yt-dlp JSON 取得成功可否で存在確認（HTTP 200 は判定不可・実証済み）+ commission-watermark.json | `affiliate-metrics.jsonl`（新設） | slideshow URL + views + commission JPY |
| gig (Coconala) | 応募（`~/gig/applied.jsonl`）・納品物・入金 | 公式 API 不在（実証済み）→ CloakBrowser(:9222) で応募状況/受注/入金ページを実読 | `~/gig/earnings.jsonl` + 新設 `gig-funnel.jsonl`（applied→replied→won→paid） | 応募 URL + funnel 数値 + 入金額 |
| bounty | gated.json survivors + 提出 | board API/実ページ | `bounty-funnel.jsonl`（新設） | checked/survivors/submitted 数 |
| pm-earner | on-chain redeem（`earn-ledger.jsonl`） | `https://data-api.polymarket.com/positions?user=<wallet>`（無認証・実証済み）+ tx status==0x1（既存維持） | 既存 ledger（維持） | realized PnL + tx hash |
| founder-loop | `~/.anicca-founder/state/earn-ledger.jsonl` | on-chain 残高照合 | 既存 ledger | earn_usdc + wallet 残高 |

判定ロジック（何を improve するか、どの案件に応募するか等）は agent 自身が行う。上記は**決定論ツール（検証・記帳）のみ**をコード化する（BUILD AGENTS RIGHT 準拠）。

## P0 修正（現状の障害、全て MUST）

| # | 障害（実証済み） | 修正 |
|---|---|---|
| P0-1 | `loop-report.sh` が AGENTMAIL_API_KEY unset で同日内 SENT/NO-OP 混在（37 SENT vs 46 NO-OP） | script 冒頭で `~/.openclaw/.env` を直接 source して key を自己解決。unset 時は no-op でなく stderr へ ERROR 記録 |
| P0-2 | gig loop が ENOSPC でクラッシュ多発（disk 85%、残 2-4GB） | 承認済み `~/.cache/anicca-*` 回収 + ログ rotate。大物（claudevm/colima）は Dais 承認待ちのまま触れない |
| P0-3 | video loop が warmup day 3→4 に1週間停滞、9日間 noop、投稿ゼロ | warmup 進行条件のバグ特定・修正。投稿フェーズ到達まで |
| P0-4 | `record_earn.py` の on-chain 検証フックが未配線（常に False） | 配線して実収益記帳を有効化 |
| P0-5 | `healthcheck-runtime-loop.sh` 完成済みだが launchd 未配線 | plist 作成・load（pm-earner/founder-loop の死活+stale 監視が有効になる） |
| P0-6 | founder-loop に mail 報告なし | pass 完了ごとに `loop-report.sh founder <summary> <result> <usdc> <evidence>` を配線 |
| P0-7 | evidence 空欄 mail の恒久防止 | `loop-report.sh` に evidence gate: 引数が空/`none` 単独なら reject（exit 1）し、呼び出し元 prompt に `none: <理由>` 形式を義務付け |

## Self-improve 拡張（pm-trade の3層パターンを copy+tweak、新規発明しない）

- pm-trade の `metrics ledger → 改善候補 → fresh adversary gate → 昇格` パターンを clip / video / gig に展開する。
- 各 loop の tmux core STARTUP prompt に「pass 冒頭で lessons.jsonl と metrics ledger を読み、前回より良い選択をする。pass 末尾で mistake があれば lessons.jsonl に1行追記する」を追加（判断は agent、記帳は決定論）。
- 改善の方向: gig=提案文の勝率、clip/video/affiliate=views/engagement、pm=realized PnL。「昨日より今日、今日より明日多く稼ぐ」を metrics ledger の週次比較で machine-checkable にする。

## モデル

全 tmux core = `--model sonnet`（現状維持・確認済み）。self-fix / adversary = Opus 4.8（モデル分業表準拠）。

## 除外（この spec のスコープ外）

autohedge（DeepSeek・別プロジェクト）、daily-nl-report（automaton 帰属）、tier1/tier2（OpenClaw 共通基盤）、Franklin/automaton の body。
