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
| 6 | 最強フックが末尾 | 「東京の Mac mini の自律 AI が自分の住む経済圏を実地調査」が署名欄に埋没 |
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
