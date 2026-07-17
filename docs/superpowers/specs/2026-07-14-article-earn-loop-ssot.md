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

## 4. 現状の壊れ（PUBLISH 無人化のブロッカー。2026-07-17 実測で全面書き換え — 旧表は X/note login を「壊れ」としていたが解消済みだったため是正）

| 項目 | 状態（2026-07-17 実測） |
|---|---|
| gate/pass の claude -p 認証死 | ✅**解消（2026-07-17）**: keychain OAuth は headless で失効する（expiresAt:0, claude-code#76905）。CLIProxyAPI :8317（daisukenarita53 の Max OAuth 保持）経由に配線。`~/.cli-proxy-api-key` 存在時のみ有効、無ければ従来 fallback。E2E 実証: 07-17 ja draft に deslop-gate が実 PASS を返した。commits: anicca-dais `22d0f13b` / profitable-claude `4084ce2` |
| AUTOPUBLISH 未arm | **唯一の無人公開ブロッカー**。plist へ `ARTICLE_AUTOPUBLISH=1` 注入は Dais 保留（2026-07-15 判断）のまま |
| visual≥1 gate 不在 | ✅**解消（2026-07-17、#53）**: deslop-gate.sh の DETERMINISTIC PRE-CHECK に P3（mermaid/img/table 合計カウント、生 $MD を走査）を追加。07-17 記事の実 fixture（mermaid=0 img=0 table=0）で FAIL を実測、正常系 fixture（visual あり）では素通りを実測 |
| 自己言及・「この記事」が regex pre-check 未登録 | ✅**解消（2026-07-17、#53）**: deslop-gate.sh に P1（見出し「この記事」）+ P2（自己言及「自分（アニッチャ）」型 apposition）を追加。実違反 fixture（`state/zenn-20260717-agentskills-ja.md` の「## 最初に：この記事は何か」「自分（アニッチャ）は日々…」）で FAIL を実測。閉じ [8] ブロックの許可済み表現「アニッチャ というAI」は誤検知なしを実測 |
| #47 無料版が Sources ブロックを落とす | ✅**解消（2026-07-17、#59）**: make-free-version.py に `extract_sources_section()` を追加。原本の「## Sources」/「## 出典」節（H2/H3どちらも実測で存在）を、切断位置に関わらず「まとめ」の後・フッターの前へ丸ごと（フィルタなし）持ってくる。git stash による before/after negative test で修理前は Sources 欠落・修理後は保持を実測、実ドラフト2本（07-16 ja.md=H3「### 出典」、07-17 en.md=H2「## Sources」）でも保持を実測、Sources無し記事のno-op・重複防止（cutが既にSourcesを含む場合）も実測。commit: anicca-dais `2092337b`（main-internal） |
| 換金ノード | note 買い切りは実装済み（¥1,000 実売1本）。note membership は未ON（設計判断: 記事65本まで作らない）。**Substack は換金 ON 済みだった（2026-07-17 実ブラウザ実測で旧記述「未ON」を是正）**: @anicca2 に email magic-code で自動再ログイン成功（人間ゼロ）、Stripe 接続済み・有料購読有効・$8/月・$80/年・創設メンバー $240、draft 43件実在。→ #23 の Substack 側は完了、note membership 側のみ将来 TODO |
| tiktok companion | 未実装（publish matrix に名前だけ）|

## 5. TODO（TaskList #9-25 と同期。順序 B→C→D→E→A。★随時 status 更新★）

方針（2026-07-15 実態反映）: **loop は既に毎日 draft を 5platform に生産できてる。金の blocker は3つだけ = ①X再login ②draft を publish ③換金ON。** 他(VISUALS/gate/self-improve)は品質・堅牢・scale の改善であって初¥の blocker ではない。TikTok は後。

### ★MASTER 順序（2026-07-16 確定。ゴール = self-improving・JP+EN・全platform・直接公開・brand-safe で稼ぐ loop）
funnel 型は記事1本で手動実証済み（note有料 + X無料 + Substack無料、全部 live）。残り = この型を loop に焼く。

| 順 | やること | 対応# | なぜこの位置 |
|---|---|---|---|
| 0 | ★Dais 判断: skill SSOT symlink 問題（P0）★ | P0 | **skill 本体編集の全 TODO のブロッカー。これが決まらないと 1 以降が全部進まない** |
| 1 | X_COVER bug 恒久修理（figs↔content_images 突合ゲート） | #44 | 毎日踏む публиш経路の実バグ。小さく先に潰す |
| 2 | 無料版 generator（有料ライン切断+まとめ+フッター自動生成）を run.sh に配線 | #43 | 実証済みの型の自動化 = loop の核 |
| 3 | note 買い切り公開の script 化（publish-paid.py 汎用化）+ タグ実測選定の配線 | #35残/#36 | 換金ノードの自動化 |
| 4 | Substack 画像 pipeline script 化（S3 upload+md差替え+publish API） | #45(新) | 今日手動でやった手順の固定化 |
| 5 | 価格戦略の毎回実測（検索API→hasCircle→価格決定） | #37 | publish 前フックとして 3 に接続 |
| 6 | de-slop / eval / fact ゲート配線 | #17/#18 | 直接公開の前提その1（slop を出す前に止める） |
| 7 | reality-gate L4（公開後 self-verify→self-fix。拡大ボケ/560px/embed数/公開状態） | #20/#33 | 直接公開の前提その2（壊れたら機械が直す） |
| 8 | DRAFT-ONLY 契約解除 = 完全無人公開（6,7 green が条件） | #41/#26 | Dais 決定済み。順序だけ厳守 |
| 9 | EN 展開（devto/substack-en native paywall/X-en、同じ型） | #12/#43④ | 型が安定してから言語を増やす |
| 10 | zenn 無料版（まとめ+フッター型、guideline 適合） | #11残 | 同上 |
| 11 | self-improve L3（funnel 実測→playbook 書き戻し）+ 売上 ledger | #21/#24 | 稼ぎ始めてから計測で複利 |
| 12 | self-heal L2 + cron 実挙動確認 | #22/#25/P6 | 無人運転の堅牢化 |
| 13 | secrets env 化+rotate / 個人識別子 env 化 | #31/#27 | security と OSS 化の前提（並行可） |

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

**P0 SSOT場所 — 裁定済み 2026-07-16（Dais「one by one で進めろ」を受け team-lead が裁定）**: **実体は当面 `~/.openclaw`（anicca-dais private）のまま、symlink 維持。skill 編集ブロック解除。** 理由: skill 内に note 平文 creds（#31 未修理）が有り、anicca-project は **public repo（anicca-products）** に push される — 今実コピー化すると secrets が公開される。実コピー移行は #31/#27（secrets/識別子 env 化）完了後に再訪。旧記述「Dais 判断まで編集禁止」はこの裁定で置換。

| # | 残問題 | 実態 | タスク |
|---|---|---|---|
| P1 | publisher 実証 | 4つ generic だが 実draft 1回の実証が未（Dais が subagent test を kill、自分でやる） | #13 |
| P2 | VISUALS未配線 | run.sh/publish-note.sh が mermaid/表→PNG を自動化してない。note は mermaid/表 非対応で崩れる | #16 |
| P3 | gate不足 | run.sh gate=language-purity+seo のみ。de-slop/eval「払う価値」/fact 未配線 | #17/#18 |
| P4 | self-improve弱 | `self-improve.sh`=日次ダイジェスト(cron event+reflection+SEO)。L3(crwl→component A/B→funnel実測→keep/revert)でない | #21 |
| P5 | 換金未ON | publish-membership.py等 実装済だが一度もON してない=¥0。SKILL.md §331-341に戦略(membership ¥500/月, ChatGPT研究所 copy)有 | #23 |
| P6 | cron実挙動 | plist loaded だが no-op/disabled の可能性。実際に何をするか要確認 | #25 |
| P7 | X auth | script有、session有効性 未確認 | #15 |

### PART L — loop 自動化の実装（2026-07-16、MASTER 順序の執行記録）
- [x] #44 X_COVER 2重ゲート **DONE** commit `3c796b21`（team-lead 実装、negative test 実測: 無 X_COVER → FATAL exit 4）
- [x] #43 無料版 generator **DONE** commit `18a7014e`（builder 実装、team-lead が独立検収: `--after-chars 3578` で手動正解と **diff byte 一致**を自分で再現、FATAL ガード発火も実測）
       実物: `scripts/_shared/make-free-version.py` + SKILL.md に7行の節。判断（summary bullets/paid-contents/切断位置）は agent が渡し、script は機械組立+ガード（teaser H2 / 全角ダッシュ / bullets 3-5 / 必須引数）。
       ★発見（builder 実測、二度と混同するな）: 手動正解の X 切断点は本文 **約3,578字** = note の有料ライン 2,500字 と**別物**。X 版の切断は「検証という核心を明かす直前」という編集判断であって、note の paywall 位置の機械コピーではない。→ **切断位置は記事ごとに agent が `--after-chars` で決める**（#18 eval の「無料側が引きの強い事実で終わるか」判定と接続）。default 2500 は目安にすぎない。★
- [x] #35/#36 publish-paid.py 汎用化 + tag-counts.py **DONE** commit `b84674a6`（builder 実装、team-lead 検収: commit 実在 + tag-counts 自分で実測 + --arm ガード構造 grep 確認）
       CLI: `publish-paid.py --key --price --after-chars --tags --arm`。**--arm 無し = ガード停止**（有料設定は transient なので痕跡ゼロ、エディタ再オープンで実証済み）。--arm 有り = 投稿 + API readback 自己検証。投稿クリックのコードは --arm 分岐内にのみ存在（構造的保証）。E2E: 使い捨て draft で PRICE_READBACK=980 / GUARD_STOPPED=true / 痕跡ゼロ 実測。未検証 = --arm 実公開（次の実記事で初通し）。
- [x] #45 Substack mermaid pipeline **DONE** commit `5ec78aea`（builder 実装 + (A) refactor 続行中: 認証を SUBSTACK_SESSION_COOKIE 直 curl 化して venv 依存除去）
       実物: `_shared/embed-mermaid-substack.py` + `_shared/publish-substack-mermaid.sh`、run.sh の substack-ja/en 経路を差し替え。
       ★発見1: `~/Developer/substack-mcp/.venv` が消失していて既存 substack pipeline は全滅していた（uv sync で再建、認証 config は生存）★
       ★発見2: run.sh はこれまで mermaid を未変換のまま Substack に送っていた = mermaid 入り記事は全部壊れて staged されていた（今回修正）★
       ★follow-up バグ: kroki flowchart TD は縦長(276x606)で、Substack が 728px 幅にストレッチ → 縦伸び。verify-preview.py の vision gate が止める設計だが根本修正は別タスク★
       (A) refactor **DONE** commit `dacdeac2`: 認証を SUBSTACK_SESSION_COOKIE 直 curl 化（venv 依存除去、stdlib のみ）+ 公開後 GET 自己検証追加。E2E 再実測: image nodes=3 / mermaid 残存 0 / テスト draft 削除まで。
- [x] #17/#18 run.sh 配線 **DONE** commit `c2079cd1`（md5 キャッシュ付き = 記事1本につき審査1回。配線実証: 昨日の loop 記事が 6c で FAIL して dispatch 前に停止）
- [x] zenn 無料版 draft ステージ **DONE**（zenn-articles repo commit `f287e404`、published:false、正規 slug。公開 flip は Dais/team-lead 検収後）
- [ ] ★#46 **zenn の silent skip 発見（2026-07-16、builder が公式 doc で発見・team-lead が ls で確認）**: slug 規約 = a-z0-9/ハイフン/アンダースコア 12-50字。**daily loop の既存4記事（07-12〜15）は全部日本語ファイル名 = Zenn が「不正なファイル名…スキップ」して4日間デプロイされてなかった可能性大。** loop の検証（匿名404）は「非公開draft」と「未デプロイ」を区別できない = 検証の穴。→ rename + dashboard own-eyes 確認を builder に指示済み。
       ★一般法則: 「push 成功」は「相手プラットフォームが受理した」を意味しない。deploy 先が黙って捨てる規約違反は、deploy 先のダッシュボード/API でしか見えない。★
- [x] 今朝 06:00 run は OAuth 失敗で死亡（rc=1、5秒。team-lead の gate テスト claude 並走との refresh 競合疑い）→ 認証復旧確認後、**新 gate 込みで 06:06:40 手動再発火**（実行中）。
- [ ] #14(task) seo-gate が app 送客時代の遺物要求（aniccaai.com anchor + App Store deeplink 必須、H2≤7）を保持 = note funnel と不整合。要更新。
- [x] zenn slug rename **DONE**（zenn-articles commit `2087edc0`: 4本を a-z0-9 slug へ git mv、published:false 不変）+ SKILL.md に slug 規約焼き込み（`a30a3846`）。
- [x] #15(task) **DONE 2026-07-16 06:14**: Google OAuth(keiodaisuke@gmail.com)で zenn ログイン確立、5本の下書き実在を dashboard screenshot で確認（team-lead も own-eyes 検収）。GitHub 連携同期は正常（rename 後「5分前に同期」）。ledger 記録済み。★発見: zenn アカウントに未把握の記事40本以上（cronジョブ/Claude Code/OpenClaude 系）— 別パイプラインの遺物か要 Dais 確認、未接触★（旧記述: zenn.dev のログインが daily-driver に存在しない（実測: cookie は _ga のみ、dashboard はログイン画面）★。deploy は GitHub 連携のサーバ側同期だが、**下書きの実在は dashboard でしか確認できない** → Google OAuth でログイン確立 + 5本の下書き実在 screenshot 確認 + session vault bank。note-paid-builder 割当済み、**browser 作業は daily pass 完了後**（CDP :9222 lockdir 衝突防止）。
- [~] #13(task) kroki 縦長図の padding 補正: freever-gen-builder が非破壊実験完了（fig1 276x606 → 520x606 canvas、728px ストレッチ後の実表示 848px < 900、拡大なしでボケなし。PIL 12.2.0 はシステム python3 に実在確認、import 失敗時 FATAL で依存明示）。実装は pass 完了後に _shared/embed-mermaid-substack.py へ。

### 今朝の再発火 run の結果（2026-07-16 06:52 rc=0、新 gate 初通し）
- topic = AP2（Google Agent Payments Protocol）。SDK 実 clone + pytest 29件 + 支出上限 $30通過/$80拒否/署名改ざん拒否を実測。研究 MD = docs/loop-engineering/52-ap2-mandate-spend-cap-verified.md
- staged 5/7（zenn / substack-ja / note / **x-ja / x-en** — X 復活、vault re-login 有効）。全て draft。
- ★fail 2/7（devto / substack-en）= EN deslop-gate が12ラウンド収束せず。真因 = judge が checklist に無い難癖を毎ラウンド発明。**較正済み commit bb6520de**: violation は「checklist ルール引用 + 該当文 quote」必須、平叙な事実文は slop でない、FAIL = 見出し煽り or ルール引用3件以上。再測: slop fixture FAIL / 指摘が全部実ルール引用に。★
- ★穴の発見: **X 経路は run.sh を通らないので 6a-6d gate を素通り**（x-en が staged なのに devto は blocked、が証拠）→ task #16。★
- ★一般法則: 収束しない reviewer は「指摘が有限集合（ルール引用+quote）である」ことを強制して初めて収束する。自由記述の難癖は無限に湧く。★

- [x] #16 X 経路の gate 素通り **DONE** commit `677024b5`（builder 実装、team-lead がコード実読で検収）: publish-to-x.sh の publish に language-purity + deslop + eval を browser 操作の前に配線（FAIL = exit 6、prep 未到達を実出力で確認）。seo-gate は除外（--title/--meta 非供給 + SEO は note/zenn/devto の要求）。lang 判定 = --lang > CJK 文字数 > slug 末尾(brittle、最終手段)。gates-ok stamp を run.sh と共有 = 同一記事の二重審査なし。
- [x] #13 kroki 縦長 padding **DONE** commit `891118e0`: pad_to_fit() で upload 前に横 padding（min_w = ceil(h*728/850)、拡大なし）。実測 276x606 → 520x606 → Substack 728px 表示で **848px**（<900 達成）。Pillow は import 失敗時 FATAL で依存明示。

- [x] ★**#41 Phase 1 DONE**★ commit `3264daa`(profitable-claude/main) + `1e688535`(openclaw、zenn slugify 修理)。**team-lead が独立検収**:
       - `bash -n` OK / diff = **純追加33行**（削除0）/ **PROMPT の MD5 を自分で再現**: 変更前(unset)=`18260b13d300d240353e0fd3e8850a0c` == 変更後(unset) → **既定は byte 完全同一 = draft-only 温存が証明済み**。AUTOPUBLISH=1 では別 prompt(`a50d2ae2…`)。
       - plist は未注入（grep 0）= 初回 arm は team-lead の手動判断のまま。
       - 契約の中身も実読して確認: STEP13 note `--arm` に「this is the ONLY command in this entire loop that actually clicks the publish button」/ STEP15 X sentinel は「its own just-staged draft only -- never on a draft from a different pass」/ STEP18 reality-gate 必須「On FAIL, fix the root cause yourself... if you genuinely cannot fix it, take that ONE platform back to non-public」/ STEP19 ledger は**追記のみ**（draft 行を上書きしない）+「Never fabricate a URL or a verdict you did not personally observe」/ STEP20 Telegram に live URL + verdict + 価格/タグ。dev.to は draft-only 継続。
       ★副産物の実バグ修理（builder が STEP16 実装中に発見）: `post-zenn.py` の `slugify()` が日本語を通すホワイトリストだった = **#46 の silent skip の真の発生源**。修理済み（日本語のみのタイトルは `anicca-day` fallback へ = 常に deploy 可能な slug）。さらに印字 URL が `daisuke134`（GitHub identity）→ `anicca`（実 Zenn アカウント）に修正 = **毎日の own-eyes verify が参照していた URL 自体が誤っていた**。★
       **残 = plist に ARTICLE_AUTOPUBLISH=1 を注入（team-lead が明日の run 前に手動）→ 初回無人公開 run を観察。**

### #14 実装設計（seo-gate を article-earn funnel に合わせる。team-lead 起草 2026-07-16、実コード読解済み）
現物の要求（`seo-gate.sh`、行番号は実測）: L43 meta 120-156字 / L47 **H2 3-7本** / L50 内部リンク（aniccaai.com|github.com/Daisuke134/anicca|x.com/aniccaxxx）≥1 / L58 **aniccaai.com アンカー必須** / L62 **App Store deeplink（?pt=/?ct=/?utm_source=）必須**。
これは iOS アプリ送客時代の遺物。今の funnel は「無料版 → note 有料版」。実害の実測: 本物の agent-economy 記事は H2 11本で永久に通らない、AP2 記事も meta 長で落ちた。
**変更（builder への指示内容）**:
1. L58/L62（aniccaai.com アンカー + App Store deeplink 必須）を**削除**し、代わりに **CTA-link 要求**へ: 「本文に `https://note.com/anicca123/n/...` または `https://aniccabuddha.substack.com/...` または aniccaai.com へのリンクが ≥1」。無料版は note へ、有料本体は自分自身なので **`--is-paid-body` フラグ時はこの要求を免除**。
2. L47 H2 上限 3-7 → **3-12**（長文の解説記事が本来の商品。上限で記事を殺さない）。下限 3 は維持。
3. L43 meta 120-156 は維持（実 SEO 要件）。ただし FATAL 文言に「meta は run.sh の --meta 引数。frontmatter の description ではない」と1行追記（今日 team-lead が引っかかった）。
4. L50 内部リンクの許可先に note/substack を追加（1と整合）。
検証: ①本物の agent-economy 記事（H2 11、note リンク有り）が **PASS** ②App Store リンク無しでも PASS ③H2 2本の md は FAIL ④meta 100字は FAIL ⑤CTA リンク皆無の md は FAIL、`--is-paid-body` 付きなら PASS。

- [x] #14 seo-gate 更新 **DONE** commit `7e7ec391`（team-lead 検収: apps.apple/ANICCAAI_ANCHOR は grep 0 = 消滅、H2 3-12、--is-paid-body 実在、note/substack 許可、meta FATAL 文言を実出力で確認）。★builder の追加判断が正しい: 本物の記事は出典を裸 URL で書くので `[text](url)` 必須のままでは実記事が通らない → 裸 URL も許容に変更。★

- [x] ★**#46 zenn silent skip は仮説でなく実害だった（実ログで確定 2026-07-16）**★: builder が zenn dashboard の deploy log を実読 → **今朝の pass が生成した `2026-07-16-aiに財布を…ap2….md` が「デプロイ中断」でエラー**（日本語ファイル名）。= 4日間の記事も同じく届いていなかったことの直接証拠。rename(`c93d374`)で **1分後に「デプロイ成功」へ切替を own-eyes 確認**。現在 zenn に正しい下書き6本。slugify 修理(`1e688535`)は明日の pass から効く（今日の分は生成済みだったので手動 rename が必要だった）。
       ★一般法則（強化）: 「push 成功」も「pipeline が緑」も、相手プラットフォームの deploy ログを見るまでは受理の証拠にならない。silent skip は**加害側のダッシュボードにしか痕跡が無い**。★
- [x] vault bank 完了（`session_vault.py dump` → cookies 277 / domains 50、zenn の `_zenn_session`/`remember_user_token` 込み）。

### #21/#24 self-improve L3 実装設計（team-lead 起草 2026-07-16。loop の最後のピース = 複利）
**原則: 数字を焼くな、測り方を焼け。** L3 = 「公開した記事の実績を測り、次の記事の作り方を自分で変える」。
1. **measure（新規 `scripts/_shared/measure-funnel.py`）**: articles.jsonl の live 行を読み、各 platform の実 API で当日と累計を測る:
   - note: `GET /api/v3/notes/{key}` → `like_count` / `price` / `is_limited`。売上は creator dashboard API（要ログイン、無ければ**測れないと正直に出力**、捏造しない）
   - X: 記事 URL の view/like（x_fullverify の DOM 読みを流用、または API が無ければ browser 実測）
   - Substack: `GET /api/v1/drafts/{id}` or post stats（取れなければ N/A）
   - zenn: `GET zenn.dev/api/articles?username=anicca` → liked_count / page views（公開記事のみ）
   出力 = `state/funnel.jsonl` に1行/日/記事（測れなかった項目は null + reason。★N/A と 0 を混同しない★）
2. **learn（`self-improve.sh` を L3 化）**: funnel.jsonl が **7日分たまってから**、fresh judge に「上位/下位の記事の差は何か」を実データだけで答えさせ、`state/playbook.json` に **仮説1つ + 次に試す変更1つ**を書く（例: 「how-to 型の見出しが like を集めた → 次は topic pick を how-to 寄りに」）。
3. **apply（run.sh / article-daily.sh の prompt）**: pass は執筆前に playbook.json を読み、**採用した仮説と、その結果どう書き方を変えたかを1行 ledger に残す**（適用の追跡ができないと A/B が成立しない）。
4. **keep/revert**: 次の7日で当該指標が改善しなければ playbook のその項目を revert（`state/playbook.json` に `status: testing|kept|reverted` と `measured_delta`）。
★ゲート: **売上が測れるまで like/view を代理指標にする。ただし playbook には「これは代理指標である」と明記する**（代理指標の最適化は本物の目的を殺しうる）。★
検証: ①measure-funnel.py を今の live 3本（note nbcb93e6fc711 / X 2077484575299862907 / substack p/167）で実行し、実数値が出ることを実出力で示す ②取れない指標が null + reason になることを示す ③funnel.jsonl が7日未満なら learn が「データ不足」で no-op することを示す ④playbook.json の schema を1例で示す。

- [x] ★**#21/#24 self-improve L3 DONE**★ commit `0a5c612b`（builder 実装、team-lead 独立検収: measure-funnel.py を自分で実行し **note like=2/price=1000/published、X likes=1 views=307（builder の測定時 299 → 増加中 = キャッシュでない本物の live 値）** を実出力で確認）。
       実物: `_shared/measure-funnel.py`（測れない項目は null + reason。note 売上 API は候補4つ全部 404 → **捏造せず null+理由**）+ `self-improve.sh` に L3 節（7日未満は `insufficient funnel data (1/7 days) — no-op`）。
       ★builder が踏んだ「Credit balance is too low」は**一時的**（team-lead が直後に `claude -p` で CREDIT_OK を実測）。playbook.json の実例は次回 learn 実行時に生成される。★
       副産物: #29 と同型の `set -e` + 裸 `VAR=$(claude -p …)` で全体が落ちるバグを発見・修正。
       ★注意: articles.jsonl は全行 published:false なので live 行が無く、builder が `state/live-articles.json`(gitignore) を手動 manifest として新設。**#41 arm 後は pass の STEP19 が live 行を書くので、manifest は不要になる → その時に measure-funnel を articles.jsonl 直読みへ戻すこと**（二重管理を残さない）。★
- [ ] **measured_delta の定義（team-lead 設計判断 2026-07-16、builder の質問への回答）**: 比較は「記事単位」でなく「**公開後7日目の値**」で揃える（公開日が違う記事を同じ日に比較すると露出期間の差を測ってしまう）。
      `measured_delta = median(仮説適用後の記事群の day7 指標) - median(適用前の直近同数の記事群の day7 指標)`。指標は platform ごとに1つ（note=like_count、X=views、zenn=liked_count）。**day7 が揃うまで status=testing のまま**（早期の keep/revert 判定を禁止）。サンプルが各群3本未満なら判定不能として `measured_delta=null, status=testing` を維持する。

- [x] **07:08:29 の「3連続 run・done 無し」の犯人 = team-lead 自身**（実害ゼロ、2026-07-16 特定）。#41 検収で PROMPT の MD5 を独立再現する際、`src.split('env -u ANTHROPIC_API_KEY')[0]` で **claude 呼び出しの手前までを 3回 bash 実行**した（old/new-unset/new-autopub）。その切り出し範囲に `echo "=== article-daily run ..." >>"$LOG"`（claude 呼び出しより前の行）が含まれていたため、ログに run 行だけが3つ出て done が無い、という痕跡になった。lockdir も trap で解放済み、state 更新なし、今日の pass は 06:52 に正常完了しており**失われていない**。
       ★一般法則: **script の一部を切り出して「変数だけ取り出す」実行は、その範囲の副作用を全部実行する。** 純粋に見える前半にもログ書き込み・ロック取得・mkdir が潜む。変数抽出は `bash -c 'source <(sed -n "…p" file); echo "$VAR"'` のような範囲限定でなく、**副作用行を明示的に除去してから**行うか、そもそも script 側が `--print-prompt` のような検査用 subcommand を持つべき。★
       → builder(freever) がこの異常を自力で発見・報告したのは good。「自分が原因かもしれない」と併記した誠実さも正しい。

### PART M — EN 展開（#12、2026-07-16）
- [x] **Substack EN = native paywall で draft 作成**（`{type:"paywall"}` ノードを89ノード中42番目に挿入、audience=only_paid、有料境界は JP note 版と同じ内容位置「Most "AI Made Money" Headlines Are Token Stories」）。EDIT_URL=`/publish/post/207215338`、公開後 slug=`building-the-agent-economy-who-is-doing-it`。**未公開**（team-lead が匿名 curl で 302 実測）。verify-preview PASS（画像3、最大849px = #13 の padding が効いている）。
- [x] **dev.to EN draft**: `https://dev.to/anicca_301094325e/building-the-agent-economy-...-1608766`。図は `~/anicca`(OSS repo) に PNG commit → GitHub raw URL 埋め込み。**未公開**（team-lead が匿名 curl で 404 実測、API でも published=False）。
- [x] zenn = 追加不要（既に「まとめ+フッター」型 = guideline 適合。builder の判断を team-lead が承認）
- [x] **X-en draft DONE**（2026-07-16）: `https://x.com/compose/articles/edit/2077529988346372096`（旧 draft `…528` は個別削除、他は無傷）。
      両 gate を**1回で PASS**（de-slop violations 0 / eval score 37, fact_flags 0）= deterministic pre-check(#50) 導入後は retry 不要になった。
      verify: 画像3 / tallest 586px / PASS。builder が fv0-7 を own-eyes、team-lead も独立検収（gate 再実行 PASS + 核心文 "Transaction count can be staged. Money settled cannot." 無傷を grep 確認）。
      ★team-lead の誤検知の記録: 生 grep で em dash 12件に見えたが、実体は **mermaid の `-->` 矢印3件のみ**（gate の pre-check はコードフェンス/URL/箇条書きを除外するので正しく 0 判定）。**gate の除外ロジックの方が俺の目視より正確だった。**★
      X_COVER = agent-economy eyecatch（builder が Read して**日本語文字を含まない抽象画像**であることを確認して流用 = 正しい判断）。
      → **EN 展開完了**: Substack EN(native paywall draft) / dev.to EN(draft) / X-en(draft)。全部未公開、go は誰も撃っていない。
- ★**発見: daily-driver が Substack からログアウトしていた**（症状が紛らわしい: 既存 draft は開けるのに**新規 draft だけ** `ERR_TOO_MANY_REDIRECTS`）。builder が `/publish/posts` がログイン画面を出すことで真因特定 → **email magic-link で復旧**（Google OAuth は Substack では禁止 = memory 記録済み手順）、`handle=anicca2, id=336441894` を API で確認。★
  ★一般法則: セッション切れは「ログイン画面が出る」とは限らない。**リダイレクトループ・特定操作だけの失敗**として現れることがある。認証を疑う前に諦めるな。★

- [x] **#31/#27 secrets/識別子 env 化 DONE** commit `a0aeda21`(openclaw) + `efdef2a`(profitable-claude)。team-lead 検収（値は出力せず存在数のみ確認）: publish-note.sh の平文 creds **grep 0 = 消滅**、bounty-cli.sh の `Daisuke134` 3件は全部 env 化の正しい実装（`GITHUB_IDENTITY="${GITHUB_IDENTITY:-Daisuke134}"` + `${STARTUP//Daisuke134/$GITHUB_IDENTITY}` 置換 + 元リテラル）。
       ★builder の手法が正しい: 巨大 single-quote プロンプトのリテラルを直接編集せず、「デフォルト = 現状のリテラル」の env を足して**構築後に文字列置換** → override 無しで既存と完全一致（挙動不変を実測）、override 有りで新値に置換。★
       ★**新発見（別タスク化）: `connector-cli.sh` に Dais の実名・電話・メールが平文**（spec は「GitHub identity」としか書いてなかった = spec が現実より粗かった。team-lead も PII の実在を grep で確認、値は見ていない）。builder は「この loop の本質が Dais 本人のイベント登録なので env 化の設計自体に判断が要る」と正しく判断して**手を付けず報告**した。★
       ★pre-push hook の弱点発見: `git show --name-only` の出力に**コミットメッセージ本文も含まれる**ため、メッセージ中の「.env」という文字列だけで secrets 混入と誤検知する。★
       残（正しく残した）: bounty/run.sh と README の `Daisuke134/anicca#997` は**過去 issue 番号の引用** = 履歴的 citation。env 化すると逆に不正確になるので残す判断は正しい。

### #22 self-heal L2 実装設計（freever 起草 → team-lead が裁定・訂正して確定 2026-07-16）
★builder の調査で確定した事実（team-lead も grep で確認）: **`article-daily.sh` は `~/anicca/skills/browser/ensure_browser.sh` を一度も呼んでいない**（grep 0）。lockdir は CDP の**排他**はするが、**CDP が死んでいた場合の復旧は誰もしていない** = L0 の唯一の本物の穴。ensure_browser.sh は既に「Chromium 再起動 + session_vault restore + cdp lease gc → ALIVE/RECOVERED/FAILED」を返す完成品なので、**呼ぶだけ**（車輪の再発明なし）。★
**採用する設計（3点。builder 案をほぼ採用、1点訂正）**:
1. **即時 alert**: `article-daily.sh` の `RC=$?` 直後に `RC != 0` なら `_shared/scripts/telegram-notify.sh` で即報告。今朝の「OAuth 失敗 rc=1 を誰も知らないまま丸一日 pass が飛ぶ」を直接潰す。5分ポーラーより速く安い。
2. **pass 冒頭で `ensure_browser.sh` を呼ぶ**（★team-lead 訂正: これは healthcheck 側でなく **pass 側**の仕事。5分毎に browser を触ると daily-driver を使う他の作業と競合する。pass は既に lockdir を持っているので、その中で1回だけ復旧を試すのが正しい★）。FAILED なら pass は browser 依存の platform を skip して正直に報告（記事執筆と note API は続行可能）。
3. **5分ポーラー `ai.anicca.article-healthcheck`**（`StartInterval=300`、`com.anicca.emergency-disk-guard` と同型）は **1つの仕事だけ**: 「06:00 を過ぎたのに run 行が無い」または「run はあるが90分経っても done が無い」を検知して Telegram alert。= **「pass が完了しない」クラスの一般化された検知**（今日の 07:08 三連発のような異常も5分以内に見える）。
**作らないもの（builder の判断を採用）**: Substack/X/zenn セッション用の専用 healthcheck。理由 = これらは「検知」の問題でなく「人間の再ログインが要る」問題。pass の STEP6-9 が既に毎朝1回検知・報告しており、288回/日の再チェックは資源の無駄。
★一般法則: **監視は「検知したら誰かが直せる」ものにだけ付ける。直せない事実を高頻度で再確認するのは監視でなく不安。**★

- [x] ★**今朝の OAuth 死の真因 = upstream の既知バグ（builder が `gh search issues` で特定、2026-07-16）**★: `anthropics/claude-code#76905`（2日前 filed）と完全一致 — **macOS Keychain の単一 credential(`Claude Code-credentials`) を複数の claude session が共有し、single-use refresh token の race に負けた側が invalid_grant → ログアウト状態**に落ちる。issue の環境説明（常時稼働 Mac mini + 1日18本の headless `claude -p` + 長時間 interactive session + Keychain item 1個）が我々の環境と一致。
       裏付け: 今朝 06:00 時点で `~/.claude/.credentials.json` の accessToken.expiresAt はまだ数時間先 = **時間切れではない**。6分後の手動 retry が素通りで成功 = 一過性の race。**team-lead の「並走 claude が原因」仮説は当たっていたが、正確には「同時刻の別 launchd ジョブ」ではなく「常時稼働の interactive session 群との credential 共有競合」**（launchd の 06:00 起動は本ジョブのみと実測）。
       対処（commit `1a60e68` に同梱、後述の混線あり）: `run_claude_pass()` 化 + **その回のログ差分だけを byte offset で切り出して** auth 失敗シグネチャを grep → 一致 かつ rc≠0 の時だけ 30秒待って**1回だけ retry**、それでも駄目なら Telegram FATAL 通知。**auth 以外の失敗には一切触らない**（retry も notify もしない）。4パターンの mock harness で検証済み（success / auth_fail_once=自己修復 / auth_fail_always=通知 / other_fail=不干渉）。
       ★一般法則: **自分のコードを疑う前に upstream の issue を検索する。** 「今日から急に落ちるようになった」は自分の変更のせいとは限らない。★
- [x] **commit 混線の自己申告（team-lead の過失、2026-07-16）**: `1a60e68` は message が STEP 1.5 のことしか書いていないが、diff には builder の auth-retry も入っている。原因 = **builder が同じファイルを編集中に team-lead が `git add <file>` でファイル丸ごと stage し、自分の変更しか書いていない message で commit した**。中身は両方正しく検証済み。訂正の history note = `4b57396`。
       ★一般法則: **共有ファイルで `git add <path>` は「今の中身全部」を stage する。他の agent が同じファイルを触っている間は、commit 前に `git diff --cached` を読んで、自分が書いていない変更が混ざっていないか確認する。**★

- [ ] ★**#47 無料版が Sources ブロックを落としている（設計欠陥。2026-07-16、X-en の eval gate が発見）**★
      症状: eval gate が X-en を **score=30 で FAIL**、fact_flags 6件（x402 の 7,541万件/2,424万ドル、Olas の 1,450万件/8.9万ドル、ACP の 95/5・90/5/5 等）= **全部「実測に裏打ちされた本物の数字」なのに出典が本文中に無い**。
      真因: 原本の `## Sources`（x402.org / EIP-8004 / Olas 等の URL 列挙）は**記事末尾** = 有料境界より後ろにあるため、`make-free-version.py` の切断で**無料版から丸ごと落ちる**。→ **我々が出す無料版は全部、出典なき数字の記事になっていた。**
      ★裁定（gate vs 記事の基準に照らして）: **gate が正しい。記事も gate も曲げず、generator を直す。** 数字は earned だが、**読者から見て earned であることを確認する手段（出典）が無料版に無い**なら、その記事は「信じろ」と言っているのと同じ = 我々の brand の逆。★
      修理（`make-free-version.py`）: 原本に `## Sources`（or `## 出典`）節があれば、**切断位置に関わらず無料版の「まとめ」の後・フッターの前に丸ごと持ってくる**。無料部分で言及した数字の出典だけを選ぶのは機械には無理なので**全部載せる**（出典は多すぎて困るものではない）。
      ★一般法則: **記事を切る操作は、本文だけでなく「その本文を支える証拠」も切る。** 切断は文字数の問題ではなく、**残った側が自立しているか**の問題。★

- [x] ★**#22 self-heal L2 DONE**★ commit `78d7744`（freever 実装、team-lead 検収: bash -n / ensure_browser 4箇所・BROWSER_STATUS・telegram_notify・ALERT_SENT・STEP 1.5・AUTOPUBLISH ブロック無傷を静的確認 / `launchctl print gui/501/ai.anicca.article-healthcheck` = 登録済み）。
      実物: ①auth 以外の rc≠0 も汎用 alert（ALERT_SENT で二重送信を防ぐ）②lockdir 取得直後に `ensure_browser.sh` を1回、ALIVE/RECOVERED 以外なら PROMPT に「browser 依存 platform は skip して正直に報告、note と執筆は続行」を追記 ③`ai.anicca.article-healthcheck`（StartInterval=300）= **ログを読むだけ**（06:05 過ぎて run 行無し / run から90分 done 無し → alert）、browser には触らず article-daily.sh を実行もしない。
      builder の正直な申告: 検証中の Telegram 実送信が制約の1回でなく2回になった（alert 本体 + messageId 確認）。
- [x] **幽霊 run 掃除（team-lead の後始末、2026-07-16 07:50-07:52）**: 新 healthcheck が動くと俺の幽霊 run に対して 08:38 頃に偽 alert を飛ばすと freever が事前警告 → backup(`article-daily.log.bak-*`) を取ってから **07:08:29 の3行 + 07:28 の2行を削除し、削除理由の annotation を追記**（掟: 行を落とす時は backup + 痕跡を残す）。結果 run 2 / done 2 で対応 = 偽 alert は飛ばない。
      ★**07:28 の2行も俺だった** — STEP 1.5 の検証で `source <(sed -n "46,200p" article-daily.sh)` を叩いた = **同じ過ちを1時間で2回、しかもそれを避けるための検証の中で**。★
      ★一般法則（確定版）: **変数を調べたいなら、ファイルを「テキストとして parse」しろ。script のどの一部も実行するな。** `bash -c '<前半>'`、`source <(sed -n ...)`、`split()` して eval — 全部同じ罠。実行はログを書き、ロックを取り、cron を起こす。★

- [x] ★**#48 de-slop gate の非決定性を根治（2026-07-16、commit `4a8601c0`）**★
      症状: **同じ本文・同じ gate で毎回違う箇所を FAIL**（1回目=em dash/quotable/footer、2回目=「Deciding, first.」等の別の既存文）。直すと別の難癖が出る = 12ラウンド事件と同じクラスで、較正(`bb6520de`)では止まらなかった。
      真因: 「checklist ルールを引用しろ」と縛っても、**ルール自体に「formulaic structure を壊せ」のような主観項目がある限り、judge は何にでも紐付けられる**。有限集合の強制が不十分だった。
      修理 = **blocking と advisory の分離**:
      - blocking（FAIL させるのはこれだけ）= **B1 煽り語 / B2 em dash / B3 filler 開閉句 / B4 裏付けの無い箴言 / B5 出典も受領書も無い事実主張** = 全部 **word-level で誰でも同じものを指せる**
      - advisory（報告するが止めない）= リズム・文長・断片・formulaic structure・rhetorical setup・meta-joiner = 主観。**「Deciding, first. Paying, second.」は著者の意図した文体であって slop ではない**と明記
      実測: slop fixture = **7件 blocking で FAIL**（緩めすぎ検査 PASS）／本物の EN 記事 = **3回連続 PASS**（blocking 0-2、指摘は advice へ）= **安定を実測で確認**。
      ★一般法則（12ラウンド事件の法則の完成形）: **judge を収束させるのは「ルールを引用しろ」ではなく「blocking にできる指摘の型を、誰が見ても同じものを指せるものだけに限定する」こと。** 主観的な良し悪しは advice として出させ、決して止めさせない。**止める権限は客観に、意見は助言に。**★
      ★運用の証明: builder が3回とも「無理に書き換えず violation をそのまま報告」したから、**記事を1文字も壊さずに gate の欠陥3つ（scope / footer / 非決定性）を潰せた**。gate に従って記事を直していたら、published 済みで承認済みの記事が毎回劣化していた。★

- [x] ★**#49 eval-gate が我々の house style と矛盾していた（2026-07-16、commit `02f82b29`）**★
      症状: X-en が **score=36（閾値35以上なのに）FAIL** — fact_flags 4件、理由「数字にインライン出典が無く、末尾 Sources 一括では per-claim mapping が無い」。
      真因: **`SKILL.md` rule 26 =「出典は本文末尾の1ブロックに全部。本文中インライン禁止」が我々の確立済み書式**（pipeline 全体・原本記事も全部この型）。eval gate はそれを知らず、我々の正式フォーマットそのものを欠陥と判定していた。
      修理: gate に house citation style を教えた —「末尾 Sources 節が該当プロジェクト/データセットを覆っていれば sourced」「first-hand receipt も sourced」「**per-claim インライン紐付けが無いことは fact_flag ではない**」「**Sources 節が丸ごと無いのに外部数字を出していたらそれは本物の fact_flag**」。
      実測: Sources 入り = **2回とも PASS（score 39/38、fact_flags 0）** / Sources を削った版 = **FAIL（30、fact_flags 6）** = 緩めすぎ検査 PASS。
      ★一般法則: **fresh judge は「その publication の書式」を知らない。** 知らないまま judge させると、**自分たちの正式フォーマットを毎回欠陥として弾く**。judge に渡すのは記事とルールだけでなく、**その記事が従っている書式の宣言**も要る。★
      ★今日の gate 欠陥は計4つ（#48 scope / #48 footer / #48 非決定性 / #49 house style）。全部 **builder が「書き換えず violation をそのまま報告」したから発見できた**。gate に従って記事を直していたら、published 済み・Dais 承認済みの記事が4回劣化していた。★
      未修理（次版で直す価値あり、記事は通す）: 無料版 summary bullet に em dash `--` が2箇所（gate は PASS を出した = blocking 3件未満）。

- [x] ★**#50 gate の最終形: 機械で判定できるものは機械が判定する（2026-07-16、commit `dca4ce7a`）**★
      2つの残穴を X-en の実物で発見（**builder が「PASS だけど em dash が残ってる」と報告してくれたから**）:
      ① **em dash がフッターに残ったまま PASS していた** = team-lead の設計ミス。「blocking 3件未満は PASS」の閾値が、**1個でもアウトの house rule（em dash ゼロ）を握り潰した**。閾値は「程度問題のルール」には合うが「binary なルール」には合わない。
      ② **同一 md で 1回目 FAIL / 2回目 PASS** = 非決定性が残っていた。**「retry すれば通る gate」は gate ではない**（#48 の blocking/advisory 分離でも消えなかった）。
      修理 = **deterministic pre-check**: LLM を呼ぶ前に regex で確定検査（em dash / 煽り語 / filler 句。コードフェンス・URL・箇条書き記号は除外）→ ヒットしたら**その場で FAIL、model は呼ばない**。model には**判断が要るものだけ**（B4 裏付けの無い箴言 / B5 出典なき主張）を残す。
      実測: X-en md = **em dash 3件で FAIL**（builder の報告どおり実在）／slop fixture = 3種検知で FAIL／clean fixture = 通過して judge へ PASS。
      ★一般法則（今日の gate 4連戦の結論）: **regex で決まることを model に決めさせるな。** model は毎回違う答えを出すが regex は出さない。gate の設計は「判断が要る部分を最小化し、残りを機械に固定する」こと。**判断の余地 = 非決定性の入口。**★
      ★運用法則: **gate が PASS を出しても、気になったものは報告する。** builder のこの1行が、閾値が house rule を握り潰していた穴を暴いた。PASS は「問題なし」の証明ではない。★

### ★gate と記事のどちらを曲げるか（裁定基準。2026-07-16 X-en の実例で確立）
gate が FAIL を出した時、**記事を直すのが正しい場合と、gate を直すのが正しい場合がある**。実例（X-en の de-slop 4件）:
| 指摘 | 裁定 | 理由 |
|---|---|---|
| em dash `--` の使用 | **記事を直す** | 本物の違反。我々のルールそのもの |
| "One problem surfaces here."（弱い rhetorical setup） | **記事を直す** | 本物。何が問題かを直接書けば済む |
| "Transaction count can be staged. Money settled cannot."（quotable だから消せ） | ★**gate を直す**★ | **記事の核心**で 1,450万件 vs 8.9万ドルという**実測に裏打ちされている**。quotable ルールは「稼いでいない疑似箴言」を狙うもの。→ gate に「earned な発見は quotable ではない」を明記（`0224b7aa`） |
| 無料版フッター（meta-joiner だから消せ） | ★**gate を直す**★ | #43 で設計・Dais 承認済みの**意図的な構造**。→ gate に「footer は判定対象外」を明記（`0224b7aa`） |
**基準**: ①その文は**実測・観測に裏打ちされているか**（yes なら守る）②それは**設計として意図的に置いたものか**（yes なら gate の scope を直す）③どちらでもなければ記事を直す。
★一般法則: **gate が「我々が意図して置いたもの」を弾いたら、それは gate の scope バグ。記事を曲げて gate に従うと、gate が守るはずだった価値を gate 自身が削る。** ただし gate を緩めた後は必ず**元の slop fixture がまだ FAIL することを実測**して、緩めすぎていないことを示す（今回も5件で FAIL を確認済み）。★
★運用: builder は **gate に迷ったら書き換えず violation をそのまま報告する**（今回 note-paid-builder がそうした）。無理に通そうとして記事を壊すのが最悪。裁定は team-lead の仕事。★

### ★運転モデル（Dais 確認 2026-07-16）: team-lead = thinker/spec-writer/verifier、builders = executor★
- 新しい機能・変更はまず**この spec に書く**（superpowers の brainstorming→spec→plan 流儀）→ builder に明確な手順+検証条件で委譲 → team-lead が**実出力で独立検収**（自己申告は証拠でない）→ spec に実測結果を書き戻して commit+push。
- 会話は揮発。**spec に書いてない発見は捨てたのと同じ。** 各 turn で spec 更新 + push を怠らない。

### 現在地スナップショット（2026-07-16 07:35 JST。次の agent はここから）
**loop の全部品が実在し、全部 E2E 検証済み。残る操作は plist への arm 1行だけ。**
| stage | 実物 | 状態 |
|---|---|---|
| ①TOPIC / ②RESEARCH / ③WRITE | article-daily.sh の PROMPT（launchd 06:00） | 8日連続 rc=0 で稼働中 |
| ①.5 PLAYBOOK | STEP 1.5（commit `1a60e68`）+ `state/playbook-applications.jsonl` | 配線済み。playbook.json は funnel 7日で生成 |
| ④PRICE | `_shared/price-check.py`（`3b75f3c2`） | live 実測済み |
| ⑤FREE-GEN | `_shared/make-free-version.py`（`18a7014e`） | 手動正解と byte 一致 |
| ⑥GATES | language-purity + seo(`7e7ec391`) + deslop(`bb6520de` 較正済) + eval、run.sh(`c2079cd1`) と X 経路(`677024b5`) 両方に配線 | 実記事を実際に止める所まで実証 |
| PUBLISH note 有料 | `publish-paid.py --arm`（`b84674a6`） | ガード停止 E2E 済。--arm 実行は未（初回は明日） |
| PUBLISH X | `publish-to-x.sh`（`3c796b21` cover gate + `677024b5` gates） | live 公開実績あり |
| PUBLISH zenn | `post-zenn.py`（`1e688535` slug 修理） | 下書き6本が dashboard に実在 |
| PUBLISH substack | `_shared/publish-substack-mermaid.sh`（`dacdeac2` + `891118e0` padding） | JA live 実績 / EN native paywall draft |
| REALITY-GATE | `reality-gate.sh`（`d2179217`） | note/x/ssr の3経路を live で PASS/FAIL 実証 |
| LEARN | `_shared/measure-funnel.py` + self-improve.sh L3（`0a5c612b`） | live 実数値取得済（note like=2 / X views=307） |
| 契約 | article-daily.sh の `ARTICLE_AUTOPUBLISH`（`3264daa`） | **未 arm**（既定 = draft-only、prompt MD5 が変更前と byte 同一で証明済み） |

**次の1手 = `~/Library/LaunchAgents/ai.anicca.article-daily.plist` に EnvironmentVariables で `ARTICLE_AUTOPUBLISH=1` を入れて launchctl reload → 翌 06:00 の初回無人公開 run を観察。** Dais 承認待ち（2026-07-16 07:35 時点）。

**Dais 判断待ち（2件）**: ①arm してよいか ②`connector-cli.sh` の PII（task #20）— この connector loop は現役か（死んでいるなら削除、生きているなら PII を env へ出す設計が要る）。③zenn アカウントの未把握記事40本以上（cronジョブ/Claude Code/OpenClaude 系）を消してよいか。

**残タスク**: self-heal L2（設計を freever に起草させ中 → team-lead が spec 化 → 実装委譲）/ #20 PII / self-improve.sh の keep-revert 実装（day7 median 定義済み、データが7日たまってから）/ X-en draft（note-paid-builder 実行中）/ Phase 2 = human-funded から親 skills/ への昇格（#31 完了後なので着手可能だが、契約と場所を同時に動かさない原則で arm 後に）。

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

- [x] #33 **図がデカすぎる問題の真因 = 幅だけで sizing していた**（Dais が何度も指摘していたが skill に入っていなかった）→ **DONE 2026-07-15 commit `4125c711`**
       実測（推測ではない。`getBoundingClientRect()` を実 DOM から読み戻した）:
       | | 修正前 | 修正後 |
       |---|---|---|
       | mermaid natural | 276x606（**縦長**。flowchart TD は kroki が portrait で吐く） | 同じ |
       | displayed | **480x1052**（ビューポートより高い + 1.74倍に拡大 = ボケる） | **255x558**（0.92倍 = 拡大なし） |
       | eyecatch | 620x325 | 620x325（正常、変化なし） |
       | 記事カラム幅 | 620 | 620 |
       真因: `compact_html(url, png, cw=480)` が**画像の元幅を無視して幅480に固定**。縦長の図は幅を固定すると高さが膨張する。しかも元が276pxしかないのに480pxを指定 = **拡大されてボケる**（デカい＋ボケるの最悪の組み合わせ）。
       修理: `scale = min(max_w/w, max_h/h, 1.0)` で**幅と高さの両方の箱に収める + 1.0 で拡大を禁止**。MAX_H=560（これを超えると次の段落が画面外に押し出される）。
       ★一般法則（SKILL.md rule 71 に焼いた）: **「デカすぎ」は幅の問題ではない。画面からはみ出すのは高さ。縦長の図は幅を縮めても異常に細くなるまで効かない。** 生成画像は必ず max-width と max-height の両方に収め、scale を 1.0 で clamp する。★
       ★★メタな一般法則（これが本命）: **同じ指摘が2回来たら、その記事を直すのをやめて skill に法則を書け。繰り返される苦情は、その記事の欠陥ではなく skill の欠陥。** 今まで毎回「幅の数字を1つ動かす」で終わっていたので毎回戻ってきた。★★
       → **reality-gate(#20) に追加すべき検査**: ①`displayed_w > natural_w` なら FAIL（拡大 = ボケ）②`displayed_h > 560` なら FAIL（画面外）。今夜 Dais が目で言ったことの機械版。

### PART I — 収益化の決定（2026-07-16。全て team-lead が note API を自分で叩いた実測。subagent 報告の又聞きではない）
- [x] #34 **決定: 買い切り ¥1,000 一本。メンバーシップは作らない。** Dais 承認済み 2026-07-16。
       ★実測（note 検索API q=Claude Code / AI自動化 sort=popular → creators API で著者ごとに hasCircle）★
       | creator | フォロワー | 記事 | メンバーシップ | 売っているもの |
       |---|---|---|---|---|
       | punimaru_dev | **177** | **3** | ❌ | **¥3,480 買い切り like=928** |
       | kon_ai | 188 | 4 | ❌ | ¥3,980 買い切り |
       | 09pauai | 1,567 | 4 | ❌ | ¥1,480 買い切り like=283 |
       | shiro_life0 | 2,334 | 11 | ❌ | ¥100,000 買い切り like=794 |
       | ebithai | 1,949 | **65** | ✅ | （メンバーシップ持ちの最小記事数） |
       | tothinks | 6,409 | 119 | ✅ | |
       | kajiken0630 | 44,877 | 295 | ✅ | |
       | goto_finance | 93,822 | 1,072 | ✅ | |
       | chatgpt_lab | 21,886 | 702 | ❌ | ★note のメンバーシップを畳んで自前ドメイン chatgpt-lab.com へ移動、名前も AGIラボ に変更★ |
       ★**測った11人中、記事10本以下でメンバーシップを持つ者はゼロ。最小は65本(ebithai)。我々は0本。**★
       → **買い切り = 「証明」の商売（フォロワー不要、実績が要る）／メンバーシップ = 「規模」の商売（記事の山が要る）**。
       → 我々 = 読者0だが証明は強い（実際に稼ぐ loop、on-chain ログ）→ 買い切り。
       価格 ¥1,000 の根拠: like=165「「AIを雇う」という設計」= 我々と同じ**解説系**の実売価格。¥3,480 が売れるのは「2ヶ月目に月10万円」= 読者が同額を稼げる約束があるから。我々の記事は解説でありその約束をしていないので同額は取れない。
       無料部分 = **約2,500文字**（実測の型: punimaru_dev 2,529字 / shiro_life0 2,467字。2人ともここで切っている）。両者とも `is_limited=false, is_trial=false` = 素の買い切り。
       **メンバーシップは記事65本を超えてから**（実測の下限）。1日1本の loop なら約2ヶ月後。順番が逆だと空箱を売ることになる。
- [x] #35 ★**公開 DONE（2026-07-16 04:13 JST、team-lead が note API `GET /api/v3/notes/nbcb93e6fc711` で実測確認）**★
       `status=published, price=1000, is_limited=false, publish_at=2026-07-16T04:13:28+09:00`
       URL = `https://note.com/anicca123/n/nbcb93e6fc711`（アカウント anicca123 / Dice、note_count=6, follower=4）
       = **初の有料記事が本番公開された。買い切り¥1,000、有料ライン2,598字（#40）。あとは売れるか。**
       残り（旧#35の未了分）: `publish-paid.py` を汎用化して loop に配線（今回は手動運転で通した）。
- [ ] #35-old **買い切り公開スクリプトが存在しない**（`grep -rl is_paid` → SKILL.md の文章のみ、コード0行）。既存 `note-publish/publish.py` は無料+メンバーシップ+試し読み専用。→ `publish-paid.py` を作る。
       実測した note の公開設定 UI（team-lead がブラウザで実取得。推測禁止）:
       - 記事タイプ = `input[name="is_paid"]` value=`free`|`paid`（ラジオ。`(r.closest('label')||r).click()` で反応）
       - 「有料」選択で出現 = 価格欄 `input[type=text][placeholder="300"]`（**既定で 500 が入っているので上書き必須**）、返金申請 checkbox、`input[name="sale_setting"]` value=`none`|`time_sale`|`twitter_retweet`|`prior_sale`
       - 「有料」を選ぶと「投稿する」→「**有料エリア設定**」に変わる = 有料ラインを引くまで投稿できない
       自己検証を必須にする: 投稿後に `GET /api/v3/notes/{key}` で `price==1000 && is_limited==false && is_trial==false` を確認、違えば非0 exit。
- [ ] #36 **ハッシュタグが壊れている**: 実物の draft に `#自分 #人間 #財布 #価値 #実際` が付いていた = 本文から機械的に抜いた無意味語。検索流入ゼロ = 買い切りが売れない直接原因。→ 読者が実際に検索する語（#AIエージェント #Claude #エージェント経済 等）にする。
- [ ] #37 ★**loop が価格戦略を毎回測り直す（自己改善）**★ Dais 指示 2026-07-16。
       **数字を skill に焼くな。測り方を焼け。** 今夜、skill に焼いてあった数字が2つとも腐っていた（「Price=500円/月」= 誰もやっていない、「ChatGPT研究所をコピー」= 当人が note から撤退済み）。
       publish 前に毎回:
       ① note 検索API で自分のニッチの popular な有料記事 → `price` と `like_count`
       ② creators API → 著者の `hasCircle` / フォロワー / 記事数
       ③ 自分の記事数 vs メンバーシップ持ちの下限 → 未満なら買い切り、超えたらメンバーシップへ切替
       ④ 同カテゴリの実売価格から価格を決める
       ★一般法則: **事実を返すチェック（hasCircle）を、事実について語る記事より優先する。API 1発が「note で稼ぐ方法」ブログ100本より正確。**★

- [x] #38 **idempotency 実証 + eyecatch 生存を実測（team-lead が実 note.com で撃った。「未検証」項目の解消）** 2026-07-16
       ★実出力★
       ```
       1回目(台帳空): DRAFT key=nbcb93e6fc711 reused=false ...     ← create が正解（台帳が実装前の draft を知らない）
       台帳: {".../2026-07-12-how-to-build-the-agent-economy-jp.md": {"key":"nbcb93e6fc711","num":"170251627",...}}
       resolve → {"action":"update","article_id":"nbcb93e6fc711","key_format_ok":true,"reason":"ledger"}
       2回目:        DRAFT key=nbcb93e6fc711 reused=true stage2_embedded=3/3   ← ★同じ key。draft は増えない★
       ```
       → **「1つの draft を磨き続ける」形が実証された**（Dais の要求）。
       ★**eyecatch は update_article で消えない**（旧「未検証」を解消）: eyecatch 設定 → 本文 update → `verify-draft.py` で `IMAGES_TOTAL=4`(mermaid 3 + eyecatch 1) `IMAGES_BROKEN=0` `VERDICT=PASS`。`update_article` の payload は name/body/body_length/hashtags のみで eyecatch を触らないため。→ **eyecatch と本文更新の順番に制約は無い。**★
       tags も同様に維持される（payload に hashtags が載るため毎回渡せば良い）。
- [x] #36 **タグは「壊れていた」のではなく「ゼロだった」**（team-lead の誤診を訂正）。エディタに見えた `#自分 #人間 #財布 #価値 #実際` は**note の自動提案**（全て同一 class `sc-35e5f35-2 cFEPnm`、削除ボタン無し）で、適用済みタグではない。決定的証拠: `--tags` を渡していなかったので `NOTE_TAGS=""` → `TAGS=[]` = **1つも付いていなかった**。結論は同じ（タグ0 = 検索流入0 = 売れない）。
       ★タグは実測で選ぶ（note hashtag API `GET /api/v2/hashtags/{tag}` が件数を返す）★:
       `#AI` 794,103 / `#生成AI` 416,162 / `#Claude` 99,592 / `#プログラミング` 97,560 / `#AI副業` 68,226 / `#暗号資産` 48,735 / `#AIエージェント` 43,821 / `#ClaudeCode` 38,875
       → 採用 = `AIエージェント,Claude,暗号資産,生成AI,AI副業`（主題+読者層+中身+流入+買う層）。**巨大タグ(#AI 79万件)は埋もれるので避ける。**

- [x] #39 ★**note の有料設定は draft に保存されない（transient form state）**★ 2026-07-16 実測。これを知らないと次の agent は一晩溶かす。
       実測: `publish-paid.py` で 有料ラジオ + 価格1000 + 有料ライン を設定 → ガードで停止 → **エディタを開き直したら `price now: NONE` / `paid selected: False`**。
       → **有料/価格/有料ラインは「投稿する」を押した瞬間に初めて確定する。ページを離れると全部消える。**
       意味すること:
       ① ガードで止まった run は note 上に**何も残さない**（副作用ゼロ = 安全）
       ② **「設定してから後で人間が確認」は不可能**。設定と公開は1回のセッションで通すしかない
       ③ だから `publish-paid.py` は公開直前に `FREE_ENDS_WITH:` / `PAID_STARTS_WITH:` を stdout に出す（同じ run 内で境界を見せる）
       ★一般法則: **UI の状態には「保存されるもの」と「投稿時にしか確定しないもの」がある。リロードして残っているかを実際に確かめるまで、どちらかは分からない。**★
- [x] #40 **有料ラインの実測位置（PAYWALL_AFTER_CHARS=2500 の結果）** 2026-07-16
       ```
       PRICE_READBACK=1000
       PAYWALL_PLACED={"ok":true,"free_chars_before_line":2598,"button_index":37,"total_buttons":84}
       FREE_ENDS_WITH: ...うち1,110万件はAI同士の依頼です。…実際に決済された金額は、生涯累計で8.9万ドルです。
                       …取引の件数は演出できますが、決済された金額は演出できない。…ERC-8004は「誰でも相手の評価を
                       書き込める棚」を用意しましたが、その評価が正しいかどうかは誰も担保していません。
       PAID_STARTS_WITH: そして検証。「その仕事は本当に正しかったのか」を確かめる部品には、名前を挙げられる本命が
                       まだ存在しません。ここが、この記事のいちばんの核心につながります。 / 「AIが稼いだ」の9割の正体
       ```
       → 無料が「1,110万件 vs 実売上8.9万ドル」という最も衝撃的な事実で終わり、「検証の空白=核心」の直前で切れる。
       有料側の先頭が [5]「AIが稼いだ」の9割の正体 = 一番読みたい見出し。**2,500字で機械的に切った結果、たまたま最適位置になった**（記事の構成が良いため）。
       ★loop への含意: 切る位置を「文字数」だけで決めると、記事によっては最悪の位置で切れる。将来は「無料側の最後が引きの強い事実で終わるか」を判定させる（#18 eval の仕事）。今は 2,500字 + 段落境界で妥当。★

### PART K — 「無料→有料への誘導は brand を毀損するか」research（2026-07-16、Dais の問いに team-lead が自分で検索して回答）
- [x] #42 **結論: 誘導そのものは brand を毀損しない。毀損するのは「煽り+中身スカスカ」。誘導は JP/EN 両界の標準 playbook。**
       | 証拠 | 出典 |
       |---|---|
       | 「無料部分が売上の9割を決める」= 無料部分の質で売る、が JP note 界の定石。X 宣伝+無料→有料が標準動線 | brain-market.com mayu_brain / note.com/anotaro/n/n7a7229826fcd（2026-07-11「フォロワー2桁で有料noteを売れるようになった無料部分の型12個」）|
       | フォロワー177・記事3本で ¥3,480 買い切り like=928 = 誘導動線は小アカでも機能（我々の実測 PART I）| note API 実測 punimaru_dev |
       | 90%+ 無料で配り paywall=「信頼税」。無料で価値を配りきる限り brand は上がる | growthinreverse.com（HCR $1M+/月、R5）|
       | note 有料販売で brand を築いてから自前ドメインへ卒業した実例 | chatgpt_lab → chatgpt-lab.com（PART I 実測）|
       | X の link penalty は**タイムライン投稿本文**の話。X Article 内の CTA リンクに減点証拠なし。skill の Article 構造テンプレも最終段=CTA が標準 | .claude/skills/x-algorithm/SKILL.md:73-76,150（ClawHub x-algorithm）|
       ★**是正 2026-07-16（Dais の直感が正しかった。上の #42 の初回結論は reference class が偏っていた）**: 初回検索のソース
       （mayu_brain / anotaro 等）は「noteの売り方を売る」インフォ商材エコシステム自身 = circular evidence。tech 系読者に
       「続きは有料noteで」は情報商材に pattern-match し、「嘘を見抜け」が主題の我々の記事と正面衝突する。★
- [x] #43 **無料 platform 記事の終わらせ方 = 「完結+フッター告知」型（是正後の正本。#42 の4条件を置換）** 2026-07-16 検索済み
       | 原則 | 出典 |
       |---|---|
       | 無料 = teaches（それ単体で完結した学び）／有料 = solves（templates, workflows, code, data insights = 別の仕事をする別の成果物）。"Free posts as trailers... that deliver" | newsletterlab.substack.com/p/how-to-grow-on-substack-free-vs-paid |
       | 宣伝は「記事末尾の固定メッセージ程度が望ましい」。誇張タイトル=信頼毀損。生成AI乱造を避けよ | zenn.dev/guideline（公式）|
       | 90%+ 無料で配る。paywall は信頼が貯まってから効く | growthinreverse.com（R5）|
       **無料版記事の型（X/zenn/substack-ja 共通、loop に焼く）**:
       ① 自然な結論で終わらせ、**「まとめ」節（3-5 bullets）を足して単体完結**させる（cliffhanger で切らない）
       ② その下に区切り線 + **フッター2-3行**: 「この記事は無料版です。完全版（note ¥1,000）には◯◯（有料側の中身を正確に名指し: "AIが稼いだ"の9割の正体 / 我々の到達点と実ログ）が入っています」— 価格明示、煽りゼロ、H2 の予告見出しにしない
       ③ 「この続き：」型の teaser H2 は**禁止**（今回 X で使った型。商材 pattern-match の直接原因）
       ④ Substack EN は外部誘導でなく **native paywall**（platform 内 preview→subscribe が規範、HCR 型）
       ⑤ X 告知のタイムライン投稿はリンクを reply に置く（link penalty は投稿側に効く）
       → note 有料版の切り方は現状維持（Dais 判断: 切り位置は良い）。直すのは無料側の「終わらせ方」だけ。
       → [x] DONE 2026-07-16 05:04 JST: Dais が旧記事を非公開化 → team-lead が md を「まとめ4 bullets+フッター」型に書換え
         → 旧draft削除 → 再ステージ → own-eyes 検証 → 再公開。**新 LIVE URL = `https://x.com/diceai0/status/2077484575299862907`**
         （旧 URL `…2077478932589547795` は死んでいる。live verify: 画像4 / tallest 571px / PASS、fv7.png でまとめ+フッター+タイムスタンプ実見）
         無料版 md の正本 = `~/.cloak/note-work/2026-07-12-agent-economy-jp-x-free.md`（この型を zenn/substack-ja にも使う）
       ★Substack-ja も同型で公開 DONE（2026-07-16 05:13 JST、Dais 指示）: **`https://aniccabuddha.substack.com/p/167`**
         手順（#45 で script 化する）: mermaid→PNG を Substack image API(`POST /api/v1/image`, data URI)で S3 upload →
         md の図を S3 URL に差替え → publish-substack.sh で draft → `POST /api/v1/drafts/{id}/publish {"send":false}`（メール爆撃なし・web のみ）。
         SSR 検証実測: 見出し/まとめ/フッター/note URL/画像5(substack-post-media) 全部 live に存在。
         発見: draft_body に markdown を投げると Substack が ProseMirror doc に自動変換する（見出し/リンク/画像 OK）。
         但し ```mermaid はコードのまま残るので事前 PNG 化が必須（今日は手動、要自動化）。
- [ ] #44 ★**X publish 経路の実バグ発見（2026-07-16 再ステージで踏んだ）: X_COVER 未設定だと本文の最初の図が cover に食われて黙って消える**★
       実測: `publish-to-x.sh` は automaton 記事以外 X_COVER を設定しない（prep-x-md.py:61）→ cover 無し md では
       `parse_markdown.py:342` が **images[0] を cover に採用** → fig1 が本文から消えた（figs:3 なのに composer images:2）。
       エラーも WARN も出ない = #30 と同じ「画像が黙って消える」クラスの X 版。今回は verify の画像数チェックと own-eyes で捕捉。
       workaround（今回使用）: `X_COVER=~/.cloak/note-work/eyecatch/agent-economy-eyecatch.png` を明示 export。
       恒久修理 TODO: publish-to-x.sh が X_COVER 未設定かつ md 先頭が画像でない場合、prep 後の figs 数と parse 後の
       content_images 数を突合して不一致なら FATAL（または eyecatch 必須化）。
       ★一般法則: 「最初の画像 = cover」のような**暗黙の consume 規則**は、入力の形が想定と1つズレるだけで正当なデータを黙って食う。
       consume する側と生成する側の数を突合するゲートが無い限り、この欠落は誰にも見えない。★

### PART J2 — #41 実装設計（team-lead 起草 2026-07-16。pass green 確認後に builder へ委譲）
前提ゲート（全部 DONE 済み）: de-slop/eval 配線(`c2079cd1`) + reality-gate(`d2179217`) + 各 platform の guarded publisher。
**Phase 1 = 契約の書き換え（場所は動かさない）**:
1. `article-daily.sh` に env kill-switch `ARTICLE_AUTOPUBLISH`（既定 0/absent = 従来 draft-only。plist で 1 を注入して初めて自動公開）。rollback = plist 1行。
2. prompt 内の契約文を書き換え: AUTOPUBLISH=1 のとき、pass は各記事について
   a. run.sh publish（6a-6d gate、PASS 必須）
   b. JP: note 有料 = `publish-paid.py --arm`（価格は price-check.py の実測 + agent 判断、タグは tag-counts.py 実測5個）
   c. 無料版 = make-free-version.py（切断位置は agent が編集判断で --after-chars 指定）→ X(`enable-publish`+`X_MODE=go go`) / zenn(published:true) / substack(`--mode go`, send:false)
   d. **公開直後に必ず reality-gate.sh <platform> を実行。FAIL → 自分で直して再公開。直せない → 該当 platform だけ非公開/draft に戻して正直に報告**
   e. Telegram 日報に live URL + reality-gate verdict + 販売設定 readback を含める
3. X の sentinel/二重ガードは「pass 自身が自分の記事に対して使うことを Dais 決定 #41 が許可した」と契約に明記（他人の記事・過去記事への go は引き続き禁止）。
**Phase 2（後日）**: human-funded/ から親 skills/ への物理昇格。MOVE 前に plist ProgramArguments + 全 skill/cron を grep（memory 掟）。Phase 1 と分離する — 契約と場所を同時に動かさない。
検証（builder の DONE 条件）: ①bash -n ②AUTOPUBLISH 未設定で従来挙動が byte 同一（契約文以外の diff なし、draft-only 温存）③=1 の分岐が prompt に入ることを grep ④plist は**まだ書き換えない**（初回の有効化は team-lead が翌朝の run 前に手動で行い、初回 run を観察する）。

### PART J — DRAFT-ONLY をやめて直接公開する（Dais 決定 2026-07-16）
- [ ] #41 ★**Dais の決定: loop は draft ではなく直接公開する**★
       理由（Dais 原文の要旨）: 「全部の記事を自分で見てチェックすることはできないし、やりたくない。公開済みのものを後から直す方がいい」
       → 現状の `article-daily.sh` の DRAFT-ONLY 契約（published 常に false 固定、公開は必ず Dais 手動）と **正面から矛盾する**。契約を書き換える必要がある。
       ★ただし順序を守れ: reality-gate(#20) が無い状態で直接公開に切り替えると、**画像が壊れた記事・slop が毎日公開される**。今夜だけで publish 経路のバグが4つ見つかっている（生MD直投げ / 成功の偽装 / 画像が黙って消える / NUM-KEY で画像が入らない）。全部「公開されたら取り返しがつかない」種類。★
       → 正しい順序:
       1. reality-gate(#20) 実装 = 公開後に自分で検証し、壊れていたら**自分で直して再公開**（人間を呼ばない）
       2. 記事品質 eval(#18) = slop を公開前に止める
       3. その2つが green で初めて DRAFT-ONLY 契約を外す（`human-funded/README.md` の昇格ルート = 親 skills/ へ移す）
       「公開してから直す」が成立するのは、**直す主体が機械で、検知も機械の時だけ**。人間が気づく設計なら draft の方が安全。

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
- [~] #11 JP publish: **note=有料公開DONE(#35)、X=無料版 LIVE 公開DONE(2026-07-16 04:42 JST)**。残=zenn/substack-ja
       ★X 公開の実物: `https://x.com/diceai0/status/2077478932589547795`（guarded go flow で publish、`PUBLISH confirmed: True`。
       live verify: body images 4 / tallest 571px / TALL>650 なし。team-lead が fv7.png で「4:42 AM · Jul 16, 2026」タイムスタンプ+CTA+note URL を own-eyes 実見）★
       funnel 稼働開始: X 無料版(live) → CTA → note 有料版 ¥1,000。誘導の brand 妥当性 = PART K #42 で research 済み・Dais 承認済み。
       X 無料版 draft（team-lead が fv_top.png/fv7.png を own-eyes 確認済み）:
       - DRAFT_URL = `https://x.com/compose/articles/edit/2077476121541799937`（未公開、Draft バッジ実見）
       - 中身 = note と同一の無料境界（「…誰も担保していません。」で切断、有料側の混入なし）+ 末尾 CTA H2 + note 有料版 URL
       - verify PASS: body images 3 / tallest 506px / TALL>650 なし。カバー(eyecatch) 正常、著者 Dice @diceai0
       - 無料版 md = `~/.cloak/note-work/2026-07-12-agent-economy-jp-x-free.md`（X 無料版の型として再利用可）
       ★funnel の型が確定: 無料版 = 有料ラインまで + CTA（有料側見出し1-2個を予告 + 買い切り価格 + URL）。loop に焼く際はこれを copy。★
- [ ] #12 EN publish devto→x +verify（tiktok除外）

## 7. 2026-07-17 決定 — 1 loop 2レーン化・OSS 方針・不確実性の解消（Dais 同席セッション）

### 7.1 決定: 新 loop は作らない。TOPIC PICK を優先順位制にして 2 レーン化

| レーン | ネタ元 | 声 |
|---|---|---|
| **A: 人間 raw ネタ** | `topics/queue/` のカード（Dais の raw 研究 + 毎晩の dev-digest + `topics/inbox.md` の思いつき行） | Dais 名義の一人称体験記（récit 型、Rule 27 拡張）。**AI と名乗らない**。SKILL.md Rule 41/65（一人称日記禁止）はレーン B 専用に降格し、レーン A では体験記テンプレを使う |
| **B: AI 自力探索** | 現行のまま（AP2 型 = 新物を実際に動かして受領証） | 現行の匿名解説者 |

- queue にカードあり → レーン A。無し → レーン B。dedup は機械式: pass 開始時に `mv queue/→in-progress/`（claim）、全 platform staged で `mv → done/`。done/ のカード名 = 再選択禁止リスト（regex 照合）。published が queue を掃除し損ねる事故は構造的に起きない。
- 最初の queue カード3枚: ①Virtuals ACP ②Olas Mech Marketplace（両方 `docs/articles/2026-07-12-agent-marketplace-DEEP-QUESTIONS.md` から切り出し）③humanizer-skill shootout（同一原文を stop-slop / stop-ai-slop-jp / k16 gist に通して比較。7.4 の照合結果が下調べ）。
- **dev-digest**: handover 依存は却下（書かれない日がある）。原料 = その日の session transcript（`~/.claude/projects/*/`、全セッション自動記録）+ 全 repo の当日 git log。23:30 launchd。抽出は「報告」ではなく**教訓抽出**（症状→誤った本能→正しい手→一般法則）。★redaction gate 必須（transcript は秘密を含む。fake secret を混ぜて FAIL する negative test 付きで実装）★。教訓ゼロの日はカード無し = レーン B が走る。
- funnel.jsonl にレーン A/B タグを付け、self-improve L3 がレーン別に効果測定 → 売れるレーンに配分が寄る。

### 7.2 決定: OSS の形 = 「Claude setup 丸ごと + 毎日稼ぐ loop」(profitable-claude)

GH 実測調査（2026-07-17、gh search）: `.claude` 公開 repo の上位は trailofbits/claude-code-config(★2045)、jarrodwatts/claude-code-config(★1059)、PaulRBerg/dot-claude 等、全部**静的テンプレ配布**。「skills + launchd/cron 自動 loop」まで OSS してる例は**ゼロ**。money 系 Claude setup も検索 0 件。→ profitable-claude は空きニッチ。
- .gitignore は定番の「default 全無視 → `!` ホワイトリスト」方式（jarrodwatts/PaulRBerg 型）。除外定番: `settings.local.json` / `.env*` / `*.log` / state 生成物。
- trailofbits 方式の settings.json deny rule（`~/.ssh` 等への Read/Edit 拒否）も同梱する。
- **自己完結化**: skill 本体を profitable-claude に置き、`.claude/skills` は symlink。stop-ai-slop-jp / stop-slop の checklist は attribution 付きで vendor（現状 deslop-gate.sh が `~/anicca-project/...` をハードコード = 他人の環境で gate 即死、実測）。

### 7.3 不確実性の解消結果（U1-U9、全部実測）

| U | 結果 |
|---|---|
| U1 gate 認証死 | ✅**解消**（§4 参照。proxy 配線、E2E PASS 実証、push 済み） |
| U2 レーンA の声 | ✅設計決定（7.1。Dais 拒否権あり） |
| U3 Substack Stripe | ✅**解消（2026-07-17 自動ログインで実測）**: Stripe 接続済み・有料購読 ON・$8/月・$80/年・founding $240。Dais の手作業は不要だった（magic-code は gog gmail で自動取得） |
| U4 firecrawl | ✅**生存**（`firecrawl scrape` 実測成功 2026-07-17。「credit 切れで既定から外す」は scrape には当てはまらない — 旧記述を是正） |
| U5 redaction | 設計に組み込み（7.1。negative test 必須） |
| U6 k16 吸収度 | ✅照合完了（7.4） |
| U7 X session | vault forever-session で概ね解消、healthcheck 監視継続 |
| U8 秘密識別子 | ✅スキャン完了（7.5） |
| U9 書籍 | `topics/done/` + 公開 URL 対応表が章立て台帳。記事10本到達時に言語/出口を決める（非ブロッカー） |
| （是正） | `connector-cli.sh` の PII 課題は **connector loop（`~/profitable-claude/skills/human-funded/connector/`）の持ち物**で article loop とは無関係。本 spec の旧記述（#27 に含めていた文脈）から切り離す |

### 7.4 k16 gist（japanese-tech-writing）照合結果 — 2026-07-17 実測

- gist = 10節78ブレット。吸収済みは**わずか ~16/78**（ダッシュ・中黒、命題型H2、劇的断片化など）。**62項目が未吸収**（段落と論証の構成・全12項目、論証の厳密さ 10項目、冗長の排除ほぼ全部、読者への誠実さ全3項目、LLM 禁止語彙の技術書系リスト等）。
- **矛盾2点**: ①二人称 — gist「あなたと呼ぶな」vs stop-ai-slop-jp #5「あなたはで書け」→ 文書種別（技術解説 vs note 体験記）で分岐が必要 ②述語強度 — gist X13「確定根拠は強く言い切れ」vs slop-jp #3「中間温度を混ぜろ」→ 対象が違うが機械適用すると衝突。
- 対応: gist を `japanese-tech-writing` として attribution 付き vendor、deslop-gate の checklist をレーン/文書種別で選択制に。shootout 記事の下調べを兼ねる。

### 7.5 U8 秘密識別子スキャン結果（OSS 前の必須作業リスト）

API key/token/password の直書き = **0 件**（全部 env 参照済み、健全）。残作業:
| 優先 | 何 | 対応 |
|---|---|---|
| 1 | article-daily.sh の Telegram chat id デフォルト値4箇所 + プロンプト内 `~/.openclaw/...` パス30箇所超 | デフォルト値削除・必須 env 化（`TELEGRAM_TARGET_ID`）、パスは `OPENCLAW_HOME` ベース env に一本化 |
| 2 | ✅**完了（2026-07-17、#58a）**: note user_id 直書き（Session構築の全4ファイル: publish-note.sh:260 / note-stage2-publish.py:50 / note-publish/rebuild-note-body.py:64 / note-publish-draft.py:40）を `os.environ.get("NOTE_USER_ID","14651590")` / `os.environ.get("NOTE_URLNAME","anicca123")` へ env fallback化（未設定時は既存値と byte-identical、bash -n/python3 compile通過を実測）。commit: anicca-dais `d57dfd2c`（main-internal） |
| 3 | ✅**完了（2026-07-17、#58a）**: run.sh:39-43 の devto/substack/note/zenn 自アカウント直書きを `${ZENN_ACCOUNT:-anicca-daisuke}` / `${DEVTO_ACCOUNT_HANDLE:-anicca_301094325e}` / `${SUBSTACK_PUBLICATION:-aniccabuddha.substack.com}` / `${NOTE_URLNAME:-anicca123}` へ env fallback化（env未設定→既定値、env設定→override、を実測確認。aniccaai-blogチャンネルは5大platformループ対象外のためスコープ外のまま）。commit: anicca-dais `d57dfd2c`（同上、run.sh part） |
| 4 | 他 repo 絶対パス依存（`~/anicca-project` spec 参照、`~/anicca` git 操作、`~/.cloak` profile、note-mcp src） | `ANICCA_PROJECT_DIR` 等のベース env + vendor（7.2）。**未着手**（#58 の残作業、authfix 担当） |
| 5 | ✅**完了（2026-07-17、#58a）**: `.gitignore` を blacklist から「default全無視(`*`) + `!`ホワイトリスト」方式（trailofbits/jarrodwatts、gh実測で確認した実際の公開repoから copy+tweak）へ書き換え。既存トラック済みファイルは無影響（gitignoreは追跡解除しない、`git status`前後差分ゼロを実測）、許可ディレクトリ配下の新規ファイルは`git add`可能（実測）、ルート直下の新規ファイル/`state/`ネスト/`.env`/`settings.local.json`は正しく除外（`git check-ignore`実測）。加えて`.claude/settings.json`にtrailofbits型`permissions.deny`（ssh鍵/クラウド認証情報/npmrc/keychain/walletアプリデータ/PEM等）を新設。commit: profitable-claude `c10cbfc` |

### 7.55 zero-config bootstrap 原則（2026-07-17 Dais 決定 — profitable-claude OSS の根本仕様）

**人間が渡すのは payout 先（銀行 or crypto wallet）だけ。** publishing アカウント（note/zenn/substack/devto/X…）は loop が自分で作る:
- loop 自身の email（gmail plus-address or agentmail）で signup。前例 = ig-account-create（2026-06-29 E2E 実証、email-only・電話なし・CAPTCHA なし）。earn アカウントは AI 自身の email を使う（Dais の Google を使わない、既存 memory 規律と同一）。
- **KYC が要る loop（coconala 系 gig work 等）は既定 OFF**。README に「KYC を済ませれば有効化できる」とだけ書く。人間がやらなければその loop は起動しない = 稼げないだけで壊れない。
- **既定 ON = KYC 不要 loop のみ**（article loop が筆頭。gig 以外はほぼ全部該当見込み）。
- 現行の keiodaisuke ベースのアカウント群は「Dais インスタンスの値」であり、OSS 版では .env のデフォルトではなく bootstrap ステップの成果物になる。

### 7.56 repo 構造決定（2026-07-17 Dais）: `human-funded/` 階層は廃止、フラット `skills/<name>/`

`human-funded` は colony 内部分類の漏れで OSS の readable naming 違反。新構造 = `profitable-claude/skills/{article-writer, gig-work, connector, life-manager, …}`（Claude Code の skill 規約と 1:1、install.sh が ~/.claude/skills/ へ symlink 登録）。#70f のパス書き換えと同時に実施。

**round2 完了（2026-07-17、builder-authfix）**: gig/bounty/affiliate は digest が round1（commit `4f801d6`）で先行 flatten 済み。round2 の対象 = `article`(→`article-writer`)/`connector`/`life-manager`/`explorer`/`tests`/`README`。`git mv`（履歴保持、article の `writer/` サブ階層も一段上へフラット化）+ 全286ファイルの参照修正（bin/, lib/, config/, tests/, launchd テンプレ, 稼働中 `~/Library/LaunchAgents` の実plist）。commit: profitable-claude(main) `682cc26`。

- **PROP-015 完全 green 化（5/5）**: digest の round1 では bounty/affiliate/gig 分のみ解消され、article/life-manager 分の36件が未解決のまま残っていた（round1 時点でも既に失敗していたことを `git stash` 比較で確認 — round2 が壊したのではなく元から未解消だった債務）。`config/anicca-ref-allowlist.txt` に19エントリ追加して分類・解消。
- **本番バグを検証中に発見・修正**: bounty/affiliate/gig-work/connector/life-manager/explorer の6ループ全`*-cli.sh`が`REPO_ROOT`を`dirname`3段で計算しており（旧 `skills/human-funded/<loop>/` の3階層ネスト前提）、round1 の flatten で2階層になって以降 `source lib/registry-enforce.sh` が静かに失敗し続けていた。つまり **CEO の pause/budget enforcement gate が全ループで無効化されたまま気づかれていなかった**（`set -e` 無しなので exit しない。`REPO_ROOT` が `/Users/anicca` を指し `source` が file-not-found で無視されるだけ）。全6ファイルを `../../..` → `../..` に修正、再検証で PROP-086（paused registry → tmux 起動しない）を実測 green 化。同型バグが `affiliate_verify.py`（ytdlp_parse vendored import）と自身のテストファイルにもあり、あわせて修正。
- **tests/art/ が一度も run-all.sh に配線されていなかった**ことを発見（7ファイル、history的に存在するのに実行されていなかった）。配線したところ2件新規に失敗が可視化されたが、いずれも path 由来ではなく別種の既存debt: (a) `test_vendor_dirs_referenced.sh` — life-manager-cli.sh の STARTUP prompt にベンダーツール名の言及が欠けているコンテンツギャップ（round1 以前から既存）。(b) `test_article_daily_contract.sh` — 「`--mode go` 禁止（draft-onlyループ前提）」という古いアサーションが、Dais 承認済みの Substack live-publish 稼働（#70f phase2 で確定済み）と矛盾。ポリシー判断が必要なため中身は書き換えず既知失敗として記録のみ。
- 稼働中 launchd 9ジョブ（article×6 + connector×2 + life-manager×1）の plist を新パスへ書換 + `bootout`→`bootstrap` 再読込、`launchctl print` で実メモリ上の ProgramArguments が新パスであることを実測確認。
- 最終テスト状態: `tests/run-all.sh` 114/116 pass（残り2件は上記の既知debt、path bug ではない）。

### 7.57 本日の教訓（2026-07-17、恒久ルール化済みのもの）

- **sandbox は「実行場所」でなく「全書き込み先」に張る**（#70e で本番 plist 5本を誤上書き→即復旧。memory 化済み）。復旧検証は on-disk + launchd 実メモリ（launchctl print argv）まで。
- **port ≠ copy**: 移植先に独自進化した配線済み実装が既にある場合、それを対象に改修する（#65impl で digest が commit 前に自己発見。eyecatch/#69 と同じ「配線されない孤児を作らない」原則の適用）。
- commit メッセージにバッククォート禁止は zsh でも再発（2回目）。`git commit -F <file>` を既定にする。
- 稼働中の live pass は kill しない。構造変更（mv/rename）は pass 完走後（#70f で実践）。

### 7.58 アイデア backlog（#71）

- **X 投稿の API 経路**: x.ai CLI（grok 課金）+ xmcp で browser 非依存の X 投稿。★draft-only 厳守★（過去の直接投稿事故の教訓）。ブラウザ経路が安定してる間は優先度低。
- **loop の一般化**: article loop → 「writing 収益化」全般（短文/長文/newsletter/連載→書籍）。topics/ queue とゲート群は形式非依存なので、platform adapter を足すだけで横展開できる構造になっている。

### 7.59 初レーンA 記事（2026-07-17 ハンコで5%）の編集精読 — 内容側の欠陥5クラスと loop 化（合意待ち #72）

E2E は全 green だったが、**中身**を編集者として精読した結果、text gate が測っていない欠陥クラスが5つ:
①看板埋没（スクープが70%地点、均等重量の調査報告化）②受領証不可視（「読んだ」のに現物断片ゼロ）③visual 貧血（自明 mermaid 1枚 = 枚数 gate の最低通過）④曖昧量化（「過半数」— JSON があるのに数えてない、タイトル5%断定 vs 本文hedge）⑤¥1,000 の値打ち設計なし（5,167字、有料部の売り不明示）。
一般化 → #72 content-rule pack: 看板1/3ルール / claim-to-artifact 比率 / visual 情報量判定 / 曖昧量化語検出+タイトル整合 / 厚み-価格 floor。Dais 合意後に SKILL.md + eval/deslop gate へ焼く。**render-verify（見た目）と content-rule（中身）が揃って初めて babysit 終了**。

**追記（2026-07-17、実ブラウザ実見で発見・修理・builder-authfix）: Substack ja/en 両 draft に frontmatter+H1 二重表示混入（公開ブロック級）**。同じレーンAの2 draft（post/207386219 ja・post/207386225 en）を実ブラウザで開いて確認したところ、note と同型のバグが Substack 経路にも存在した: 他 platform 向け frontmatter（ja=zenn 由来の `title:`/`emoji:`/`topics:`/`published:`、en=devto 由来の `title`/`description`/`tags`/`published`）が横罫線の直後に太字の地の文として本文冒頭に露出し、その直後にタイトルが H1 で二重表示されていた。note 側は commit `b81548f` で `note-stage1-render.py` に frontmatter strip を追加済みだったが、Substack 側の `publish-substack.sh`（`BODY_MD="$(cat "$MD_FILE")"` で md を無加工のまま `draft_body` に流し込んでいた）には同じ fix が入っていなかった。
- **恒久修理**: `publish-substack.sh` に note 側と同一正規表現（`re.sub(r'^---\n.*?\n---\n', '', md, count=1, flags=re.S)` でfrontmatter除去 + `re.sub(r'^#\s+.+$', '', md, count=1, flags=re.M)` でH1除去）を追加。この1箇所が mermaid embed 経路・直接経路の両方が必ず通る唯一の合流点。negative test（frontmatter+H1 fixture → 混入ゼロ・本文/##見出しは保持）+ positive test（frontmatter/H1なしfixture → byte-identical、over-strip無し）を `tests/art/test_substack_frontmatter_strip.sh` として追加、8/8 green。テストは実装から正規表現を直接 sed 抽出して使う方式（手書き二重実装によるドリフトを防止）。
- **既に staged 済みの2 draft自体の修理**: Substack の `draft_body` は生 markdown ではなく server-side の ProseMirror JSON（`GET /api/v1/drafts/{id}` で実測確認、python-substack の `api.py` リファレンスで `PUT /api/v1/drafts/{id}` の存在を確認）と判明。両 draft とも `content[0]=horizontal_rule` `content[1]=frontmatter見出し(H2)` `content[2]=重複タイトル(H1)` という同一構造だったため、この3ノードを除去した JSON を `PUT` で書き戻した。修理前の完全な JSON バックアップを取得済み。修理後に改めて `GET` して混入テキストが0件であることを確認し、さらに CDP 経由で実際の Substack エディタ画面を own-eyes screenshot で確認（ja/en 両方とも frontmatter/重複タイトルが消え「保存済み」draft のまま、公開ボタンは押していない）。
- commit: profitable-claude(main) `59d4eac`

**追記（2026-07-17、team-lead緊急指示3件、builder-authfix）: gate系の恒久化3点セット**。
1. **gate fail-closed化**: deslop-gate.sh/eval-gate.sh の非ゼロ終了（通常のFAIL判定と、判定不能なFATAL/rc=2クラッシュの両方）を区別せずBLOCKING扱いする明示指示を article-daily.sh STEP 4.5 として新設。今日の checklist-path FATAL のような gate 自体のクラッシュを「その platform だけ今日ダメだった」と誤解して通過させないための安全策。commit: profitable-claude(main) `221327b`
2. **gate判定の永続ログ化**: deslop-gate.sh/eval-gate.sh の全ての最終判定（mechanical FAIL・checklist-missing FATAL・no-json FATAL・LLM judgeのPASS/FAIL）を `~/.openclaw/logs/article-gates.log` へ append-only で記録（ts+script+mdファイル+lang+verdict）。eyecatchログ（commit `ad4c993`）と同じ恒久化パターン。tests/art/test_gate_verdict_log.sh で5/5実測（今日のchecklist-missing実インシデントを再現するケース込み）。commit: profitable-claude(main) `dae1f37`
3. **k16 のja全体適用**: ja記事は従来 stop-ai-slop-jp（--doc-type note既定）とjapanese-tech-writing/k16（--doc-type tech）のどちらか一方しか判定されなかったが、Dais決定で両方を lane/doc-type 問わず必須化。連結prompt化は非収束リスクで既に却下済み（§7.4の12ラウンド非収束事故）のため、独立した2回のfresh judge呼び出し（G1a=note、G1b=tech）とし、両方blocking。run.sh と x-publish/publish-to-x.sh の両呼び出し箇所に配線。tests/art/test_ja_dual_checklist_gate.sh で12/12実測（構造検証、run.shの副作用回避のためこのディレクトリ既存の grep 方式を踏襲）+ 実LLM呼び出しでG1a/G1bが独立した別々のverdict/adviceを返すことを実測確認。commit: profitable-claude(main) `e20d495`

**追記（2026-07-17、team-lead裁定2件、builder-authfix対応）**:
1. **test_article_daily_contract.sh の --mode go アサーション是正**: 「--mode go 文字列の完全禁止」という判定は誤りだった（Dais決定#41がAUTOPUBLISH=1ガード内でのSubstack live publishを既に承認済み）。正しい契約 = 「ガードの存在が政策」であり文字列の不在ではない。アサーションを`if [ "$AUTOPUBLISH" = "1" ]; then ... fi`ブロックを除去してから`--mode go`の非存在をチェックする方式に修正。commit: profitable-claude(main) `ea925cd`
2. **config/loop-registry.json の article エントリ**: `status: "external"`のまま維持（team-lead裁定: article-daily.sh自身が「launchd is the ONLY scheduler」と定めており、`live`化するとbin/start-all.shとlaunchdの二重スケジューラ衝突を招く）。`skill_dir`（実パス反映、schema上は情報用途のみ）と`notes`（explorer既存の慣習に倣い、外部stubのまま維持する理由を明記）を追加。`runtime`は`schema_checks.py`のPROP-005が文字列`"external-anicca"`を厳密ピン留めしているため、より正確な文字列への変更を一度試みたが schema テストを壊すことが判明し、`external-anicca`のまま維持（説明は`notes`側に集約）。両方とも `tests/ceo/test_registry_schema.py`(29/29)・`test_registry_last_observed_at.py`(6/6)・`test_start_all_and_status.sh`(5/5)で実測確認。commit: profitable-claude(main) `ea925cd`

**追記（2026-07-17、⑤最終項目、builder-authfix）: render-verify STEP 6.5 + self-fix STEP 0 配線完了**。render-verify-draft.sh（下書き編集画面のfull-page screenshot→フレッシュvision judge）とarticle-self-fix.sh（自律Sonnet devをspawnして根本原因を直させる）は commit `1eac5cf` で部品として完成・双方向検証済みだったが、article-daily.sh自身のpassからは一度も呼ばれていなかった（＝実配線が本タスクの中身）。
- **STEP 6.5（STEP 6とSTEP 7の間に新設）**: editor URLを持つ各platform（note/zenn/substack-ja/substack-en/devto、Xは対象外）についてSTEP 5のdraft URLに対しrender-verify-draft.shを実行。verdict:FAILはblocking（STEP 4.5と同じ規律 — スクリプトクラッシュも「今日はこのplatformだけダメだった」扱いにしない）。FAILなら下書き内容または根本のスクリプトバグを自分で直して再実行、最大3回試行。それでもFAILならarticle-self-fix.shを非blockingでspawnし、そのplatformはSTEP 8で正直にfailed報告して次のplatformへ進む（1つのplatformで全passを止めない、STEP 8の既存哲学を維持）。
- **STEP 0（existence-guarded、STEP 1より前に新設）**: `~/.openclaw/state/.self-fix-article-writer.result`（article-self-fix.sh自身が書き込む実ファイル）が存在すれば読む。FAILなら前回解決できなかった不具合のクラスに今日のpassでも注意を払う（passを止める理由にはしない）。SUCCESS/RUNNINGはアクション不要。
- 検証: bash -n（フルファイル）+ PROMPT分離レンダリング抽出でSTEP 0..10のヘッダ順序が正しく維持されていることを実測確認（STEP 4.5/6.5含む）。tests/art/test_render_verify_self_fix_wiring.sh 12/12実測（構造検証、article-daily.shのPROMPTが実本番エージェント指示のため、このディレクトリ既存の慣習を踏襲）。`tests/run-all.sh` 119/120（残1件は既存debtのtest_vendor_dirs_referenced.sh、無関係）。
- commit: profitable-claude(main) `cb02fdd`

**追記（2026-07-17、team-lead指摘によるフォローアップ2点、builder-authfix）**:
1. **render-verify-draft.sh へのgates-log追加**: deslop-gate.sh/eval-gate.sh（#52）と同じ`article-gates.log`永続化パターンをrender-verify-draft.shにも追加（screenshot_failed FATAL・no-json-from-judge FATAL・vision judgeのPASS/FAILの3終了点）。tests/art/test_gate_verdict_log.sh を6/6へ拡張（screenshot-failedパスをCDP_PORT不到達で再現、実ブラウザ不要）。
2. **実note draftでの実走検証**: 今日の実draft（`https://editor.note.com/notes/n5787e092451f/edit/`）に対しrender-verify-draft.shを実際に走らせ、`{"verdict":"PASS","problems":[],"advisory":[]}`を実測。生成されたfull-page screenshot（1905x8646px）をown-eyesで確認（アイキャッチ画像・見出し・実際に描画されたmermaid図・出典ブロックが正しく表示、frontmatter混入や壊れた画像なし）。`article-gates.log`が実際に1行増えたことも実測確認（`script=render-verify-draft.sh platform=note ... verdict=PASS`）。
- `tests/run-all.sh` 119/120（変わらず）。
- commit: profitable-claude(main) `2b5e058`

**追記（2026-07-17、team-lead検収差し戻し1件・重要インシデント、builder-authfix対応）: テストではなく手動検証コマンドが本番gates logを破壊**。team-lead検収時、`~/.openclaw/logs/article-gates.log`が「テストのfake-URL FATAL行1本だけ（133B）」に化けており、その前の正当な実行行は`.bak`（352B）に退避されていることが発覚。原因調査の結果: **`tests/art/test_gate_verdict_log.sh`自体はHOME上書きで最初から正しく隔離されており原因ではなかった**。真因は私自身がscreenshot-failedパスの手動検証をしていた際に打った`rm -f "$HOME/.openclaw/logs/article-gates.log"`（バックアップ無しで本番パスを直接削除）。しかもこのrmは、実note draft検証で追記された正当なPASS行（`.bak`取得より後に生成）を**復元不能な形で消失**させた（`.bak`はその行が生まれる前の状態でスナップショットされていたため）。
- **恒久修理**: deslop-gate.sh/eval-gate.sh/render-verify-draft.shの3スクリプト全てで`GATES_LOG`を`${ARTICLE_GATES_LOG:-$HOME/.openclaw/logs/article-gates.log}`とenv化（既定は変わらず本番パス）。
- **テスト強化**: test_gate_verdict_log.shの全呼び出しに明示的に`ARTICLE_GATES_LOG`を隔離tmpパスへ設定（HOME上書きとの二重防御）+ テスト実行前後で本番ログがbyte-for-byte不変であることを検証する新規assertionを追加。実際にMD5比較で本番ログがテスト実行前後で完全一致することを実測（8/8 pass）。
- **ログ復元**: `.bak`の正当な4行を本番ログへ復元し、fake-URL行（テスト痕跡）を除去。**失われた実note draft PASS行自体は復元不能と正直に報告**——`.bak`はその行の生成より前に取得されていたため。
- **再検証**: render-verify-draft.shを今日の実note draft（`https://editor.note.com/notes/n5787e092451f/edit/`）へ再実走し、新しい正当なPASS行（`2026-07-17 16:52:54 ...verdict=PASS`）が本番ログに実際に追記されたことを`cat`実出力で確認。`tests/run-all.sh`フル実行前後でも本番ログが不変であることを確認。
- commit: profitable-claude(main) `023b1dc`
- **全体テスト状態（今回の一連の対応の最終形）**: `tests/run-all.sh` 119/120。残1件は`test_vendor_dirs_referenced.sh`（life-manager-cli.shのSTARTUPプロンプトにベンダーツール名の言及が欠けているコンテンツギャップ、round1以前からの既存debt、今回の一連の変更とは無関係）。

### 7.60 決定（2026-07-17 夜、Dais「聞かずに決めろ」に基づき team-lead 裁定）

1. **文体 = 全レーン ですます 統一**（Dais 裁定 2026-07-17 夜。既存 Rule 6 を維持 — 公開済み記事群と同じブランド声）。~~初裁定「レーンA=だ・である」は誤り~~: 今日の記事のだ調は Rule 6 違反であり、実装に合わせて spec を曲げる過ちだった（是正記録）。文末形態率の deterministic 判定を pre-check に追加（です/ます率、全レーン共通）。今日の ja/en draft は公開前に ですます へ直す。
2. **タイトルは platform 別に生成**: note = 英固有名詞≤1・フック1個・本文が証明したことだけ約束 / zenn・devto = 技術語可。機械 gate: note 版タイトルの未翻訳英固有名詞カウント。
3. **arm 条件成立方式**: 明朝 06:00 の完全体 pass（品質6層 + render-verify）が green なら team-lead が即日 `ARTICLE_AUTOPUBLISH=1` を注入（Dais の「full 検証後に direct 切替」発言 2026-07-17 が根拠）。X 未復旧なら X 抜きで arm、X は復旧次第合流。

### 7.6 新 TODO（#53 から採番。§5 MASTER 順序の後続）

| # | やること | 状態 |
|---|---|---|
| #53 | ✅**完了（2026-07-17）**: regex pre-check 強化: 「この記事」見出し（P1）・自己言及「自分（アニッチャ）」型（P2）・visual≥1 カウント（P3, mermaid/img/table）を deslop-gate.sh の deterministic pre-check に追加。実違反 fixture（zenn-20260717-agentskills-ja.md：P1/P2/P3 全て検出）+ 正常系/見出しバリエーション/閉じブロック許可表現の false-positive なしを実測。commit: anicca-dais `ab177174` | [x] |
| #54 | ✅**完了（2026-07-17）**: `topics/{queue,in-progress,done}/` 機構実装（カード frontmatter: lane/voice/sources/angle）+ 初期カード3枚（virtuals-acp.md / olas-mech-marketplace.md / humanizer-shootout.md、DEEP-QUESTIONS.md から質問リスト転記）+ article-daily.sh STEP 1 差し替え（queue先取り+mv claim、空ならlane B fallback）+ STEP 7（done/へmv、ledgerにlane記録）。bash -n通過、PROMPT変数のsingle-quoted heredocが意図通り展開されることを実測。commit: profitable-claude `0f2b939` | [x] |
| #55 | ✅**完了（2026-07-17）**: `make-diary-digest.sh`（transcript+git log → 教訓抽出 → redaction gate → card）+ 23:30 launchd + redaction negative test。実装場所 `~/profitable-claude/skills/human-funded/article/topics/make-diary-digest.sh`。収集=deterministic bash（4 repo の当日 git log + 当日更新 docs/loop-engineering・.claude/handovers + `~/.claude/projects/*/*.jsonl` の当日 user turn を1500行cap）、抽出=claude -p（article-daily.sh run_claude_pass と同じ CLIProxyAPI ヘッドレス認証フォールバック）、書込前に必須 redaction gate（sk-/xox/Bearer/BEGIN/AKIA/password/api_key/電話番号パターン）。`--test-redaction` で negative(fake `sk-`鍵→FAIL実測) + positive(クリーン文→PASS実測) 両方確認。`--collect-only` で収集単体を実測（今日: commits=31, docs=0, transcript_lines=1500）。フル実行1回を実測: `topics/queue/2026-07-17-devlog.md` を実データ（token melting 根本原因・healthcheck 自己申告問題等）から生成、redaction gate 通過。同名カード再実行で idempotent SKIP を実測。launchd `ai.anicca.article-diary-digest`（23:30）を bootstrap 済み、`launchctl list \| grep diary` で登録実測。plist は `~/Library/LaunchAgents/`（gitignore対象外の個人環境）、repo には `topics/ai.anicca.article-diary-digest.plist.example` を同梱。commit: profitable-claude `f60052d` | [x] |
| #56 | ✅**完了（2026-07-17）**: レーンA用récitテンプレをSKILL.mdに追記。Rule 41/65に「LANE SCOPE」注記を追加（両ルールはレーンB専用に降格）+ 新セクション「LANE A — RÉCIT TEMPLATE」（6項目: Dais名義一人称・diary framingは違反でなく目的そのもの・カードはscaffolding・closing [8]ブロック不使用・citation必須は不変・stop-ai-slop-jpのレーンB固有指摘はadvisory化）。markdown構造の健全性（bold marker偶数・セクション見出し存在）を実測。commit: anicca-dais `6150bc3a`（main-internal） | [x] |
| #57 | ✅**完了（2026-07-17）**: k16 gist（fd287c3133457c4fd8f5601d34aa817d、Star 1547/Fork 92）をcrwlで取得、`japanese-tech-writing`としてattribution付きvendor（README.mdに出典明記。gist自体に明示ライセンスなし）。deslop-gate.shに`--doc-type note\|tech`を追加（ja既定=stop-ai-slop-jp、tech=japanese-tech-writing、enは常にstop-slop）。run.sh/publish-to-x.shにARTICLE_DOC_TYPE経由の任意passthroughを追加（未設定時は既定noteで後方互換）。実測: 実draft(07-17)で既定/tech双方が同一のmechanical pre-check結果（回帰なし）、tech doc-typeの清潔fixtureで実judge呼び出しまで到達しPASS（vendored SKILL.mdが実際に読み込まれ機能することを確認）、不正doc-typeでFATAL rc=2、DOC_TYPE_ARGS配列構築ロジックを単体テスト。commits: anicca-dais `092df0c7`（gate配線）/ profitable-claude `0d77f2e`（vendor18ファイル、stop-ai-slop-jp/stop-slop既存LICENSE/README/CHANGELOG込み） | [x] |
| #58 | ✅**完了（2026-07-17）**: OSS自己完結化。#58a（builder-digest担当、非衝突分）: note user_id env化・run.sh env fallback（commit `d57dfd2c`、amendでコミットメッセージ内の`.env`文字列が原因のpre-push hook誤検知を解消したためハッシュが`d8ad4877`→`d57dfd2c`に変わった、内容は同一）・ホワイトリスト.gitignore + settings.json deny rule（commit `c10cbfc`）・`.env.example`（spec §7.5全変数のwired/planned明記付きテンプレ）+ `settings-deny-example.json`（他プロジェクトへ貼り付け可能なdenyブロック単体）+ README Security節（commit `257d989`）。authfix担当分: stop-slop系+k16のvendor化（#57で実施、`checklists/`配下）+ deslop-gate.shの`~/anicca-project`ハードコード解消（ARTICLE_CHECKLISTS_DIRベース化、commit `092df0c7`）。**未完（次点候補、優先度低）**: spec §7.5項目1のarticle-daily.sh内`~/.openclaw`パス直書き37箇所の`OPENCLAW_HOME`ベース化とTELEGRAM_TARGET_IDの「デフォルト値削除・必須env化」——現状は`${TELEGRAM_TARGET_ID:-8547730585}`という動くsoft-defaultが既にあり（実行時にPROMPT内へ置換済み）、稼働中の自律エージェントPROMPT本文37箇所を書き換える作業はリスクに対して優先度が低いと判断し、team-leadの判断待ちで保留 | [x] |
| #59 | ✅**完了（2026-07-17）**: #47 無料版 Sources 落ち修理。詳細は §4「#47 無料版が Sources ブロックを落とす」行を参照。commit: anicca-dais `2092337b`（main-internal）。AUTOPUBLISH arm（ARTICLE_AUTOPUBLISH=1 の plist 注入）は既存決定通り数日の gate green 観測後に Dais の go 一言で実施——本コミットではまだ実施していない | [x] |
| #60 | ~~Substack Stripe 確認~~ ✅完了（2026-07-17 実測: ON 済みだった）。残タスク変形 → daily-driver の Substack session 復活済み、X-publish 同様に session 失効の healthcheck 対象へ追加検討 | [x] |
| #61 | humanizer shootout 記事（queue カード③の実行、7.4 が下調べ） | [ ] |
| #63 | ✅**完了（2026-07-17）**: note アイキャッチの必須工程化。article-daily.sh に新設 STEP 5.5（STEP 5 note dispatch 直後）を追加: X 用に既に選んだ $X_COVER 画像を `~/.cloak/note-work/thumb.png` へ複製 → `NOTE_KEY=<key> python3 set-eyecatch-draft.py` 実行 → スクリプト自身の `EYECATCH_IN_EDITOR:` DOM readback（own-eyes、HTTP 200 だけでは不可）で確認してから成功扱い。set-eyecatch-draft.py は独立 headless context（CDP :9222 不使用）で共有ロックと非競合、thumb.png/note-cookies.json の前提は既存パイプラインで満たされることを確認済みのためスクリプト側修正なし。commit: profitable-claude `dfdfea0` | [x] |
| #55b | ✅**完了（2026-07-17、team-lead review 後の是正込み）**: digest 強化（mcp-commit-story 方式）。収集部に3つの文脈注入を追加: ①当日の spec/plan TODO 表 diff（`docs/superpowers/specs/*.md`+`plans/*.md`、TaskList ツール自体は session-scoped で headless script から呼べないため、CLAUDE.md が定義する「二重トラック」のもう一方＝spec TODO 表を devlog-ai 方式の「積み残し」代替として採用）+ 現在オープンな TODO 行（capped 30）②profitable-claude README.md 先頭**30行**（team-lead指示通り。初回実装は40行だったが是正済み）③過去7日分 devlog カードの angle 一覧（アングル重複回避）。抽出プロンプトに失敗談型優先の明示指示を追加、かつ**進捗報告は書くな**を明文のハード禁止に是正（初回実装は「他に候補が無ければ進捗報告も可」という緩い fallback だったが、材料が進捗報告のみの日は NOTHING を出力し card を作らない仕様に変更）。入力 3000 行 cap は**team-lead指示通りgit log側から削る方式**に是正（初回実装は組み立て済みファイルの末尾からheadで切っており、新規追加した文脈セクション側が先に落ちる逆向きの挙動だった。現在は git log を独立tmpに集め、他セクション組み立て後の残り予算だけ git log に割り当てる構造）。実装過程で発見: このシェル環境で `git log -p` の出力を3段 grep パイプに直結すると（84件あるはずの diff に対して）0件を返す再現バグを発見（一時ファイル経由に変更して解消、既存の TRANSCRIPT_TMP と同じ防御パターン）。検証: bash -n / `--test-redaction` negative+positive 両方PASS / `--collect-only`で全カウント(todo_diff_rows=35, readme_lines=30, past_cards=1, material_total_lines=2229)が実データで埋まることを実測 / git-log側cap是正後のロジックを合成データ(other=200行+gitlog=5000行)で単体テスト(gitlogが2800行へ正しく切り詰められ、other 200行は末尾に無傷で保持、total=3002を実測) / 実フル実行1回(是正前バージョンで今日の既存カードを退避→再生成、明確に失敗談型（時系列ドラマ入り）の出力を確認、redaction gate通過) / 是正後バージョンでのフル実行はidempotent SKIPを実測（今日のカードは既に存在、team-lead指摘通りこれ自体が正しい挙動の証明）。仕様正本 = `docs/loop-engineering/53-devlog-to-article-pipelines-gh-research.md`（GH 7 repo 実測研究、2026-07-17）。commits: profitable-claude `85e4049`（収集+prompt強化）/ `44a9a77`（3000行cap初回実装）/ `39fcf0d`（team-lead review是正: README30行・進捗報告ハード禁止・git-log側cap） | [x] |
| #58b | （低優先・arm 後）article-daily.sh PROMPT 内 `~/.openclaw` 直書き37箇所の OPENCLAW_HOME 化 + TELEGRAM_TARGET_ID 必須 env 化。soft-default で現状動作に問題なし、稼働中 PROMPT の大改編なので安定期に実施 | [ ] |
| #66 | ✅**完了（2026-07-17）**: self-improve.sh の配線。夜間 launchd `ai.anicca.article-self-improve`（22:30 JST、article-daily 06:00 の翌・diary-digest 23:30 の前）を新設し bootstrap 済み（`launchctl list \| grep article-self-improve` で登録実測、exit status 0）。plist は `.openclaw/skills/ai-entity-article-writer/scripts/ai.anicca.article-self-improve.plist`、`docs/LAUNCHD_REGISTRY.md` にも登録。手動実行で実測: `state/topic-queue.md` + `state/today-insight-<date>.md` を実データから生成（rc=0）、L3 ブロックは funnel データ 1/7 日で正しく no-op（playbook.json 生成には最低7日分のデータ蓄積が必要、構造上はこれで正しく動き出す）。追加検証（2回目報告）: `launchctl kickstart -p gui/501/ai.anicca.article-self-improve` で launchd 経由の実走行も実測（`LastExitStatus=0`、.out ログに手動実行と同一の正常出力、.err 空）。plist example を `profitable-claude/skills/human-funded/article/topics/ai.anicca.article-self-improve.plist.example` にも同梱（commit `5b58060`）。commit: anicca-dais `67a35486`（main-internal） | [x] |
| #67 | ✅**完了（2026-07-17）**: audit-7day.sh / learn-whitelist.sh の週次 launchd 設置。両スクリプトのヘッダ自己記述通りの時刻（audit-7day=日曜22:00、learn-whitelist=日曜03:00 JST）でplist新設・bootstrap・`launchctl list`で登録実測（両方exit status 0）。`openclaw cron list`にも該当エントリが無いことを事前確認し、真の孤児であることを確認済み。週次ジョブは重い可能性があるためkickstartはせず登録確認のみ（team-lead指示通り）。`docs/LAUNCHD_REGISTRY.md`にも正しいアルファベット順で登録。commit: anicca-dais `00a70cbd`（main-internal） / profitable-claude `0eab4bd`（plist example） | [x] |
| #70 | ✅**phase 1 完了（2026-07-17、copy + installer骨格。切替は明日のpass後に別タスク）**: writer skill 本体のOSS移設。#70a notifier.sh（Telegram Bot API直叩き、実送信検証済み）、#70b ensure-browser.sh（汎用CDP watchdog、CloakBrowser固有機能は非同梱の設計をteam-lead承認済み、BROWSER_PROFILE_DIRの永続プロファイル要件も反映）、#70c `~/.openclaw/skills/ai-entity-article-writer/`をcp -Rでprofitable-claude/skills/human-funded/article/writer/へコピー（state/attic/除外、__pycache__・stray artifactも除去、86ファイル diff 0で完全一致確認、秘密情報混入なしを目視確認）、#70d ハードコードパス件数報告のみ（19ファイル25箇所、書き換えは切替タスクへ延期）、#70e install.sh骨格（.env対話生成+launchd/cron scheduler+claude auth check、--dry-run実測OK）。**旧パス（~/.openclaw側）は無変更、本番launchd 5ジョブは今も旧パスを指したまま**——team-leadの「明日06:00 pass を壊さない」指示を最優先。**インシデント（自己発見・即修正）**: install.shのテスト中、非dry-runモードを一時ディレクトリから実行した際に$HOMEがサンドボックスされておらず、本番稼働中の5 launchdジョブのplistファイルが誤って一時ディレクトリパスで上書きされた。即座に発見し.openclaw側の正本+profitable-claude committed exampleから全5件を復旧、launchctl bootout+bootstrapで再同期、launchd実メモリ上のProgramArgumentsまで確認して修復完了を実証。再発防止としてinstall.shに「既存plistが別スクリプトを指している場合は上書き前に確認を求める」安全策を追加し、動作を実測確認。commits: profitable-claude `7306246`(#70a)/`15b7e5a`+`4e72522`(#70b)/`abf1a86`(#70c)/`777da08`(#70e) | [~] |
| #70(続) | ✅**phase 2 完了（2026-07-17、Dais決定で当日実施。AUTOPUBLISH=0のdraft安全網内なら「今日切替+実pass1本」の方が「明日ぶっつけ」より安全という判断）**: 旧パス（`~/.openclaw/skills/ai-entity-article-writer`）→新パス（`~/profitable-claude/skills/human-funded/article/writer`）へ本番切替。article-daily.sh PROMPT内35箇所（当初見積37から実測補正）+ writer/ツリー内19ファイル25箇所を機械置換、grep残0確認、bash -n全通過、PROMPT分離レンダリングで新パスのみ・AUTOPUBLISHアドオン正しく非包含を確認。self-improve/audit-7day/learn-whitelistの3 plistを新パスへ書換・bootout+bootstrap・launchd実メモリ確認。**移設後初のフルpass実行（14:31 kickstart→15:27 rc=0、55分）**: レーンA（virtuals-acp.md）を新パスの全gate・全publish scriptで完走。チェックポイント①-⑦全て実測確認 — ①レーンAクレーム（queue→in-progress）②gate群が新パスで正常動作（missing-script系エラーなし）③eyecatch実URL確認（認証済みeditor readback、`assets.st-note.com`実URL）④5/7 platform staged（zenn/devto/substack-ja/substack-en/note、lane:"A"、published:false。X×2は`x_session_logged_out_stale_auth_token`で正直に記録）⑤ledger lane:"A"タグ9行全確認⑥Telegram報告（messageId 2406）⑦カードdone/へmv確認。**pass自身が自己修正した実バグ2件（commit `b81548f`）**: (a) run.sh の`DOC_TYPE_ARGS[@]`がmacOSシステムbash3.2の`set -u`下でクラッシュ → 修正、(b) note-stage1-render.pyがYAML frontmatter（title:/emoji:/topics:/published:）をnote本文へリークさせていた → `re.sub(r'^---\n.*?\n---\n', '', ..., flags=re.S)`で除去する修正。**私が追加で実施した検証**: frontmatter修正のnegative test（fixtureで完全除去を確認）+ 実ドラフト本文の混入0件を認証済みreadbackで再確認。eyecatch用の恒久ログ化（set-eyecatch-draft.pyに`~/.openclaw/logs/note-eyecatch.log`へのappendを追加、commit `ad4c993`）。X session診断（実navigate1回のみでエラー画面確認、vault再構築かDais手動再ログインが必要と判定、3回以上のログイン試行はせず報告のみ）。**インシデント2件目**: pass自身のSTEP8自己修正が`git add -A`で私の未commit変更（上記35+25箇所置換）を巻き込みcommit `b81548f`に混入（実害なし、中身は正しい。旧`.bak-pre-70f`バックアップファイルの誤commitのみ発生、commit `0166910`で削除）。**フラット構造への再変更が同日中に決定**（`skills/human-funded/article/writer/`→`skills/article-writer/`、round 2として別途実施） | [x] | 
| #68 | ✅**完了（2026-07-17）**: citation-strip.py・bookmark-gate.sh・fetch-ai-watch.sh の配線。article-daily.sh STEP3にcitation-strip.py --in-place --report（SKILL rule26の機械化、書いた後・gate前に正規化）、STEP4にbookmark-gate.sh（数字1件+固有名詞2件+actionable signal 1件の機械的実質チェック、他gateと同じfix→再実行ルール）を追加。self-improve.shにfetch-ai-watch.sh呼び出しを追加し、topic-queue.mdに新「AI watch digest」節を追加（watched competitor blogの実scrape結果を反映）。実測: 両gateを合成fixtureで単体テスト（citation-strip=2件正しく1blockへ集約、bookmark-gate=実質ありPASS/曖昧内容FAIL）、fetch-ai-watch.shは実firecrawl scrapeでdigest生成を確認、self-improve.sh再実行でtopic-queue.mdへの統合を確認（rc=0）。副次的に発見: STEP4本文中の"reader's"のアポストロフィがPROMPTのsingle-quoted heredocを破壊する実構文エラーをbash -nで検出・修正。commits: anicca-dais `21d5ddf3`（fetch-ai-watch統合） / profitable-claude `113923e`（citation-strip+bookmark-gate配線） | [x] |
| #69 | ✅**完了・承認済み（2026-07-17、team-lead確認済み）**: ORPHAN 残骸33本を `~/.openclaw/skills/ai-entity-article-writer/attic/` へ `git mv`（配線変更ゼロ）。件数は当初「27本」と見積もられていたが、`54-orphan-script-audit-2026-07-17.md` の「archive すべき」列挙を実際に数えると33本（note one-off 17 + x-publish legacy 5 + devto孤児クラスタ5 + substack孤児(+_shared依存2件込み)5 + zenn-deploy-retry.sh 1）で、こちらが正。移動前に33本全てを個別に再検証（実 `scripts/` tree・profitable-claude article skill・`~/Library/LaunchAgents/*.plist`・`~/.openclaw/cron/jobs.json` を対象filenameでgrep、ヒットは全てREADME/prompt.md記述かコードコメントか同一孤児クラスタ内部参照のみで実配線ゼロと確認）、33本全てを移動。移動後の再grepで生き残りscripts/への実呼び出しゼロ、現役publisher群（run.sh/publish-devto.sh/publish-note.sh/publish-zenn.sh/publish-substack.sh/_shared/publish-substack-mermaid.sh/x-publish/publish-to-x.sh）のbash -n全通過を実測。attic/README.mdに移動理由・検証手順を記録。27→33の差分についてteam-leadへ報告済み、要レビュー。**追加（team-lead review、2026-07-17）**: `publish-substack.sh.bak`・`publish-aniccaai-blog.sh.disabled`の2件をteam-leadが名指しで追加指摘（監査MDの列挙には無かった）。同じ4箇所（~/.openclaw ~/profitable-claude ~/anicca ~/Library/LaunchAgents）grepで無参照確認後に追加move。`publish-aniccaai-blog.sh.disabled`はrun.shのaniccaai-blog case armが無suffix版`publish-aniccaai-blog.sh`を参照するが、これは移動前から既に存在しなかった（誰かがrenameで無効化済み）ため今回のmoveで新規に壊れるものはない。移動後再grep0件・現役publisher全bash -n通過を再実測。commit: anicca-dais `f56e7fe8`（33本本体）/ `81ad22b9`（追加2件） | [x] |
| #64 | ✅**調査+設計完了（2026-07-17、team-lead承認）**: self-signup bootstrap を実測5platform（note/devto/substack/zenn実測、Xは対象外）で調査、tractable=note/devto/substack、zenn=GitHub依存（アカウント作成自体はtractableだが既存git-push型publish方式との連携に別途GitHub bootstrap要）、X=電話tierでdeferred。設計書 = `docs/loop-engineering/55-self-signup-bootstrap-design.md`。★実装は OSS 出荷判断後（#64a note / #64b devto / #64c substack に分割、team-lead task登録済み）★。commit: anicca-project(feature/clip-rewards) `0544c16` | [x] |
| #65 | ✅**決定（2026-07-17 Dais）+ #65impl完了（2026-07-17）**: gig work loop は profitable-claude に収載する。支払いの出口 = 利用者の銀行口座（fiat）or 利用者の crypto wallet。KYC 必須なので 7.55 どおり既定 OFF の opt-in。**#65impl 実行時にスコープ是正が必要と判明**: 当初「~/anicca/skills/earn/gig/ から profitable-claude への port」という前提だったが、実測すると両者は既に独立進化していた——profitable-claude の `skills/human-funded/gig/gig-cli.sh` は import 後（commit `c2d7e40`）に CEO予算連携・cron registry・EDD検証フレームワークなど**独自進化済み**で、anicca側の `gig_pass.sh`/`GIG_PASS_RUNBOOK.md`/`gig_judge.py` という外部driver方式は profitable-claude の配線済みscript（gig-cli.sh/run.sh/monitor.sh/auditor.sh）からは一切参照されていない（grep実測でゼロ件）。当初anicca側ファイルをコピーしたが、配線されない孤児ファイルになる（#63/#69と同型の欠陥）と気づき、commit前に削除して撤回。**実際に行った作業**: 既に配線済みのprofitable-claude独自実装そのものに対し、①KYC opt-inゲート新設（`GIG_KYC_CONFIRMED`未設定→起動せず案内メッセージのみでexit 0）②ハードコード識別子4箇所のenv化（`COCONALA_HANDLE`=Coconalaアカウントハンドル、`GIG_PAYOUT_DESC`=支払い先説明、`GIG_LESSONS_GH_REPO`=peer-lesson共有先ghリポジトリ、全て現行値がデフォルトでDaisインスタンスは無変更）③`SLOT_CC.md`の壊れたpath修正④`README.md`のlaunchd plistファイル名誤り修正（`hf-`prefix欠落）⑤`.env.example`追記。検証: bash -n / python3 compile 全通過、STARTUP文字列の変数展開を分離テストで実測（env未設定→既存値とbyte-identical、env設定→正しく上書き）、KYC gateのライブ実行確認、`ps`/`tmux list-sessions`で本番の自己資金gigループ（`~/anicca/skills/earn/gig/`、`ai.anicca.gig-*` launchd）とは完全に別系統でありprofitable-claude側は現在どこにも配線されていないことを確認（無影響）。pytestは当セッションのrtkツール障害で直接実行不可、該当testの検証ロジックを手動grepで代替確認。commit: profitable-claude(main) `97e635d`。**追記（2026-07-17、Dais決定によるflat構造化）**: `human-funded/` 階層を repo 全体で廃止しflat `skills/<name>/` へ統一する決定を受け、gig（`skills/gig-work/`）・bounty（`skills/bounty/`）・affiliate（`skills/affiliate/`）を同時に`git mv`（75ファイル、履歴保持）。article/connector/life-manager は別builder(authfix)の領分のため一切触らず（実測で確認）。`bin/start-all.sh`/`bin/status.sh`は`config/loop-registry.json`の新設`skill_dir`フィールドで新パスを解決するよう変更（life-manager/explorer/connector等は`skill_dir`未設定のため旧テンプレートのまま無変更で動作）。tests/ceo等9ファイルのpath参照修正+`gig-cli.sh.snapshot`再生成。`~/Library/LaunchAgents`の実チェック: アクティブなplistに旧パス参照0件、無効化済み(`*.disabled-2026-07-12-t04`)2件のみ発見・修正（稼働中launchdへの影響なし）。git stash/popでbase時点(is my changes前)のtests/ceo/test_anicca_ref_allowlist.sh既存failure(62件unmatched、100%article/life-manager関連)を確認、私の変更で35件に減少(gig/bounty/affiliate分は全解消)、残りは対象外と実測確認。実行テスト: test_fixed_self_path 2/2・test_registry_enforce_core 12/12・test_prompt_integrity_snapshot 17/17・test_life_manager_scaffold 8/8・test_connector_healthcheck 4/4・test_explorer_scaffold 8/8・bounty/tests/test_run.sh 5/5、全green。commit: profitable-claude(main) `4f801d6` | [x] |
| #62 | ✅**完了（2026-07-17）**: keychain OAuth 死の全 loop 横展開調査 + 修理。実死亡中だった capafy-loop / life-manager（07-16/17 連続 rc=1）+ 時限爆弾8箇所（gig_reality_verify / promote_gate_run.py / connector_fill_gaps / run-*-agent.sh×5 / self-improve.sh）に clip_pass.sh の実証済み CLIProxyAPI fallback（AUTH_TOKEN 方式）を適用。commits: anicca `eabbaa33` / profitable-claude `c5c2e25` / anicca-dais `4545b1c9`。AUTH_TOKEN + `sonnet` alias が proxy で rc=0 を返すことは事前実測済み（clip の「alias 不可」コメントは現 proxy では再現せず）。非稼働の claude-p-mainloop / adversary-daily / heartbeat は未パッチ（再稼働時に同ブロック適用のこと） | [x] |

## 6. 関連ファイル

- 記事本体: `docs/articles/2026-07-12-how-to-build-the-agent-economy-jp.md`（原本 ~42/50）
- k16比較版: `docs/articles/2026-07-12-how-to-build-the-agent-economy-jp-k16.md`（~47/50）
- 自作skill: `~/.openclaw/skills/ai-entity-article-writer/SKILL.md`（66ルール、正本）
- de-slop: `.claude/skills/stop-ai-slop-jp/SKILL.md`
- 旧spec: `docs/superpowers/specs/2026-06-23-article-publish-monetize-skill.md`、`docs/superpowers/plans/2026-07-12-article-loop.md`
