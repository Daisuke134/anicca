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

## Cadence Contract（health の bar、Dais 2026-07-08 指示）

health の判定基準は「artifact が存在する」ではなく「**今日、契約した頻度で成果が出たか**」とする。各 loop は cadence contract を宣言し、healthcheck はそれで判定する:

| loop | cadence contract（MUST） | 判定（JST 日境界） |
|---|---|---|
| clip | 1 reel/日/アカウント 投稿 | 当日 ledger 行 + live 検証（IG 実ページ） |
| affiliate | 1 slideshow/日 投稿 | 当日 ledger 行 + yt-dlp JSON 取得成功 |
| video | warmup 中: warmup_day が毎日 +1 進行。卒業後: 1 投稿/日 | 当日 audit ledger 行の内容で判定 |
| gig | N 件/日 応募（N は agent が市場を見て設定、下限1）+ funnel 更新 | applied.jsonl 当日行 |
| bounty | 1 巡回/日（checked が増加） | gated.json の checked 増分 |
| pm-earner | 1 pass/時 + redeem 確認/日 | earner.log + ledger |
| founder-loop | 1 pass/日 + ledger 更新 | STATE.md mtime + ledger |

- 当日 21:00 JST までに contract 未達 → healthcheck が self-fix.sh へ escalate（「7日前に投稿があるからOK」は不合格）。
- 日次 scorecard mail: loop ごとに ✅posted-today / ❌missed + **streak（連続達成日数）**を表示。streak が health の KPI。
- 既存 `OUT_STALE_HRS`（30h）方式はこの cadence contract 判定に置き換える。

## EDD（Evaluation-Driven Development、self-improve の bar）

verification（二値、self-heal の bar）と evaluation（スカラー、self-improve の目的関数）を分離する。**pm-trade の openevolve パターン（evaluator→score→adversary gate→昇格）を全 loop に一般化する。**

| loop | evaluation metric（週次 score） | 改善対象（genome） |
|---|---|---|
| clip | views/reel（48h窓）+ follower 増分 + payout USDC | クリップ選定基準・caption・投稿時刻 |
| affiliate | views/slideshow + commission JPY/週 | 商品選定・slideshow 構成 |
| video | views/投稿 + 収益化進捗 | ニッチ・台本・頻度 |
| gig | funnel: 応募→返信率→受注率→入金 JPY/週 | 提案文・案件選定基準・価格 |
| bounty | survivors 発見数/週 + payout | board 選定・gate 条件 |
| pm | realized PnL/週（既存 combined_score、実装済み） | 戦略コード（既存） |

- 各 loop に `evaluator`（metrics ledger → score 算出、決定論）を置き、**「今週 > 先週」を machine-checkable にする**（昨日より今日、今日より明日多く稼ぐの実装形）。
- 改善候補（prompt/戦略ファイルの変更）は fresh adversary（Opus 4.8）gate PASS でのみ昇格（pm-trade の promote_gate.sh を copy+tweak）。
- mistakes は loop ごとの `state/lessons.jsonl` に記録し、pass 冒頭で必読。

## Dashboard（aniccaai.com、Dais 指示）

- 各 loop の状態を `~/anicca/skills/self/telemetry-collect.sh`（既存）を拡張して `loop-registry.json` に集約: {loop名, type, account, status(✅/❌ posted-today), streak, 当日 artifact URL, 週次 metric, 累計収益, model}。
- dashboard-sync（Dais owned）が loop-registry.json を fetch → `apps/landing/public/dashboard.json` に "loops" セクションとして merge → aniccaai.com/dashboard に描画。
- frontend 実装順序は規約通り: gpt-tasteskill → frontend-design → 実ブラウザ検証。
- claude-p loop 自身は landing に直接 write しない（既存の write 制限を維持）。

## Loop Scaling（fleet 増殖、self-improve の一部）

- **scale-eligible 条件（決定論 gate）**: cadence streak ≥7日 AND 週次 evaluation score が閾値超 AND disk 空き ≥5GB。条件を満たした loop type は fleet 拡張可。
- **spawner（ツール、判断は agent）**: `ig-account-create` skill（実証済み: email-only、@aiclipsvault）で新アカウント作成 → loop instance を `loop-registry.jsonl` に登録 → 既存 cli.sh を account 引数でパラメータ化した tmux core + healthcheck plist を自動生成（clip-producer の ANICCA_INSTANCE env パターンを copy）。
- **guardrail（MUST）**: 新アカウントは platform 毎の warmup schedule に従う / 同一 platform の新規作成は N 日に1つ / fleet 上限は config で明示 / ban 検知（投稿失敗連続）で該当 instance を pause し lessons.jsonl に記録。
- 「1アカウントに投稿する clipping」→「数百アカウントに投稿する clipping factory」への道はこの registry+spawner が担う。

## OpenClaw 統合（Dais 指示: OpenClaw を廃止し claude-p に統合）

- 手順: ①cron 棚卸し（enabled 103 jobs を earn投稿系/Life Manager系/インフラ系に分類、実施中）→ ②earn/投稿系 job を claude-p の tmux core / launchd に移植（skill 本体を ~/anicca/skills へ移設、fuel を openai-codex → Anthropic Sonnet に切替）→ ③Life Manager 系も claude-p loop 化 → ④インフラ系は healthcheck-runtime-loop + dashboard collector で置換 → ⑤OpenClaw gateway を disable して7日間並走観察 → ⑥問題なければ削除。
- **削除前の MUST**: ~/.openclaw の state/ledger は anicca-dais repo に push 済みであることを確認（不可侵 store の保全）。最終削除は不可逆 broadcast に当たるため Dais の明示 go で実行。
- 移行対象の確定リストは棚卸し結果を本 spec に追記して確定する。

## 除外（この spec のスコープ外）

autohedge（DeepSeek・別プロジェクト）、daily-nl-report（automaton 帰属）、Franklin/automaton の body。tier1/tier2 は OpenClaw 廃止と同時に healthcheck-runtime-loop 系へ吸収（上記⑥まで現状維持）。
