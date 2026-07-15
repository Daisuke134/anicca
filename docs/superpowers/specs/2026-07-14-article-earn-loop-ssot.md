# Article-Earn Loop — 研究/設計メモ（2026-07-14）

> ⚠️ **これは SoT ではない**（2026-07-15 訂正）。本物の SoT = ①`docs/articles/2026-07-12-agent-economy-REVIEW-STATUS.md` ②handover `2026-07-14_0629.md` の Goal A ③`docs/superpowers/specs/2026-07-13-profitable-claude-earn-loops-spec.md`。本ファイルは skill選定/収益化 research の参照メモとして残す。

**Goal**: 人間らしい（AI slop ゼロの）日本語+英語の記事を書き、全platformへ publish し、writing で **10k MRR** を no-human-in-the-loop で稼ぐ loop を作る。

このファイルが article-earn loop の唯一の正本（SSOT）。進捗はここと TaskList tool の二重トラック。

---

## 0. 前提となった research（一次ソース）

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

## 5. TODO（granular・LOOP-FIRST。ONLY working on = article loop）

方針: **記事を手で出さない。** loop を動く状態にする → loop に agent-economy 記事(JP+EN)を出させる → 動くのを見る → cron で自走。記事の ship は STEP2(loop のテスト出力)であって手作業ではない。全体が「動く」ことが最優先。

### STEP 1 — loop を「任意の1記事を端から端まで draft できる」状態にする
- [ ] L1 記事ごと手書き publish script を廃止→パラメータ化（`--markdown-file` で任意記事を流せる）★無人化の鍵
- [ ] L2 run.sh に ⑤VISUALS 組込み: Mermaid→PNG / 表→PNG(note用) / cover 生成
- [ ] L3 run.sh に de-slop→eval「Daisが払うか」→fact の3ゲート配線（今は language+seo のみ）
- [ ] L4 note login の Vue reactivity bug 修理
- [ ] L5 X session 再取得
- [ ] L6 k16の7ルール→playbook WRITE-JP / ECC+Karpathy→WRITE-EN 移植（今後 loop が書く記事の質）

### STEP 2 — TEST: loop に agent-economy 記事を出させ、動作を見る（= ship はここ）
- [ ] L7  jp-k16.md を loop に投入 → まず zenn/dev.to(mermaid native) から draft+verify、動くのを見る
- [ ] L8  → note(PNG必須)/Substack-ja/X-ja も draft+verify
- [ ] L9  en.md を loop に投入 → dev.to/Substack-en/X-en draft+verify
- [ ] L10 全 draft URL を meta.json 記録 + screenshot で Dais 確認（公開ボタンは押さない）

### STEP 3 — 換金ノード + 自走
- [ ] L11 ⑦に note有料/メンバーシップ ON + Substack有料tier ON（¥0→初売上）
- [ ] L12 LEARN: CVR分析+ベスプラ検索+成功記事copy→PLAYBOOK自動書戻し
- [ ] L13 Capafy に WRITE エンジン出品（publish部剥がす、即金）
- [ ] L14 全platform横断の売上 ledger
- [ ] L15 cron/launchd(`ai.anicca.article-daily`) 再有効化 = 俺抜きで自走開始

## 6. 関連ファイル

- 記事本体: `docs/articles/2026-07-12-how-to-build-the-agent-economy-jp.md`（原本 ~42/50）
- k16比較版: `docs/articles/2026-07-12-how-to-build-the-agent-economy-jp-k16.md`（~47/50）
- 自作skill: `~/.openclaw/skills/ai-entity-article-writer/SKILL.md`（66ルール、正本）
- de-slop: `.claude/skills/stop-ai-slop-jp/SKILL.md`
- 旧spec: `docs/superpowers/specs/2026-06-23-article-publish-monetize-skill.md`、`docs/superpowers/plans/2026-07-12-article-loop.md`
