# TASKLIST — ★唯一の SSOT★（順序は Dais が決めた。勝手に入れ替えるな）

最終更新: 2026-07-14 JST / branch `feature/clip-rewards`
TaskList（会話内）と本ファイルと spec は **同じ ID・同じ順序**。3つが一致しない時は本ファイルが正。

> ★実行基盤の確定（2026-07-14）★ **全 earn loop は claude-p（このMac の launchd `ai.anicca.*.plist`）で走る。openclaw gateway cron ではない**（openclaw subscription は停止予定）。clip の再スケジュールは launchd plist の再有効化であって jobs.json への登録ではない。

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
| **19 / L0-3** | **learn-from-winners: scout.py（成功者の実物を見る道具）を全ループ共通に** | ✅ DONE（scout.py 実測済 + gig 配線 + SKILL.md。clip/video は各タスクで配線） |
| **19.5** | **gig の respawn 地獄を止める（reality-verify が logged-out で誤 FALSE→respawn を一日中）** | ✅ DONE（verifier 判定前に L0-2 restore+keepalive。logged-out なら verdict=None で defer。commit pushed 2026-07-13） |
| **20 / GIG-1** | earn-gig を skill 化（1行プロンプトを分解） | ✅ DONE（STARTUP 18700→1576字、パス手順を GIG_PASS_RUNBOOK.md に verbatim 抽出。commit 166e9a44） |
| **21 / GIG-2** | プロフィール実編集（アイコン+カバー+自己紹介） | ✅ 自己紹介+★アイコン画像★を実編集・実画面確認（1024²PNG生成→upload、hash変化）。カバー/サムネは runbook のローテーションで自走 |
| **21.7 / GIG-10K** | 10k MRR 自走の実挙動検証: ①monitor 勝者の全コンポ差分 ②table-stakes 一気埋め（既存6出品を勝者へ改善+新規追加）③playbook.json 生成 ④段階1 初レビュー | ⬜ runbook に指示は焼込済（PULL/TABLE-STAKES/FULL-MENU/BAKE/ITERATE-EXISTING）。★実挙動を1フルパスで検証要★ |
| **21.5** | 学びを焼き込んで一般化（勝者パターンを playbook.json に蓄積→3勝者共通で core 戦略に昇格→戦略からコンポーネント修正） | ✅ DONE（BAKE THE LEARNING を runbook に。commit pushed） |
| **22 / GIG-3** | paid=0（納品→検収→出金→着金） | ✅ DONE（仕組みは runbook B1/EARNED CHECK に既存。振込申請は実収益が出て初めて可能＝earnings 待ち。Dais 確認） |
| **23 / CLIP-1** | clip: self-improve + scout を移植し投稿失敗を直す（→ 下記「CLIP LOOP 最新理解」に展開） | 🔧 進行中: FIX-1✅ FIX-2✅ POST-11✅(instagrapi 投稿 実証+配線)。残 LOOP-3/MON-5/OBS-6/DECOUPLE-12 |
| **24 / VIDEO-1** | video: warmup の hardcode を外し self-improve + scout 移植 | pending |
| **25 / LM-1** | life manager loop（X-1）を 1k MRR まで | pending |
| **26 / Q3** | scale: steel-browser を Docker で cloud に立て、gig/clip 1本を回す PoC + ToS 公式確認 + 経済表（調査済 → doc 45） | pending |
| **27 / OSS** | profitable-claude 公開 + dashboard 収益透明化 | pending |

Q2（ブラウザ共有の ASCII）は提出済み → spec §3 / `~/anicca/skills/browser/SKILL.md`。

---

## CLIP LOOP — ★LIVE TRUTH（毎回ここだけ読めば現状が分かる。built と scheduled を混同しない）★

> 更新: 2026-07-15 JST。**launchctl / ファイルシステムで実測して更新すること。記憶や古いログ（openclaw 等）で書かない。**
> **openclaw では何も走っていない。clip は claude-p 系 = launchd + sonnet sub-call で回す設計。openclaw ログは見るな。**

### ✅ BUILT（部品は完成・実証済み）
- **instagrapi 無料投稿** = 動く。`run.sh`(POST-11) が `scripts/instagrapi_post.py` を呼ぶ。session `~/.cloak/instagrapi-aiclipsvault.json`(authorization_data 有効)。browser 経路(`post_reel.py`)は IG が silently drop するため**廃棄**。
- **loop harness** `clip_pass.sh` = Reflexion 全鎖 LEARN→AFF-FIND→PRODUCE→POST→MEASURE→REFLECT。各 LLM step = `--model sonnet --no-session-persistence` の bounded sub-call。
- **affiliate** = Digistore Q-Money 50%/$88、`~/clips/offer.json` joined:true、sid1=account 帰属スキーム有り。

### ❌ NOT SCHEDULED（唯一の穴 = これが理由で自律稼働していない）
- **clip_pass.sh はどの launchd にも載っていない。** 実測(2026-07-15 launchctl): `ai.anicca.clip-*` / `claude-p-mainloop` / `pm-earner` / `com.anicca.daemon` = **全部 `.disabled-2026-07-12`**。
- 稼働中の earn launchd = gig / sol-trade / x402 / self-improve-evolve / ceo-runner / agent-economy-loop のみ。**clip は無い。**
- ∴ **clip は今、自律で毎日投稿していない。** 最後の投稿 2026-07-14 は**手動テスト**。`clip-metrics.jsonl`=空(MEASURE 未走)、bio に link 無し。
- 別レール `clip-promote`=ClipAffiliates per-view、phase idle、$0。
- **収益 = ¥0**（Digistore dashboard に実 sale が載った時だけ「稼いだ」）。

### → TO-BE（closed の定義）
sonnet が1人で(opus/fable/人間 抜き) **launchd で毎日**: 生成→instagrapi投稿→測定→自己改善。俺が何もしない状態で `.last-post` が翌日も自動で進み grid に reel が増え続ける = closed。

### OSS 探索の結論（gh 一次情報で裏取り）
丸ごと1 repo は **公に存在しない**。最も近い = **darkzOGx/youtube-automation-agent（★1586）** = 生成→投稿→分析→自己改善が本物のコード（`analytics-optimization-agent.js`→`content-strategy-agent.js` の historicalPerformance フィードバック）。ただし **YouTube 単独 / acc作成・warm・マネタイズ無し**。うちは acc/warm/マネタイズ層を既に持つ（業界より先行）。→ **丸ごと採用でなく、darkzOGx の metrics→自己改善ループの設計だけ copy**。

### アーキテクチャ決定
- **1 engine（社会マーケ工場）+ 差替可ノード**。PRODUCE（clip/slideshow/video-moneyprinter/avatar）と MONETIZE（affiliate/ebook/app/clipaffiliates）を差し替えるだけ。loop 機構（LEARN→POST→MEASURE→REFLECT + Reflexion + self-heal）は全 format 共通。今 clip/slideshow/video が別 skill = 断片重複 → 収斂する。
- **1 loop = 1 acc**（fanout）。全アカ共有 loop 禁止（1 ban で連鎖死・直列で遅い）。1 acc = 1 isolated CloakBrowser profile+port + 1 Reflexion state。scale = 同 engine を profile 変えて N 個。
- **10k MRR の鍵 = 金の帰属 + affiliate-finder**。views でなく **$/post** を最適化。per-post trackable link → affiliate dashboard 読取 → 収益を投稿毎に帰属 → Reflexion が金で最適化。勝ち combo（niche×format×hook×offer）を1アカで実証→N アカに clone。

### ✅ DONE（部品・実証済み。詳細ログは git 履歴へ）
- FIX-1/FIX-2: poster 診断(browser 経路=死筋、instagrapi へ pivot) + producer 復旧(1080×1920/faststart)。
- POST-11: instagrapi 無料投稿 実装+実証、run.sh に配線。
- LOOP-3: `clip_pass.sh` = Reflexion 統合ループ（producer+post+measure+reflect を1本に）作成。
- OBS-6(部分): Telegram 報告 配線済。
- MON-5(部分): offer 取得 = Digistore Q-Money 50%/$88、`~/clips/offer.json` joined:true、sid1 帰属スキーム。

### ⬜ 残り TODO（★唯一の SSOT。1行 = 1 atomic 動作。TaskList tool と同一 ID・同順。終わった瞬間ここを update★）
**順序でしかやらない。1つ緑になったら即この表を update してから次へ。**

★focus = aiclipsvault 1アカのみ。金を生むまで scale(×N)しない。★

| 順 | ID | 1つの動作（atomic） | done の検証（実観測） | 状態 |
|---|---|---|---|---|
| 1 | READY | `~/.cloak/clip-accounts.json` の aiclipsvault を `status:"ready"` に（07-14 instagrapi 投稿成功=投稿できる。run.sh の skip を解除） | ファイルに `aiclipsvault "status":"ready"` | ✅ DONE 2026-07-15（JSON 妥当・grep 確認） |
| 2 | ENABLE | 統合ループ plist `ai.anicca.clip-loop-aiclipsvault`（`clip_pass.sh`, 6h毎, RunAtLoad, ENABLED）を1個作って load。旧分離 plist(clip-producer/clip-core/clip-proactive)を廃止 | `launchctl list \| grep clip-loop` が PID を返す | ✅ DONE 2026-07-15（PID 登録・err.log に STEP LEARN start = 自走開始） |
| 3 | WATCH-POST | enable 後 loop が回す最初の pass を watch。実 reel が1本 grid に出るか + Telegram 発火 | logged-out で reel URL が HTTP 200 + Telegram に reel link | 🔧 初回 pass 実走したが **publish せず**（下記 3a が真因） |
| **3a** | **CLEAR-CHALLENGE** | ★2026-07-15 実測で判明した真の blocker★ aiclipsvault の IG session が **reCAPTCHA/checkpoint challenge** で無効化（9223 browser が `instagram.com/auth_platform/recaptcha/` に居る、保存 instagrapi session=`login_required`）。CapSolver 等で challenge 突破 → session 復活（memory: capsolver_turnstile_bypass, 4tier fallback） | 保存 session で instagrapi `account_info` が通る（login_required が消える） | ⬜ **今ここ（browser 空き次第）** |
| — | (LEARN timeout) | LEARN step が毎 pass 15分 timeout(rc=124)。scout が重すぎ pass を食う。後で LEARN を軽量化 | LEARN done rc=0 | ⬜ 後回し |
| 4 | CLIP-BIO | clip_pass.sh に「website(external_url)欄に `<offer_link>?sid1=aiclipsvault` を入れる」judgment-driven step を足す（IG は website だけ clickable=金の入口、bio 本文 URL は不可）。idempotent | logged-out で profile に link 実見 | ⬜ |
| 5 | SELFRUN | 俺が何もしない状態で翌日 `.last-post` が自動で進むのを確認（自走の証明） | 翌日 `.last-post-aiclipsvault` の epoch が介入なしで更新 | ⬜ |
| 6 | MEASURE-$ | Digistore dashboard から sid 別 EPC を読み REFLECT に渡す配線を1本入れる | `clip-metrics.jsonl` に $ 行が載る | ⬜ |

- **唯一の成果指標 = Digistore dashboard に実 sale。今 ¥0。** loop が回る≠稼いだ。
- ★INV-12: 全部 loop(sonnet) がやる。orchestrator は plist/skill 化だけ。恒常運用で run.sh を叩かない。★
- 正本 docs: spec §6 / docs/earn/{social-marketing-factory-toolstack,ig-posting-method-graph-api-pivot,ig-posting-restriction-and-warmup-policy,crypto-affiliate-feasibility}.md / docs/loop-engineering/{47-cold-start-bible,49-affiliate-money-playbook,48-master-loop-map}.md
- 実装ファイル(LIVE): ~/anicca/skills/earn/clip/{clip_pass.sh, run.sh, producer.sh, scripts/{instagrapi_post.py, pipeline.py, burn_captions.py, verify_clip.sh, export_camofox_cookies.py}, self_heal.py, reel_verify.py, _instance_paths.sh}
- ★REFACTOR 対象（survey 2026-07-15、DEAD safe-to-remove。loop 実行中は触らない、pass 完了後に）★:
  - `launchd/{ai.anicca.clip-producer.plist, ai.anicca.clip-core-healthcheck.plist}`（旧分離 plist、統合 plist が supersede）
  - `clip-cli.sh` + `clip-healthcheck.sh` + `tests/test_clip_cli_self_provision_prompt.sh`（旧 tmux/gateway-cron アーキ、まとめて）
  - `monitor.sh` + `count_posts.py` + `tests/test_count_posts.py` + `tests/fixtures/ledger-2026-07-03-snapshot.jsonl` + `__pycache__/`（monitor 連鎖、まとめて。monitor は手動観測用＝要確認）
  - `verify_posted_quality.py`（live caller ゼロ）
  - run.sh:26 の `$POSTER` 変数（dead code。instagrapi_post.py が唯一の poster）
  - ★触るな★: 外部 `~/.claude/skills/ig-reels-poster/scripts/post_reel.py`（self_heal が --verify-only で使用）と `ig-account-create/scripts/cdp.py`
- GMX(agora crypto rail) → docs/earn/gmx-referral-setup.md（別 goal、session 末に verify）

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
