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

## CLIP LOOP — 最新理解（2026-07-14、実コード確認済み）

### 現状（自分の目で確認）
- **最終投稿 2026-07-11 21:47。約3日ゼロ。** launchd `ai.anicca.clip-*` plist 全部 `.disabled-2026-07-12-t04`＝停止中。
- **停止の真因（コード確定）**: `post_reel.py` の bitrate fix で mp4 が ~2MB→**~29MB** に肥大 → IG ブラウザ投稿の `シェア中` spinner が **stall** → publish 確認 5/5 失敗（L206 コメントに実観測記録）。queue に 27-29MB の未投稿7本。
- **品質バグ**（連鎖の元）: 小ファイル時代は投稿できたが IG が **200×200 に潰した**（below_floor）。＝「品質↑=大ファイル=投稿stall」のジレンマ。
- **収益 $0**。bio に affiliate/product link 無し。self-improve ループ（metrics→reflect→次投稿）が clip には無い（記録のみ）。
- 別レール `clip-promote`=ClipAffiliates(promote.fun) per-view 即金、phase idle、$0。

### OSS 探索の結論（gh 一次情報で裏取り）
丸ごと1 repo は **公に存在しない**。最も近い = **darkzOGx/youtube-automation-agent（★1586）** = 生成→投稿→分析→自己改善が本物のコード（`analytics-optimization-agent.js`→`content-strategy-agent.js` の historicalPerformance フィードバック）。ただし **YouTube 単独 / acc作成・warm・マネタイズ無し**。うちは acc/warm/マネタイズ層を既に持つ（業界より先行）。→ **丸ごと採用でなく、darkzOGx の metrics→自己改善ループの設計だけ copy**。

### アーキテクチャ決定
- **1 engine（社会マーケ工場）+ 差替可ノード**。PRODUCE（clip/slideshow/video-moneyprinter/avatar）と MONETIZE（affiliate/ebook/app/clipaffiliates）を差し替えるだけ。loop 機構（LEARN→POST→MEASURE→REFLECT + Reflexion + self-heal）は全 format 共通。今 clip/slideshow/video が別 skill = 断片重複 → 収斂する。
- **1 loop = 1 acc**（fanout）。全アカ共有 loop 禁止（1 ban で連鎖死・直列で遅い）。1 acc = 1 isolated CloakBrowser profile+port + 1 Reflexion state。scale = 同 engine を profile 変えて N 個。
- **10k MRR の鍵 = 金の帰属 + affiliate-finder**。views でなく **$/post** を最適化。per-post trackable link → affiliate dashboard 読取 → 収益を投稿毎に帰属 → Reflexion が金で最適化。勝ち combo（niche×format×hook×offer）を1アカで実証→N アカに clone。

### 7サブタスク（TaskList #1-8 と一致）
| ID | 一手 |
|---|---|
| CLIP-FIX-1 | ✅ DONE 2026-07-14 — 診断: poster/file 無罪、真因=account 投稿制限。出荷: cadence gate(<=1投稿/20h) を run.sh に(commit 54e4f133)。★運用: aiclipsvault は数日休養で自然解除待ち(コードで解けない)★ |

### CLIP-FIX-1 実装ログ（2026-07-14、俺が直接実測）
- @aiclipsvault(port 9223, login済)に queue clip を実投稿 → `outcome=failed, post_url=null`。profile 独立確認で新 reel 出ず = **H1 確定（本当に publish されてない、「シェア中」spinner が真に hang。screenshot 6-sharing.png で spinner 実見）**。verify の false-neg(H2)ではない。
- **★真因 = mp4 の moov atom がファイル末尾（faststart 無し）★**。ffprobe: h264 High/yuv420p/level40/aac = IG 互換。だが moov@末尾 → IG web uploader は 28MB を全DLするまで処理開始できず hang。**小ファイル時代(2MB)は全DLが速く成功 → bitrate fix で28MB化して露呈**、と辻褄一致。
- **fix = `ffmpeg -c copy -movflags +faststart`（再エンコード不要、moov を先頭へ移動、品質不変）**。恒久化 = ①producer の最終エンコードに追加 ②既存 queue 7本を remux。
- ❌ **faststart 仮説は falsified**: `+faststart` remux 版(moov 先頭)を実投稿 → やはり failed/新reel出ず。moov 位置は真因でなかった（検証してよかった、断定せず）。
- ❌ **size 仮説も falsified**: 2.6MB/15s/1080×1920（旧成功サイズ相当）を投稿 → **やはり failed/新reel出ず**。3ファイル(28MB/faststart/2.6MB)が全て `シェア中` で同一 hang = **コンテンツ非依存**。→ ファイルは犯人でない。
- **最有力仮説（未確定）= aiclipsvault の投稿制限**（作成2週間・warming中・status "investigating"・最後の成功~10日前・以降全滅）。web「シェア中」永久spinner は action-block/soft-ban の既知症状。account_status ページは 404（診断にならず）。
- 進行中: 既知原因を検索 subagent で確認中。fix 方針は結果次第（コード修正 or warm延長/休養/別アカ/mobile経路）。★poster のコードは壊れてない可能性が高い（flow は share まで正常到達、IG 側が publish を silently drop）★
| CLIP-FIX-2 | ✅ DONE 2026-07-14 — 真の穴=producer 2重故障(パス切れ+engine消失=07-11以降 clip 生成ゼロ)。fix: scripts を ~/anicca へ移動+再ポイント(97efc624)、engine self-heal、burn_captions に faststart。★E2E 実証: producer フル実走→新clip `_g4l7YkDQwA_EN.mp4` 生成、1080×1920/3.79Mbps/60s/gate通過/faststart=YES。queue 8本全て faststart 化★。残: 60s は長い(Reels 短尺化は LEARN/self-improve で) |
| CLIP-LOOP-3 | ✅ DONE 2026-07-14 — clip_pass.sh(Reflexion harness) 作成。chain=LEARN→PRODUCE(producer)→POST(run.sh instagrapi+telegram)→MEASURE→REFLECT。各LLM step=bounded claude sub-call --no-session-persistence。REFLECT 単体実走で reflection.jsonl に honest next-lever 書込 実証(commit a292316f)。★full-pass E2E は LOOP-4 で cron 配線後★。$/post 最適化は MON-5(Dub.co)後に MEASURE へ配線 |
| CLIP-LOOP-4 | **launchd plist 再有効化**（openclaw でない）。1 acc=1 loop |
| CLIP-MON-5 | ★affiliate-finder ノード新設★ + per-post trackable link + ClipAffiliates 即金 |
| CLIP-OBS-6 | Telegram 報告 + 全アカ dashboard（views/engagement/$）|
| CLIP-SCALE-7 | 勝ち combo を N アカに clone、多platform 展開 |

### ★2026-07-14 session 到達点（clip loop 完成度）★
✅ FIX-1(poster診断: web composer死筋) / FIX-2(producer復旧+品質1080²) / POST-11(instagrapi 無料投稿, reel/DaxPaF9saPA 実証) / OBS-6(Telegram+link, TELEGRAM_SENT=true) / LOOP-3(Reflexion harness clip_pass.sh + cold-start bible + affiliate money bible 埋込) / MON-5 offer取得(★Digistore Q-Money 50% 実promolink https://www.digistore24.com/redir/569951/keiodaisukeaiclips1f031/ , offer.json joined:true★)
⬜ **closed まで残り5手（全部 loop がやる、INV-12）**:
  1. bio-set step — loop が browser で bio に link+sid（instagrapi account_edit は login_required で不可→browser）
  2. LOOP-4 — clip_pass.sh を単一 launchd cron に配線 + aiclipsvault status=ready（旧 clip-producer/clip-proactive 廃止）
  3. MEASURE→$ — sid別 EPC を Digistore dashboard から読み REFLECT に渡す（10k の駆動輪）
  4. skillify #15 — account作+affiliate-finder を skill 化（新アカ自己bootstrap、shared-first/finder-hedge）
  5. shared offer config — 再発見せず共有offer即使う
- 正本 docs: spec §6 / docs/earn/{social-marketing-factory-toolstack,ig-posting-method-graph-api-pivot,ig-posting-restriction-and-warmup-policy,crypto-affiliate-feasibility}.md / docs/loop-engineering/{47-cold-start-bible,49-affiliate-money-playbook,48-master-loop-map}.md
- GMX(agora crypto rail)setup 実測 → docs/earn/gmx-referral-setup.md（本 session 末に orchestrator が verify）
- 実装ファイル: ~/anicca/skills/earn/clip/{clip_pass.sh, run.sh, producer.sh, scripts/instagrapi_post.py}

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
