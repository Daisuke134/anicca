# Article-Earn Loop — 作業 SPEC（唯一の正本 / 随時更新）

> ★このタスク(article-earn loop)の SPEC はこの1ファイルだけ。**新規ファイルを作らない。** 理解が進む度・進捗する度にここを更新（future self と他 agent が status 再検索でトークンを溶かさない為）。
> 関連: 記事ブロック承認状態=`docs/articles/2026-07-12-agent-economy-REVIEW-STATUS.md` / 親spec=`docs/superpowers/specs/2026-07-13-profitable-claude-earn-loops-spec.md`。
> 進捗の二重トラック: このファイル §5 ＋ TaskList tool(#9-25)。

**Goal**: 人間らしい（AI slop ゼロの）日本語+英語の記事を書き、全platformへ publish し、writing で **10k MRR** を no-human-in-the-loop で稼ぐ loop を作る。土台 skill = `~/.openclaw/skills/ai-entity-article-writer`（実測 ~90% 完成。執筆playbook+全publisher+収益化コード[note membership/paywall]+verifier部分+self-improve部分が既に在る）。

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

## 5. TODO（TaskList #9-25 と同期。順序 B→C→D→E→A。★随時 status 更新★）

方針: skill を「動く」に直す(B) → verifier(C) → loop 自走(D) → 換金(E) → その loop で agent-economy 記事を publish(A=テスト出力)。記事を手で出さない。TikTok は全体が回ってから追加（Dais 2026-07-15）。

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
- [ ] #16 T4 VISUALS(Mermaid/表→PNG/eyecatch) を run.sh に組込み
- [ ] #17 T5 de-slop ゲート(stop-ai-slop-jp/stop-slop)配線（今 language+seo のみ）
- [ ] #18 T6 eval「賢い読者/Daisが払うか」/50 + fact 配線（fresh adversary）

### PART C — verifier
- [ ] #20 V1 L4 reality-gate(session restore→ログアウト実見→naturalWidth>0→draft確認、公開ならFAIL)

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
