# Agent tool-calling ベストプラクティス × Franklin loop 実コードのギャップ分析

日付: 2026-07-18 ／ 調査: bp-research(web) + franklin-code-read(実コード deep-read) ／ 統合: main session
目的: 「franklin/claude-p が人間ゼロで外部から稼ぐ」goal の律速が tool-calling 品質にあるかを確定し、直し方を決める。

## A. 外部ベストプラクティス（一次ソース）

| # | ルール | 出典 |
|---|---|---|
| 1 | **説明の質が性能を決める最大要因**。各 tool 最低3-4文: 何をする/いつ使う/いつ使わない/各引数の意味 | platform.claude.com docs: "Provide extremely detailed descriptions. This is by far the most important factor" |
| 2 | 新入社員に説明するつもりで書く（暗黙知を明示） | anthropic.com/engineering/writing-tools-for-agents |
| 3 | **多段 workflow を1つの高レベル tool に統合**（API を粒々でラップしない） | 同上 + tool-use docs |
| 4 | **tool 数を絞る**: BFCL 実測で tool 4個→51個で選択精度 43%→2%。メニューは1回 5-8個 | tianpan.co/blog/2026-04-09-tool-selection-problem |
| 5 | tool 定義はトークンを食う: 58 tool ≈ 55,000 tok | 同上（Anthropic 計測の引用） |
| 6 | エラーは actionable に（正しい入力例を添えて返す） | writing-tools-for-agents |
| 7 | レスポンスは高シグナルのみ・構造化（UUID 羅列でなく意味語） | 同上 |
| 8 | poka-yoke: 引数設計でミスを構造的に不可能に（例: 絶対パス強制） | anthropic.com/engineering/building-effective-agents |
| 9 | 複雑 tool には `input_examples` | tool-use docs |
| 10 | eval 駆動: 実タスク数十本で accuracy/呼び出し数/токен/エラー率を計測し transcript を解析して磨く | writing-tools-for-agents |

失敗モード(深刻度順): ①tool 過多で選択精度崩壊(+存在しない tool を hallucinate) ②token 爆発 ③曖昧・重複 description ④形式は正しいが意味が誤る silent error ⑤低レベル API 形状。

## B. Franklin loop の実態（file:line、franklin-code-read 実測）

1. **tool は実質1個 `run_skill`**（`prompt.mjs:175-211`）。slot enum(live 12個) + `args` は `additionalProperties:true` の自由形式（`prompt.mjs:198-201`）。skill 個別の args schema 無し。
2. **description は registry.json の summary 1行だけ**。SKILL.md 本文(x402-sell の100行 recipe、hl-trade の戦略)はモデルに一切渡らない。`run_skill` の desc は `prompt.mjs:187-193` のハードコード固定文。
3. ★**prompt/registry の乖離 = 実バグ**★: system prompt が「COLONY BOOTSTRAP PRIORITY: FIRST action MUST be `economy/gig`」(`prompt.mjs:120-127`)と命じるが **`economy/gig` は registry に存在しない**（live は economy/ubi・economy/lending）。`hl_trade`・`token_launch` も prompt で推奨されるが dormant で enum 外。**モデルは毎 wake「選べない物を選べ」と指示されている**。失敗モード①(hallucinate)の教科書パターン。
4. **feedback は生 stdout 900字の切り詰め**（`index.mjs:757`→last20 が次 wake の prompt 末尾へ）。構造化(JSON の sales/error/PnL)ではない。selfEval の earnSteer(`self-eval.mjs:58-60`)だけが構造化されている。
5. **x402_sell tool は「serve が上がってるか確認」だけ**（`earn/run.sh:275`）。reprice/商品追加/改廃/登録の店管理 action はモデルから呼べない。= 店の lifecycle が menu に無い(SELF-STORE-1 の根拠、実コードで確定)。
6. **runtime 分岐**（`brain.mjs:33-49`）: franklin = ClawRouter HTTP + OpenAI 互換 `tools:`（native tool-calling）。claude-p = `claude -p` subprocess に **schema をテキストで手書き注入**（`brain.mjs:200-216` が JSON 模倣を few-shot 矯正）= native tool channel 不使用。弱い経路。
7. 死んだ二重実装: `run-skill.mjs`(args 非転送) は旧版、本番は `index.mjs:1045/1115`。混乱源。

## C. 診断（理想 / 問題 / 解決）

**理想**: 見知らぬ人の device に wallet 1個で生まれた franklin が、①正しい tool menu(5-8個、詳細 description、args schema、examples) ②構造化された前回結果 を毎 wake 受け取り、店の開設→登録→商品改廃→検証まで自分の tool で回し、外部 tx だけを稼ぎと数える(INV-EXT)。Claude subscription 勢(claude-p 型)は同じ skill 資産を Claude Code の native 経路(skill+MCP tool)で使う。誰も置き去りにしない。

**問題(優先順)**:
- P1: prompt/registry 乖離 — 存在しない slot を最優先指示（バグ、毎 wake 汚染）
- P2: 店 lifecycle が tool に無い — 自営不可能（俺が代行していた = INV-EXT-4 違反）
- P3: description 1行 + args schema 無し — best practice の最重要項目が最弱
- P4: 結果が生ログ — モデルが EV 比較できない
- P5: claude-p の tool-calling がテキスト模倣 — subscription 勢の経路が二級市民

**解決(実装順)**:
- S1(TOOL-1): prompt/registry 乖離の修正。prompt の doctrine 記述を registry の live slot から生成 or 乖離検知で CI fail。安い・即効。
- S2(TOOL-2): tool 定義を SKILL.md frontmatter から生成(name/詳細 description/args schema/input_examples)。単一 run_skill enum を廃し per-skill tool 化、catalog-gate で menu ≤8 を維持。子スクリプトは stdout JSON のみ(既存規約)を徹底し、ledger 結果を構造化して次 wake へ。
- S3(SELF-STORE-1): store_ensure / store_review / store_update の3統合 tool を S2 の形式で追加。
- S4(PROD-2): 売れる商品(転売 margin/real-time データ)を store_update の候補として渡す。
- S5(CLAUDE-P-TOOLS): claude-p 経路を native 化 — `claude -p` テキスト模倣をやめ、skill を Claude Code skill + MCP tool として提供(subscription 勢の正式 onboarding 経路を兼ねる)。

## D. 出典
- anthropic.com/engineering/writing-tools-for-agents (2025-09-11)
- anthropic.com/engineering/building-effective-agents
- platform.claude.com tool-use docs (implement-tool-use)
- tianpan.co/blog/2026-04-09-tool-selection-problem-agent-tool-routing-at-scale
- 実コード: ~/anicca/runtime/loop/{prompt,brain,index,always-act-router,self-eval}.mjs、skills/earn/run.sh(file:line は本文中)
