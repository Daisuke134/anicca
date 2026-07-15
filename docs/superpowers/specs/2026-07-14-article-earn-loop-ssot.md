# Article-Earn Loop — SSOT（2026-07-14）

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

## 5. TODO（granular・これが正本。上から順に消す）

### A. 既に書いた agent-economy 記事を JP+EN で ship する（即・独立）
- [ ] A1  JP ship版を確定（`jp-k16.md`=47/50 を採用、原本は捨てる）
- [ ] A2  JP Mermaid 図3枚を PNG レンダリング（note は Mermaid 非対応）
- [ ] A3  JP 表を PNG レンダリング（note は表 非対応、`note-render-tables.py`）
- [ ] A4  JP eyecatch/cover 画像を生成（GPT-image）
- [ ] A5  note に draft投稿 → screenshot verify → meta.json（買切+定期購読の両対応）
- [ ] A6  Zenn に draft投稿（frontmatter、1記事/24h rate 注意）→ verify
- [ ] A7  Substack-ja に draft投稿 → verify
- [ ] A8  X Articles JP に draft投稿（clipboard paste が前draft破壊に注意）→ verify
- [ ] A9  tiktok 画像 JP 生成
- [ ] A10 EN Mermaid 図3枚を PNG レンダリング
- [ ] A11 EN cover 画像を生成
- [ ] A12 dev.to に draft投稿（`published:false` 固定）→ verify（naturalWidth>0）
- [ ] A13 Substack-en に draft投稿 → verify
- [ ] A14 X Articles EN に draft投稿 → verify
- [ ] A15 tiktok 画像 EN 生成
- [ ] A16 全 draft の URL を meta.json に記録。公開ボタンは Dais 手動のみ

### B. loop 化（skill を良く+無人化+換金+自走）
- [ ] B1  k16 の7ルールを playbook WRITE-JP に移植（悪い例→良い例1行、bloat無し）
- [ ] B2  ECC+Karpathy 型を playbook WRITE-EN に移植
- [ ] B3  de-slop→eval /50「Daisが自腹で払うか」→fact の3ゲートを run.sh/gate群に正式配線
- [ ] B4  ③RUN→受領書 と ⑤VISUALS(mermaid→PNG, cover生成) を run.sh に組込み
- [ ] B5  記事ごと手書き publish script を廃止→パラメータ化（無人化の鍵）
- [ ] B6  note login の Vue reactivity bug 修理
- [ ] B7  X session 再取得
- [ ] B8  ⑦に換金ノード追加: note 有料/メンバーシップ ON + Substack 有料tier ON
- [ ] B9  Capafy に WRITE エンジン単体を出品（publish部を剥がす、即金ライン）
- [ ] B10 LEARN: CVR/売上分析 + ベスプラ常時検索 + 成功記事copy → PLAYBOOK 自動書戻し
- [ ] B11 全platform横断の売上 ledger（誰がいくら払ったか）
- [ ] B12 cron/launchd(`ai.anicca.article-daily`) 再有効化 = 俺抜きで自走開始

## 6. 関連ファイル

- 記事本体: `docs/articles/2026-07-12-how-to-build-the-agent-economy-jp.md`（原本 ~42/50）
- k16比較版: `docs/articles/2026-07-12-how-to-build-the-agent-economy-jp-k16.md`（~47/50）
- 自作skill: `~/.openclaw/skills/ai-entity-article-writer/SKILL.md`（66ルール、正本）
- de-slop: `.claude/skills/stop-ai-slop-jp/SKILL.md`
- 旧spec: `docs/superpowers/specs/2026-06-23-article-publish-monetize-skill.md`、`docs/superpowers/plans/2026-07-12-article-loop.md`
