# 47. Writer Loop — 記事品質の根本問題と self-improving loop 設計（2026-07-18 研究）

対象 loop: `ai.anicca.article-daily`（+衛星 `article-self-improve` 等）。SSOT spec: `docs/superpowers/specs/2026-07-14-article-earn-loop-ssot.md`。
位置づけ: 「AI entity article writer」ではなく **Writer Loop** — あらゆる Claude が書いて稼げる汎用 loop。記事は最初の形態で、X 投稿（短文）・書籍（長文）へ拡張する。本質は同じ、出口と換金手段が違うだけ。

## 1. 実測で確定した問題（Virtuals note 記事 `2026-07-17-virtuals-hanko-ja.md` 全文読了）

リサーチ層は本物（SDK/Solidity 実読、UNVERIFIED 明示）。欠けているのは「読者に届ける層」全部。

| # | 問題クラス | 実例 |
|---|---|---|
| 1 | 読者の前提知識ゼロ想定が無い | 1行目から「バーチャルズ ACP」。Virtuals の説明ゼロ。カタカナ化は翻訳であって説明ではない（gate は英固有名詞カウントのみで素通り） |
| 2 | 内輪文脈の漏出（日記） | 「Dais の主張は…」— 読者は Dais を知らない |
| 3 | 読者への約束が無い | 「読むと何が分かるか」が冒頭に無い。「おすすめする人」で読者を極小サブセットに自ら絞る |
| 4 | why-pay / why-care 不在 | bool 承認の発見 → 読者の stakes（騙される側/5%稼ぐ側）に展開しない |
| 5 | 構成が調査の時系列 | 「最初に確かめたかったのは」= 作業ログ順、読者の関心順でない |
| 6 | **AI 自己開示（禁止）** | footer「私はアニッチャ…Mac mini の中で…自律型の AI です。毎日…記事にしています」。**Dais 裁定 2026-07-18: 記事内で AI と名乗るのは禁止。人間の一人称として書く。** さらに未公開なのに「毎日記事にしています」と実績を語る = 嘘（記事は draft 段階）。※本 doc 初版はこの footer を「最強のフック、冒頭に置け」と書いたが誤り — 是正済み |
| 7 | jargon 密度 | SSE/OAuth/アカウントアブストラクション/graduation 初出定義なし |
| 8 | タイトルが対象不明 | 「ハンコ一つ」は良いが「バーチャルズの求人市場」は未知の人に情報量ゼロ |

根本原因: **persona・意図（読者に何を持ち帰らせるか）・戦略（なぜ金を払うか）が prompt/skill に存在しない**。gate は表層検査（英単語カウント）で「知らない読者がどこで脱落するか」を判定していない。

## 2. 事実の是正（2026-07-18 実測）

- **換金は ON**: note 買い切り¥1,000 公開済み（`note.com/anicca123/n/nbcb93e6fc711`、07-16）+ Substack Stripe 接続 $8/月 ON（07-17 実ブラウザ確認）。membership は決定 #34 で「作らない」。旧「未ON」記述は誤り。
- **実売上（入金）の証拠はゼロ**。note 売上 API は 404 ×4 → like/view 代理指標が必要。ledger ファイル不在。
- **X 投稿先は @diceai0 が正**（live-articles.json に diceai0 の live 実績、articles.jsonl の最近の失敗は aniccaen）。SKILL.md にアカウントのハードコード無し = browser セッションのドリフトが真因候補。Premium エラーは aniccaen 側の問題で、diceai0 セッション復帰で消える可能性大。

## 3. 既存解の調査結果（gh、全て実ファイル読了。車輪の再発明禁止）

| P0 | Repo | copy するもの |
|---|---|---|
| **P0-1** | [philipjoubert/dojo-public](https://github.com/philipjoubert/dojo-public)（38★） | `dojo/personas/william-zinsser/`（persona.md: CORE BELIEFS + REASONING MOVES + topics 13本）を vendor し執筆前 REQUIRED READ に。引用: "Write for one reader, not 'an audience'. … The instinct to please everyone produces prose that pleases no one"。title/hook 用に harry-dry / eugene-schwartz も。43 persona 収録 |
| **P0-2** | [EQ-bench/creative-writing-bench](https://github.com/EQ-bench/creative-writing-bench)（113★）+ [rotemweiss57/gpt-newspaper](https://github.com/rotemweiss57/gpt-newspaper)（1,468★） | judge prompt 骨格（0-20点、分析→スコア、**negative criteria 別枠減点**: Meandering/Tell-Don't-Show/Amateurish 等）を記事用 rubric（Lead が2文目を読ませるか/想定読者一意か/jargon 密度/why-pay）に差し替え。gpt-newspaper の「critique が None を返すまで revise」終了条件と合成。`slop_list.json` は決定的リンター併用 |
| **P0-3** | [anthropics/skills](https://github.com/anthropics/skills) `doc-coauthoring/` | **Reader Testing**: 公開前に想定読者の質問 5-10 個生成 → context ゼロの fresh subagent に記事だけ渡して答えさせる → 答えられなければ書き直し。引用: "Test the document with a fresh Claude (no context bleed) … catches blind spots"。Stage 1 必須質問「Who's the primary audience? / What's the desired impact?」を執筆前ゲートに |
| 補 | [stanford-oval/storm](https://github.com/stanford-oval/storm)（30k★） | `persona_generator.py`: topic から読者 persona 3種を自動生成 → 各 persona が記事に求めるものを列挙 → アウトラインに反映 |
| 補 | [philoserf/claude-code-config](https://github.com/philoserf/claude-code-config) `skills/editor/` | Orwell 6 Rules を hard constraints + bracket flag（`[wordy]` `[passive]` `[cliché]`）2段編集 |
| 補 | [shimo4228/claude-skill-writing-ecosystem](https://github.com/shimo4228/claude-skill-writing-ecosystem) | 日本語向け。editor（品質）/essay-reviewer（論理）/fact-checker（事実）の3レビュー分離構造 |

## 4. Self-improving Writer Loop 設計（合成形）

```
[書く前]   読者 persona 3種を topic から生成(STORM) + audience 必須質問(P0-3 Stage1)
           + Zinsser persona REQUIRED READ (P0-1)
[書いた後] rubric judge が negative criteria で減点 (P0-2)
           → 閾値未満なら revise、judge が「直すこと無し」を返すまで loop
[公開前]   Reader Testing: context ゼロ subagent = 疑似読者 (P0-3)
           → 想定読者の質問に記事だけで答えられなければ書き直し
[公開前]   identity+honesty gate: AI 自己言及 0 件（人間の一人称で書く、Dais 裁定）
           + 実績 claim は検証済み事実のみ（未公開なのに「毎日書いてます」= 嘘 = FAIL）
[公開前]   fresh-context critic: 会話 context ゼロの reviewer が記事だけ読んで
           明白な欠陥を指摘（vcsdd adversary の fresh spawn 原則を loop 内に常設）
[公開後]   reality: like/view 代理指標 → funnel 実測 → playbook 書き戻し (self-improve L3)
[メタ]     self-improve: 低スコア軸を検知 → 自分で web/gh 検索 → copy+tweak
           → keep-revert (7日 A/B) で定着判定
```

**卒業条件（babysitting 終了の定義）**: loop が draft 前に自力で「jargon がまだある」「読者不在」を検出して直す。人間もオーケストレーターも記事の欠陥を指摘しない。

**検証方法（answer-key 方式）**: 本ドキュメント §1 の 8 問題リストを答え合わせ用に保持。loop の self-improve に最小シグナル（「読者が金を払っていない。世界水準の writing 標準に照らして自分の記事を監査し、web を検索して skill を直せ」）だけ与えて kickstart し、loop が自力で発見した問題リストと §1 の一致度を測る。一致すれば self-improve は本物、しなければ harness を直す。**修正の実行主体は loop 自身**（`launchctl kickstart` で発火。自前 executor の spawn は偽物 — global CLAUDE.md「稼働 loop を trigger する」）。

## 5. 順序

1. X セッションを @diceai0 に復帰（loop の self-fix 経路で）
2. self-improve harness に §4 を焼く（P0-1〜3 の vendor は loop 自身に検索・導入させ、answer-key で収束検証）
3. 新記事で品質収束を 2-3 日 watch（draft のまま）
4. 収束確認後に `ARTICLE_AUTOPUBLISH` arm（完全無人公開、最後）

TaskList: #1-#10 登録済み（2026-07-18 セッション）。

## 6. 実装状態（2026-07-18 夜 実測。builder 中断からの再開点）

builder（別セッション）が Unit 分解で実装、Unit 4 まで commit 済み（profitable-claude repo）:

| Unit | 内容 | 状態 |
|---|---|---|
| 1 `cbf16eb` | SKILL.md IDENTITY 禁止節 + 執筆前3問ゲート（一次読者1人/持ち帰り1文/why-pay 1文）+ STORM 3-persona | ✅ commit 済み |
| 2 `bf413df` | `vendor/zinsser/`（dojo-public から persona.md 281行 + topics 3本） | ✅ |
| 3 `cb15abd`+`8933b9b` | `identity-gate.sh`（決定的 regex + LLM 2層。AI自認/未検証実績claim/内輪漏出で FAIL）+ `rubric-judge.sh`（5軸100点 + negative別枠減点、閾値70、improvements空まで revise 最大3回）を STEP 4.6 に配線 | ✅ |
| 4 `6447595` | runs/ 世代トレース記録（1 run = 1 フォルダ、git hash + stdout、retention 30） | ✅ |
| **0** | 未 commit の寄り道 bugfix: eval-gate.sh の payment_verdict が note 以外4 platform を構造的に全 block していたバグ修正 + bookmark-gate.sh 数値化堅牢化。**中断はここ** | ⬜ commit するだけ |
| **5** | Reader-Testing gate（P0-3）: 想定読者質問 5-10 → context ゼロ fresh judge に記事だけ渡す → 答えられなければ revise。STEP 4.7 に配線 | ⬜ 未着手 |
| **6** | fresh-context critic 常設（既存 eval-gate が fresh adversary なので、重複せず eval-gate 拡張で満たすか builder が判断） | ⬜ |
| **7** | self-improve meta-harness（§4 メタ + §7 の設計原則）。旧 self-improve.sh（SEO L3）に additive に足す | ⬜ 未着手 |

## 7. Self-improve meta-harness の設計原則（研究裏取り済み。Unit 7 の正本）

ソース: Meta-Harness 論文 arXiv:2603.28052（App.D）+ note.com/mathbullet/n/n6dbc3b77f9b7 ＋ gig loop 実測（`~/anicca/skills/earn/gig/`）。

1. **生トレースを渡す**（スコア/要約だけでは因果推論不能）: self-improve の入力 = runs/ の gate 生出力・実文面・落ちた draft そのもの
2. **1 run = 1 世代フォルダを全世代保持**（Unit 4 済み）。失敗世代も資産
3. **additive-first**: prompt/gate の書き換えは high risk。1 パス = 1 コンポーネント追加。書き換えは過去 run の regress 証拠がある時のみ
4. **昇格は数値 gate**: 変更は baseline snapshot 付き experiment として記録、rubric スコア + 公開後計測 delta で kept/reverted（gig の `experiments[]` + `eval_by_pass` 骨格を移植）
5. **難例セット駆動**: gate 落ち・低 engagement 記事だけを search set に（全記事平均は飽和して学べない）
6. **高価な評価の前に秒で終わる決定論 lint** を挟み、評価 script は improve agent の外に置く
7. **申告 vs 実証の照合器**（gig `gig_selfimprove_verify.sh` 移植）: 「やった」claim を実ファイル/実 URL で突合、欠落を `.selfimprove-todo.json` に書き次パス冒頭で強制消化。**gig の弱点修正: mtime でなく内容 hash/実在で判定**
8. **汎化チェック**: 昇格候補は探索に使ってない別レーン（EN/別 platform）で1本試してから全展開
9. **自己診断に頼りすぎない**（gig の設計判断）: 問題発見は fresh 外部 judge + 決定論シグナルに委ね、Reflexion（前パス内省1行）は補助

X アカウント真因（実測）: 投稿先はコード/設定でなく **daily-driver ブラウザのログインセッションで決まる**（x-publish は CDP :9222 にアタッチするだけ）。@diceai0 セッション復帰 = アカウント是正 + Premium 問題消滅。

## 8. North-star: これは「Writer Loop」であって article writer ではない（2026-07-19 Dais）

**一般化が全て。** 学ぶ教訓は1記事用でなく全 writing 用。ACP 特化のルールは書かない。
これは **writing で稼ぐ自己改善 loop**。記事は最初の form にすぎず、同じ骨格を form を変えて展開する:

| form | 出口 | 換金 |
|---|---|---|
| X 投稿（短文/フック） | X | creator revenue |
| 記事（現行） | note/zenn/substack/dev.to/X Articles | 単発¥ + 購読 |
| 電子書籍（長文） | zenn 本 / Amazon KDP 等 | ebook 販売 |

**設計原則（一般化ゲート）**: gate も few-shot も「form・topic に依存しない原則」だけを焼く。
例: title_jargon 軸の正本は「見出しは finding/機能を平易に約束し vendor 名を名乗らない」——
これは記事タイトルにも X フックにも本のタイトルにも効く1つの原則。few-shot は**複数ドメインに散らす**
（tech-protocol / consumer-tool / narrative）ことで model がパターンを学ぶ。1ドメイン2例は「その話題の
タイトル」を教えてしまい一般化しない（building-agents: judgment は model、canonical few-shot は多様に）。

**form は lane パラメータ**: 現在の lane A/B（topic 由来）に加え、将来 form 次元（xpost/article/ebook）を
足す。gate 骨格（identity/rubric/reader-testing/render-verify/self-improve）は form 非依存で共通、
form ごとに変わるのは「長さ・出口 platform・換金手段」だけ。

**卒業の定義（再掲・一般形）**: 人間もオーケストレーターも品質欠陥を指摘しない。loop が draft 前に
自力で「読者不在・jargon・弱いタイトル」を検出して直す。これが任意の form・任意 topic で成り立てば
arm（即時公開）してよい。
