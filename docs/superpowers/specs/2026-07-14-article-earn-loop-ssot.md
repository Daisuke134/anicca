# Article-Earn Loop — 作業 SPEC（唯一の正本 / 随時更新）

> ★このタスク(article-earn loop)の SPEC はこの1ファイルだけ。**新規ファイルを作らない。** 理解が進む度・進捗する度にここを更新（future self と他 agent が status 再検索でトークンを溶かさない為）。
> 関連: 記事ブロック承認状態=`docs/articles/2026-07-12-agent-economy-REVIEW-STATUS.md` / 親spec=`docs/superpowers/specs/2026-07-13-profitable-claude-earn-loops-spec.md`。
> 進捗の二重トラック: このファイル §5 ＋ TaskList tool(#9-25)。

**Goal**: 人間らしい（AI slop ゼロの）日本語+英語の記事を書き、全platformへ publish し、writing で **10k MRR** を no-human-in-the-loop で稼ぐ loop を作る。土台 skill = `~/.openclaw/skills/ai-entity-article-writer`（実測 ~90% 完成。執筆playbook+全publisher+収益化コード[note membership/paywall]+verifier部分+self-improve部分が既に在る）。

---

## 0. ★配置マップ（flip-flop 防止・2026-07-15 実測。場所で迷ったら必ず先にここを読む）

loop は **3箇所に散在**。これが俺の flip-flop（enabled/disabled を何度も言い直した）の根本原因。

| 役割 | 正確な path | 備考 |
|---|---|---|
| scheduler | `~/Library/LaunchAgents/ai.anicca.article-daily.plist` | launchd。**毎日 06:00**。loaded=YES, LastExitStatus=0 |
| loop 実体 | `~/profitable-claude/skills/human-funded/article/article-daily.sh` (88行) | plist が呼ぶ。bounded `claude -p` を1回走らせる（run.sh を直接ではない） |
| skill(執筆+publisher) | `~/.openclaw/skills/ai-entity-article-writer/` （`.claude/skills/ai-entity-article-writer` は**ここへの symlink**） | claude -p pass が使う道具。run.sh / publish-*.sh |
| state | `~/profitable-claude/skills/human-funded/article/state/` | lockdir 等 |
| ★活動ログ(本物) | `~/.openclaw/logs/article-daily.log` | ★`.out`/`.err` は launchd capture で空。実ログは `.log`★ |

**loop の型**: launchd（唯一の scheduler）→ article-daily.sh → mkdir lockdir（daily-driver browser :9222 の競合防止）→ `claude -p` bounded pass が 執筆→publish→`openclaw message send`(telegram)報告。self-register scheduler は使わない。timeout も掛けない（capafy/life-manager が rc=124 で途中死した教訓）。

**定義的状態(2026-07-15、`article-daily.log` で確定)**: ★**loop は壊れてない。毎日 fire して記事を作ってる。**★ 07-12/13/14/15 全て rc=0、今日07-15 06:27 完了。**毎日 JP+EN 記事を執筆 → 5プラットフォーム(zenn/devto/substack-ja/substack-en/note)に draft ステージング → own-eyes 検証 → Telegram報告**（07-14/15 は 5/5 成功、07-13 は note timeout で 4/5）。
- **唯一の恒常故障 = X(Twitter)**: daily-driver session ログアウト、cookie復元も失敗 → **Dais 手動 re-login 要**。
- note は disk逼迫日だけ camofox timeout（07-14/15 は成功）。
- ★**全 draft は公開されてない（設計通り、公開=Dais手動）→ だから「どこにも投稿されてない」ように見える。¥0 の真因 = ①draft が誰にも publish されない ②換金未ON。loop の"生産"は正常。**★
- staged 済で未publish の記事: x402(07-12) / ERC-8004(07-13) / トークン病(07-14) / OpenEvolve(07-15)。
- 途中で pass 自身が実バグを毎日修正して main-internal に push してる（freshness-gate no-op, publish-note fallback, devto timezone 等）= self-heal は部分的に効いてる。

**flip-flop の再発防止（HARD）**: 俺は (a)`~/.openclaw` の run.sh だけ見て「これが loop」と誤認、(b) 空の `.out` を見て「動いてない」と誤認、(c) SKILL.md:121 の古いメモ「old crons DISABLED」を鵜呑み。→ **今後は必ず: ①plist の ProgramArguments が指す実体 ②その script 内の `$LOG` 変数が指すログ、を見る。断片で断定しない。**

---

## 1. 前提となった research（一次ソース）

| # | 発見 | 出典 |
|---|---|---|
| R1 | 記事課金"単体"で自動10k MRR の実例はゼロ。だが人間含めれば $1M/月級が実在。本命メカニズム = **定期購読** | growthinreverse.com（HCR $1M+/月、Lenny $2M+/年）|
| R2 | 10k MRR は moonshot でなく mid-tier。Amy Suto = $22k MRR（42k無料/1,917有料/~3年、+本+consulting） | amysuto.com |
| R3 | note.com top1000 平均 ¥1,515万/年。サブスクが単発の3倍速成長。top1000が全収益の94%独占 | note.jp 公式 |
| R4 | how-to型は narrative型の**1.9倍**の値がつく（note 30万記事） | note.jp（¥1,842 vs ¥983）|
| R5 | 90%+無料で配り paywall=「信頼税」。高頻度cadenceで習慣化してから課金 | HCR/Lenny/Slow Boring |
| R6 | 手数料: Substack 10%+Stripe。note 最大20%+15%積上げ。dev.to/X=換金不可・送客専用 | 各公式 fee page |
| R7 | JP prose best = k16shikano japanese-tech-writing（⭐1422）。EN best = ECC土台+Karpathy型。cody は12フェーズで遅く却下 | gh/gist 実読 |
| R8 | anti-slop: JP=stop-ai-slop-jp（手元にiKora128版と同一）、EN=hardikpandya/stop-slop | gh 実読 |
| R9 | 参考実装（車輪回避）= daigotanaka/social-blog-skills（note+Substack+X横断） | gh |

## 1. 決定事項（整合済み設計）

- **決定① 統合（作り直さない）**: 自作 `ai-entity-article-writer`（40日Dais編集の66ルール）を骨格に残す。市販skillにこの「編集の目・プロセス・publish安全」は無い。
- **k16 は"移植"であって"置換"でない**: 比較実測 = 原本 ~42/50、k16版 ~47/50。差+5は特定7ルール由来（命題型H2禁止・見出しネタバレ排除・空虚予告文削除・命令調弱化・中黒並列排除・段落一トピック化・空虚動詞具体化）。この7ルールだけWRITE工程へ移植する。
- **決定② loop 二層**: 無料funnel（zenn/dev.to/X/tiktok=習慣化&無料リスト育成&送客）／ 換金（note有料+Substack有料購読=**定期購読が土台**、product drop・founding tier・storefrontは後乗せARPU倍化）。
- **決定③ 順序**: SKILL → PUBLISH → MONETIZE → LOOP。
- **記事の型**: how-to型で書く（「このAIが$X稼いだ、あなたが再現する手順」）= narrative の1.9倍の値（R4）。
- 公開ボタンは常にDais手動。cronはdraft生成のみ。NOTE_FORCE_DRAFT等の安全ゲート維持。

## 2. 記事 loop の full ASCII

```
┌──────────────── ENGINE（1記事を作る／毎日回る）────────────────┐
│ TOPIC PICK ─ AIが次ネタ選ぶ（AI-entity/repo、how-to型で）        │
│     ↓                                                          │
│ RESEARCH ─── context7(docs)+crwl(web)+gh + ★実際にRUNして受領書★  │
│     ↓                                                          │
│ WRITE ────── 自作skill骨格 + k16の7ルール移植                    │
│     ├ JP版                                                     │
│     └ EN版（ECC土台+Karpathy型）                               │
│     ↓                                                          │
│ ┌──────── NO-SLOP ゲートスタック ────────┐                     │
│ │ G1 de-slop: stop-ai-slop-jp / stop-slop │                     │
│ │ G2 eval:   fresh adversary /50、<35→書直│                     │
│ │ G3 fact:   Claim|Evidence|Status        │                     │
│ └───────────────┬─────────────────────────┘                    │
│                 ↓                                              │
│ HUMAN FINAL CHECK ─ Dais が各platform draft を目視（公開ボタン）  │
└─────────────────┬──────────────────────────────────────────────┘
                  ↓
┌──────────────── DISTRIBUTION ─────────────────────────────────┐
│ 無料funnel（習慣化・SEO・リスト育成）  換金ノード（金が出る）      │
│ ───────────────────────────────    ─────────────────────      │
│ zenn（無料）─┐                       note 有料/メンバーシップ(JP) │
│ dev.to ──────┼─ 末尾CTA・BIOで ───→  Substack 有料購読(EN/global) │
│ X Articles ──┤     送客              ＋四半期 product drop        │
│ tiktok画像 ──┘                       ＋高額 founding tier         │
└─────────────────┬──────────────────────────────────────────────┘
                  ↓
  VERIFY ── screenshot+URL を state/meta.json に記録
                  ↓
  LEARN ─── 売上/CVR 計測 → PLAYBOOK に自動書戻し（self-improve）
                  ↺ loop
```

## 3. なぜ AI slop が出ないか（入口+出口）

- 入口: k16の7ルールをWRITE工程に入れる = そもそも slop を生まない
- 出口: G1 de-slop（偏愛語・全角ダッシュ・主体の不在・命題型H2・リズム均一・両論併記）→ G2 eval（/50、35未満書直し）→ G3 fact（出典無し断定/幻覚）→ 人間目視（機械が拾えぬ「意味の取りにくさ」）

## 4. 現状の壊れ（PUBLISH 無人化のブロッカー）

| 項目 | 状態 |
|---|---|
| 記事ごと publish script 手書き | ★唯一の無人loopブロッカー。パラメータ化必要 |
| note login | Vue reactivity bug で自動login不可 |
| X セッション | 有効creds無し、再取得必要 |
| tiktok companion | 未実装（publish matrixに名前だけ）|
| 換金ノード | note のみ実装・一度もON していない・¥0。cross-platform orchestrator無し |

## 5. TODO（TaskList #9-25 と同期。順序 B→C→D→E→A。★随時 status 更新★）

方針（2026-07-15 実態反映）: **loop は既に毎日 draft を 5platform に生産できてる。金の blocker は3つだけ = ①X再login ②draft を publish ③換金ON。** 他(VISUALS/gate/self-improve)は品質・堅牢・scale の改善であって初¥の blocker ではない。TikTok は後。

### ★BUILD方法（決定 2026-07-15、Anthropic 裏取り済）= manual-first-then-skillify
- **Option A 採用**（手で1本 GREAT draft にする→gap を skill に焼く→loop 再現→ログで二次研磨）。Option B(盲目で skill 先直し)は非推奨。
- 出典: Anthropic「Agent Skills」= "discover what context Claude actually needs, instead of trying to anticipate it upfront" / "Start with evaluation" / skill-creator の draft→run→human eval→rewrite ループ。実例: gpgkd906/auth9(human review→AI iterate, 20周で収束)。
- **VISUALS ツール（#16、deterministic script として skill に焼く。prose に書かない）**:
  - Mermaid→PNG: `mmdc`(mermaid-cli、md内の```mermaid を一括置換) or mermaid.ink(hosted、Chromium不要)
  - 表→PNG: `node-html-to-image`(puppeteer) or `vercel/satori`
  - eyecatch: satori/node-html-to-image でブランド枠+文字、hero art は image-gen(`mcp blockrun_image`)。★文字は raster model でなく satori で（text崩れ防止）★

### ★TIER 0 — 初¥への最短路（これだけが金の直接 blocker）
- [x] M-X   #15 X re-login ✅DONE(2026-07-15): Dais 手動login → `session_vault.py dump` で vault に bank(285 cookies, x.com banked=True)。creds = `~/.openclaw/identity/social-accounts/x.json`(email kodaisuke@keio.jp + password len15)。
      ★教訓: 生Playwright+高速決め打ちで X anti-bot(電話認証壁)を踏んだ → **browser作業は必ず daily-driver skill(`~/anicca/skills/browser/`)経由・agentic で**（CLAUDE.md の掟）。
      ★★FOREVER-SESSION（実測 robust、二度と調べ直さない）: ①launchd `ai.anicca.session-vault` 30分毎 dump(vault に rotating backup) ②dump に空snapshotガード(`session_vault.py:123`「never overwrite good vault with empty」) ③`ensure_browser.sh` が relaunch 時 restore ④`~/.cloak`(vault+profile)は `disk-autoprune.sh:9` の**保護store**で disk満杯でも消えない。→ **Chromium死/disk圧迫でも profile+credential 残存、開けば既ログイン、手動login不要。**★★
      再login ladder（skill）: `session_vault.py restore` → `keepalive <authed-url>` → x.json creds で self-login。
- [—] M-PUB draft の publish は **保留（Dais 2026-07-15: まだやらない）**。→ 換金(M-MON)も公開が前提なので当面後回し。今は loop の"品質と堅牢"(TIER1)を上げる方に注力。
- [ ] M-MON #23 換金ON: note membership(¥500/月)+ how-to部の paywall / Substack有料tier（コード実在、ONだけ）
→ この3つで **初¥**。以降は下の TIER で 10k MRR へ複利。

### ★問題インベントリ（実測 2026-07-15。実装前に全部潰す。過去の思い込みを実測で訂正済）

**訂正された思い込み（実測で潰した）**:
- ❌「note login 壊れてる(Vue bug)」→ 実測: note-mcp venv=OK / camofox daemon :9377=生存 / .env=有。**依存は健全**。publish-note.sh は 2026-07-12/15 に keychain/clone-path/camofox-profile を多数fix済、`create_draft(session,article)` も generic(line204)。→ **note publish は動く見込み（要: 実draft 1回で実証）**
- ❌「cron 未load」→ 実測: `ai.anicca.article-daily` plist は launchctl に **loaded 済**(status 0)。※但し daily-run.sh は NOTE_TOPIC 無しで no-op + SKILL.md「old crons DISABLED」→ 実挙動 要確認
- ❌「#13 = note新規draft作成が未実装」→ run.sh が呼ぶ `publish-note.sh:204` は create_draft で generic に新draft作る。line49で拒否してたのは別script(note-publish/publish-to-note.sh、未使用系)。→ **publisher は4つとも generic = #13 実質DONE、要実証のみ**

**★P0 SSOT場所（Dais判断が要る、実装の前提）**: `.claude/skills/ai-entity-article-writer` は **openclaw への symlink**（`→ ~/.openclaw/skills/...`）。git は symlink 1個だけtrack、実体は ~/.openclaw(anicca-dais private)。Dais「SSOT=.claude/skills、openclaw編集するな」→ symlink を実コピー化して anicca-project に取り込む移行が必要。**この判断が済むまで skill 本体を編集しない。**

| # | 残問題 | 実態 | タスク |
|---|---|---|---|
| P1 | publisher 実証 | 4つ generic だが 実draft 1回の実証が未（Dais が subagent test を kill、自分でやる） | #13 |
| P2 | VISUALS未配線 | run.sh/publish-note.sh が mermaid/表→PNG を自動化してない。note は mermaid/表 非対応で崩れる | #16 |
| P3 | gate不足 | run.sh gate=language-purity+seo のみ。de-slop/eval「払う価値」/fact 未配線 | #17/#18 |
| P4 | self-improve弱 | `self-improve.sh`=日次ダイジェスト(cron event+reflection+SEO)。L3(crwl→component A/B→funnel実測→keep/revert)でない | #21 |
| P5 | 換金未ON | publish-membership.py等 実装済だが一度もON してない=¥0。SKILL.md §331-341に戦略(membership ¥500/月, ChatGPT研究所 copy)有 | #23 |
| P6 | cron実挙動 | plist loaded だが no-op/disabled の可能性。実際に何をするか要確認 | #25 |
| P7 | X auth | script有、session有効性 未確認 | #15 |

### PART B — skill を動くに
- [~] #13 T1 パラメータ化 — zenn/devto/substack=**DONE**、★残=note新規draft自動作成（#14と結合）★
- [ ] #14 T2 note login Vue reactivity bug 修理
- [ ] #15 T3 X session 再取得
- [x] #16 T4 VISUALS **DONE 2026-07-15**（commit `fbd362a9` @ anicca-dais main-internal, push済）
       配線した実物: `publish-note.sh` = stage1-render(表→PNG, manifest生成) → manifest title を --title と同期 → create_draft(manifest body) → stage2-publish(kroki mermaid→PNG, upload_body_image, update_article=draft_saveのみ)。
       run.sh 契約は不変（stdout=`DRAFT (unpublished) key=...` 1行のみ、診断は全て stderr）。DRAFT-ONLY 温存（publish_article は import ごと不在）。
       WORK dir = `~/.cloak/note-work/note-stage-daily/$$-<ts>`（/tmp 不使用、手動Automatonの共有dirと分離）。
       ★副産物の実バグ修正: `set -euo pipefail` 下の `VAR=$(cmd); EC=$?` は cmd 失敗時に即死し FATAL 分岐へ到達しない。3箇所を `if VAR=$(cmd); then EC=0; else EC=$?; fi` へ。実測再現: `bash -c 'set -euo pipefail; OUT=$(false); EC=$?; echo reached'` は reached を出さず exit 1。★
       検証済(ネットワーク副作用なし): bash -n / py_compile OK、既存回帰 `note-publish/test-de-automaton.py`(INV-1〜5, draft-onlyリーク検査) PASS、引数欠落で `FATAL: --markdown-file --title required` exit 1、stage1 単体実行で `tables=1 mermaids=1` + body に `@@TBL1@@`/`@@FIG1@@` 生成を実測。
       ★未検証 = 実 note.com への実 draft 作成（ネットワーク）。#3 E2E で初めて通す。★
       旧記述（履歴）: ★訂正: "作る"必要なし、既に実装済。gap=日次loopへの配線★
       **adversary verdict 2026-07-15 = FAIL**（CRITICAL 0 / MAJOR 1 / MINOR 2）→ #29 で修理中。
       ★破れなかった不変条件（実測済、二度と疑うな）: DRAFT-ONLY は型レベルで保証されている。note-mcp の `create_draft`/`update_article` は共に `POST /v1/text_notes/draft_save?is_temp_saved=true` のみ(articles.py:292-293)。`ArticleInput`(models.py:100-113) に status/publish フィールドが存在しない = env/引数で公開に化ける道が無い。`publish_article`(articles.py:815) は note_mcp/server.py の MCP tool ハンドラ専用でこの経路に未配線。★
       run.sh 契約も diff 実測で不変を確認（唯一の非 stderr 行 = publish-note.sh:317）。WORK dir の per-run 一意性も確認、手動パイプラインの共有 dir と衝突なし。

- [ ] #29 **#16 の adversary 指摘の修理**（2026-07-15、fresh builder 実行中）
       - **MAJOR: silent degradation が構造化された成功シグナルに露出しない**（publish-note.sh:178-195, 307-314 / run.sh:124-138）。stage1/stage2 失敗時 WARN は stderr のみ + exit 0。run.sh の `ah_record ... "draft"`(124) と META_FILE の jq 構造(129-138) に stage1_ok/stage2_ok が無い → **「画像付き draft が出来た run」と「stage1 が壊れて生MDにフォールバックし mermaid が崩れた draft が出来た run」が meta.json / account-history 上で区別不能**。#16 が直した問題が再発しても誰も気づけない。→ 経路情報を meta.json に露出（stdout 契約は壊さない）。
       - MINOR1: `DRAFT_NUM` 抽出(292)だけ bare な `VAR=$(cmd|grep)` で set -e 防御パターン外。grep 非マッチで FATAL 文言なしに即死 → run.sh 側に「empty URL」という誤解を招くエラーが出る。現状は note-mcp の型契約(`Article.id` 必須 str)が守っているので実害なし。DRAFT_KEY 抽出(286, pre-existing)も同型。
       - MINOR2: cookie キャッシュ `~/.cloak/note-work/note-cookies.json` が temp+rename なしの直接書き込み。手動パイプラインと同時稼働で読み手が JSONDecodeError。→ os.replace で atomic 化。
       ★一般法則: 「best-effort で WARN + exit 0」は、その run が degraded だったことを機械可読な形で残して初めて成立する。残さないなら成功の偽装。★
       **R1修理 = commit `64071733`**（stdout の1行に `stage1_ok=/stage2_ok=` トークン追記 → run.sh:97-98 が grep → meta.json(155-157) + account-history snippet(139)）。MINOR1/2 も修理済（302/308行の set -e ガード、247-254行 mkstemp+os.replace）。回帰スイート PASS を team-lead が自分で実行して確認。

- [x] #30 ★**画像が黙って消える実バグ**（adversary R2 が発見、team-lead が実コードで確認）→ **DONE 2026-07-15 commit `794e6529`**★
       修理の実物（team-lead が自分で grep + 回帰実行して確認）: 空文字消去を廃止し `note-stage2-publish.py:41` で `[画像の埋め込みに失敗しました: {label}]` の**可視プレースホルダ**に置換（人間が draft を見て気づける）。`L70` で `EMBED_SUMMARY embedded=N/M failed=...` を stdout に、1件でも失敗なら `L72 sys.exit(1)`。★`L68 update_article` が `L72 sys.exit(1)` より前 = draft は失敗時も必ず保存される（部分的でも中身のある draft を残す）★。
       設計が正しい理由: **exit code の意味を「プロセスが生きてるか」→「全画像が入ったか」に変えた**ので、publish-note.sh 側の `STAGE2_RC -ne 0 → stage2_ok=false` は無変更のまま正しくなる（真因を直せば下流が自動で直る）。
       追加: `stage2_embedded=N/M` を publish-note.sh の stdout トークン → run.sh → meta.json に配線。**reality-gate(#20) が「何枚中何枚入ったか」を直接読める。**
       回帰スイートに新不変条件 `partial-embed-failure` を追加、`A3_FAIL_UPLOAD` env で失敗注入（ネットワーク不要）。team-lead が自分で実行し `PASS -- all static + behavioral invariants hold (stage1 + stage2 leak-checked, partial-override + multi-infographic + partial-embed-failure)` を確認。
       旧記述（履歴・バグの現物）:
       `note-stage2-publish.py:42,49,54`:
       `except Exception as e: print(f"tbl{i} FAIL ..."); nb=nb.replace(f"@@TBL{i}@@","")`
       - 画像 upload 失敗時、マーカーを**空文字に置換して消す** = 痕跡が残らない（生 `@@TBL1@@` が残る方がまだマシ。壊れたと分かるから）
       - re-raise も sys.exit も無い → `update_article`(L55) が成功すれば **exit 0**
       - `publish-note.sh:322-335` は exit code だけで STAGE2_OK を決める → `stage2_ok=true` が meta.json に載る
       - **結果: N枚中1枚が黙って消えた記事が「成功」として記録される。loop は毎日これをやっている可能性がある。**
       → 目的: `stage2_ok=true` が「要求された画像が全て実際に埋め込まれた」を意味するようにする。draft 自体は残す（部分的でも中身のある draft を残す方が良い）が、成功とは報告しない。
       ★一般法則（#16 の法則の強化版）: **exit code は「プロセスが死ななかったか」しか語らない。「仕事が出来たか」は別に測って別に報告しないと、成功の偽装になる。** per-item の try/except は、失敗カウントを集約して終了ステータスに反映して初めて正当。★
       ★これは reality-gate(#20) が毎日検出すべき失敗クラスの実例 = #20 の仕様の一次資料。★
       既存(実装済): `note-stage2-publish.py`=kroki.io で mermaid→PNG(L27-29)+S3画像upload(upload_body_image)+eyecatch / `note-stage1-render.py`=表→PNG(L21-46)。draft-only 保証コメント有。
       ★真の gap: 日次loop の note 経路 `run.sh→publish-note.sh→create_draft(生MD)` が stage1/stage2 を通さず生markdownを投げてる → note で ```mermaid が崩れ画像無し = 「悪いdraft」の真因。★
       → 作業 = publish-note.sh(生MD経路)を stage1-render→stage2-publish(画像経路)に差し替える配線のみ。
       research copy: ①igapyon「正本MD書き換えない/生成PNGはgit外の使い捨て」を不変条件化 ②drillan `LoginError`分類を stale-cookie 診断に。捨てる: session作り直し(我々のdaily-driver cookie抽出が堅い)/publish(bool)フラグ。
       我々の note publisher は OSS最強クラス(drillan/note-mcp を vendor、S3 upload、draft-safe = review中最強)。
- [ ] #17 T5 de-slop ゲート(stop-ai-slop-jp/stop-slop)配線（今 language+seo のみ）
- [ ] #18 T6 eval「賢い読者/Daisが払うか」/50 + fact 配線（fresh adversary）

### PART C — verifier
- [ ] #20 V1 L4 reality-gate(session restore→ログアウト実見→naturalWidth>0→draft確認、公開ならFAIL)
       ★2026-07-15 発見: reality-gate は「人間を loop から外す許可証」。これが無い限り DRAFT-ONLY 契約(下記 #26)は正しい安全弁であり、外してはならない。順序 = reality-gate 実装 → 契約書換 → 自動公開。★

### PART H — 実 E2E で発覚（2026-07-15、team-lead が実 note.com に draft を作って踏んだ）
- [x] #32 ★**stage2 が update_article に numeric ID を渡していて必ず落ちる**（= 日次 loop の note 経路は配線しても画像が入らない真の理由）★ → **修理 commit `84c6c94f`**（E2E 再実行で検証中）
       **真因（builder が note-mcp 実コードで確定。team-lead の推測は誤りだったので訂正して記録する）**:
       - `update_article` は numeric/key 両方を受理する。だが本文に**単独行の埋め込み対象URL**（YouTube/Twitter/note.com/GitHub/Zenn/Qiita 等。判定 = `note_mcp/utils/markdown_to_html.py:220-241 has_embed_url`）が含まれると、key 取得のため `get_article_via_api(session, numeric_id)` を **numeric のまま**呼ぶ（`articles.py:619`）。ところがその関数自身が numeric を明示 reject する（`articles.py:674-684`）。→ **numeric ID しか持たない状態で「埋め込み対象URLを含む本文」を保存することは note-mcp 内部で構造的に不可能。** KEY を渡せば `_is_article_key_format` が真になりこの壊れた経路を丸ごと迂回する（`articles.py:390-402, 610-624`）。
       - ★team-lead の推測「upload_body_image は numeric を要求する」は**誤り**。`images.py:234-342` 全文確認の結果、**`note_id` 引数は関数本体で一度も参照されていない**。fig1-3 が NUM で成功したのは引数が無視されているから。★
       - 既存の手動パイプライン `note-publish/publish-to-note.sh:44` に `export NOTE_KEY="$KEY"` という**未完成の配線の痕跡**があった（stage2 側は NOTE_KEY を読んでいなかった＝繋がっていない）。今回それを完成させた。
       修理: stage2 が `ARTICLE_ID = KEY or NUM` を update_article に渡す（upload_body_image は NUM のまま = 無視されるので無害）。update_article 失敗時も `EMBED_SUMMARY embedded=0/total failed=update_article:<err>` を必ず出してから exit 1（旧: 例外で無言死し stdout が空 → `stage2_embedded=` が空になるバグも同時修理）。設計判断: 本文保存が失敗した以上「保存された本文に何枚入ったか」は **0 が正しい**。
       回帰: negative test 4件追加。**`git stash` で修理を戻すと6件 FAIL（実バグ再現）、戻すと PASS** = テストが空虚でないことを実証済み。
       未修理（別task化。触らない判断）: `rebuild-note-body.py`（手動 Automaton パイプライン）も NUM のみ渡す同じ古いパターン。Automaton 記事の本文に単独行の埋め込み対象URLが無い限り顕在化しないので trigger するまで触らない。
       ★一般法則: **「動いている」と「引数が使われている」は別。API が引数を受け取ることは、その引数を使うことを意味しない。実コードを読むまで、どの引数が効いているかは分からない。**★
       実出力（証拠、捏造でなく実 tool_result）:
       ```
       stage1 render OK — tables=0 | mermaids=3
       embedding tables/mermaid as images (draft NUM=170244382)
       fig1 / fig2 / fig3                      ← mermaid 3枚の PNG 化と upload_body_image は成功している
       Traceback ... note-stage2-publish.py:68 in main
         await update_article(sess, NUM, ArticleInput(...))
       note_mcp.models.NoteAPIError: Numeric article ID '170244382' is not supported.
         Please use the article key format (e.g., 'n1234567890ab').
       DRAFT (unpublished) key=n3ecfe7a55890 stage1_ok=true stage2_ok=false stage2_embedded=
       ```
       → 画像 upload は成功、本文への埋め込み(update_article)で死ぬ。draft は残るが mermaid 生・画像ゼロ = #16 が直そうとした状態そのもの。
       → 修理方針: `upload_body_image` は numeric ID を要求（NUM で成功している）、`update_article` は key を要求。**stage2 は NUM と KEY の両方が要る**可能性。note-mcp の実シグネチャで確定させること。既存の手動パイプライン `scripts/note-publish/`(成功実績あり) が何を渡しているかに合わせる（推測禁止）。
       → `stage2_embedded=` が空なのは EMBED_SUMMARY 出力前に例外死したため。update_article 失敗時も呼び出し元に伝わるべきか要設計。
       ★**この失敗は #16/#30 の修理が無ければ「成功」と記録されていた。ゲートが仕事をした証拠。** stage2_ok=false が立ち WARN が出た。★
       ★一般法則: **配線を直しても、その先の API 契約が合っているとは限らない。ローカル検証（py_compile/回帰/fixture）は「呼び出しの形」しか検証しない。実 API の ID 形式のような契約違反は、実ネットワークに出るまで絶対に分からない。だから E2E は省略不可。**★

### PART G — セキュリティ（2026-07-15 発見）
- [ ] #31 **note の email/password が `publish-note.sh` に平文ハードコード**（冒頭コメント + 変数デフォルトの2箇所）。`~/.openclaw`(private) に commit 済み。→ env 化 + パスワード rotate が要る。Dais 判断待ち（既存状態なので今夜の作業は止めない）。他の publish script(zenn/devto/substack/x) にも同種が無いか要 grep。

### PART F — no-human-loop への障壁（2026-07-15 実測で判明、pc-repo 調査）
- [ ] #26 **DRAFT-ONLY 契約が設計として埋まっている**。`~/profitable-claude/skills/human-funded/article/article-daily.sh` = 「DRAFT ONLY、絶対に自動公開しない。published フラグ常に false 固定。X の `go`(実公開) 呼び出しは明示禁止。公開は必ず Dais が手動」。
       `skills/human-funded/README.md` に昇格ルート有: 「installer の既存クレデンシャル/OAuth/KYC/1-tap 確認が要る skill だけここに置く。human-in-loop 不要になれば親 `skills/` へ昇格」。
       → article は reality-gate(#20) 完成時に親 skills/ へ昇格させ、契約を自動公開へ書き換えるのが設計者の意図。今は触るな。
- [ ] #27 **個人識別子のハードコード = 他人が install できない**。実測: `article-daily.sh` に Telegram target ID 直書き、`bounty-cli.sh`/`bounty/run.sh`/`connector-cli.sh`/`human-funded/README.md` に GitHub identity `Daisuke134` 直書き。
       同 README に「installer 固有クレデンシャルを OSS コードに焼き込むな、env var で外出しする」という Anti-pattern 規定があるのに違反している状態。→ env 化が汎用化の前提。
- [ ] #28 **収益源が repo に未配線**。`~/profitable-claude/README.md` の Loop 表 = bounty(Algora/GitHub) / affiliate(Amazon JP) / gig(Coconala→MUFG) のみ。note/Substack/dev.to の content royalty は `human-funded/README.md` の「Initial intent」に将来候補として書かれているだけで実配線ゼロ。#23(換金) と対。

### PART D — loop 自走
- [ ] #21 L-a L3 self-improve(日次ダイジェスト→crwl成功記事→component A/B→funnel実測→keep/revert→playbook.json)
- [ ] #22 L-b L2 self-heal(5分毎) + L0 共有基盤(disk-guard/ensure_browser/cdp lease/session_vault)
- [ ] #25 C-cron daily cron/launchd(`ai.anicca.article-daily`) 再有効化 = 自走（今DISABLED）

### PART E — 換金（コードは在る、ONにする）
- [ ] #23 M1 note membership/paywall 実ON + Substack有料tier（¥0→初売上）
- [ ] #24 M2 売上ledger +(後段)product drop/founding tier/Capafy出品

### PART A — その loop で記事を publish（テスト出力）
- [x] #9  [6]-出典 Dais承認（2026-07-15 承認済）
- [ ] #10 REVIEW-STATUS を REVIEWED化
- [ ] #11 JP publish note→zenn→substack-ja→x +verify（tiktok除外）
- [ ] #12 EN publish devto→x +verify（tiktok除外）

## 6. 関連ファイル

- 記事本体: `docs/articles/2026-07-12-how-to-build-the-agent-economy-jp.md`（原本 ~42/50）
- k16比較版: `docs/articles/2026-07-12-how-to-build-the-agent-economy-jp-k16.md`（~47/50）
- 自作skill: `~/.openclaw/skills/ai-entity-article-writer/SKILL.md`（66ルール、正本）
- de-slop: `.claude/skills/stop-ai-slop-jp/SKILL.md`
- 旧spec: `docs/superpowers/specs/2026-06-23-article-publish-monetize-skill.md`、`docs/superpowers/plans/2026-07-12-article-loop.md`
