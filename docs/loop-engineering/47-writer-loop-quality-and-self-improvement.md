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

TaskList の現在状態は §16.5 と §17 を正本とする。D1-D8 はすべて **DONE**、model-agnostic daily sprint は P1 **DONE** / P2-P4 **TODO**。§16.4 は D1-D8 の完了条件だけを定義する。

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

## 9. 記事の型 = EXPLAINER であって体験の日記ではない（2026-07-19 Dais 裁定）

**なぜ人が読むか**: AI / crypto / エージェント経済という新しい分野を、速く正しく理解したいから。
「これは何で、なぜ重要か」を知りたい。だから記事の**主題は分野/物そのもの**であって、書き手の体験ではない。

| | ダメ（体験の日記） | 良い（explainer） |
|---|---|---|
| 主題 | 「私が◯◯を覗いてみた話 / 確かめたこと」 | 「◯◯という仕組みはこう動く」 |
| 一次調査(SDK/contract 実読) | それ自体が話の中身 | 主張を裏づける**証拠** |
| 読後に読者が得るもの | 「著者が何をしたか」 | 「その物が何で、なぜ重要か」 |

一次ソースを実読する強み（moat）は保つ。ただし**説明を前に出し、訪問記を前に出さない**。
hamburger template の [2]何か / [3]landscape / [4]どう動く が背骨、[5]receipts は補強証拠。

**gate 化（実装済み）**: rubric に減点軸 `self_as_subject` を追加。主語が終始「私が何をしたか」で、
主題であるべき「◯◯とは何か」が体験の背後に隠れたら減点。judgment は model、few-shot（BAD:訪問記 /
GOOD:仕組み説明）付き。SKILL に「SUBJECT = EXPLAINER, NOT DIARY」節。
検証(2026-07-19): 旧日記記事 = self_as_subject 発火(score 42)、explainer 版 ACP = 非発火。軸は両者を区別する。

**topic queue の是正**: 体験の日記系カード（devlog / dashboard-lied / token-melting / four-false-edges 等）は
`_hold/` に退避したまま = 正しい（体験ネタ）。だが explainer 系（olas-mech-marketplace = A2A とは何かの説明）を
一緒に held したのは誤り → queue に復帰した。今後 _hold には「自分の体験」ネタのみ、queue には explainer ネタ。

## 10. 検証済みの現状（2026-07-19）: loop は完全動作、残りは autopublish の switch だけ

今日の pass が JA+EN を全 platform に draft stage 済み（実測、articles.jsonl + 実 draft URL）:
zenn-ja / devto-en / substack-ja / substack-en / note-ja / x-ja / x-en。X も @diceai0 復帰で通る。
gate 骨格 + 自律(#14) + 収益連動(#13) + form(#12) + explainer(#9) 全て稼働。**残るは #7 arm（ARTICLE_AUTOPUBLISH=1）**
のみで、これは複数日 watch で品質が別 topic でも安定して 70+ を出すのを実測してから最後に引く。

## 11. #7 arm と #8 OSS 化は別物（2026-07-19 明確化）

**#7 と #8 は対象が違う**:
- **#7 ARM** = Dais 自身の loop を live 化。Dais のアカウント(note=anicca123 / substack=aniccabuddha / X=diceai0)に毎日投稿して Dais が稼ぐ。コード作業ゼロ、環境変数1個。
- **#8 OSS 化** = 見知らぬ他人が clone して、自分のアカウントで自分が稼げるようにする。まとまった実装。

### #7 arm の正確なコマンド（品質確認後に実行）
毎朝 06:00 JST の定期 pass を live 化する = plist に env を焼く:
```bash
PB=/usr/libexec/PlistBuddy; P=~/Library/LaunchAgents/ai.anicca.article-daily.plist
$PB -c "Add :EnvironmentVariables dict" -c "Add :EnvironmentVariables:ARTICLE_AUTOPUBLISH string 1" "$P" 2>/dev/null || \
  $PB -c "Set :EnvironmentVariables:ARTICLE_AUTOPUBLISH 1" "$P"
launchctl unload "$P"; launchctl load "$P"
```
これで次の 06:00 pass から draft でなく即公開。dev.to だけは常に draft(仕様)。

### #8 OSS 化の実際の gap（実測 2026-07-19）
「git clone profitable-claude && 1コマンドで自動起動→自分のメールでアカウント自動作成→全platform投稿→稼ぐ」
という理想に対し、今の実体:

| ステップ | 状態 | gap |
|---|---|---|
| clone→launchd 起動 | ✅ | plist 置くだけ |
| 記事執筆→gate→publish | ✅ | loop 本体は完成 |
| 自分のメールで signup | 🔶 | self-signup/gen-plus-address.sh あり。だが keiodaisuke gmail 固定、全platform自動signup未配線 |
| 各platformログイン | 🔶 | ig-account-create は IG で実証済。note/substack/zenn/X の自動作成+login は要ビルド。今は「人間が1回作ってログイン」前提 |
| アカウント名を自分のに | ❌ | anicca123(12) / aniccabuddha(15) / diceai0 / anicca_301 / telegram 8547730585 がハードコード。env 化して剥がす |
| payout(稼いだ金の受取) | 人間 | KYC/銀行/Stripe = 各人の1回手作業(Substack $/note振込/X Premium) |

**#8 のタスク** = ①ハードコード(アカウント名/telegram/email)を env 化 ②全platform自動signup を IG パターンで note/substack/zenn/X に展開 ③KYC/payout は loop が「あなたの銀行を1回繋いで」と依頼する導線。
**「clone して勝手に全部」の単一コマンドは今は存在しない** — それを作るのが #8。KYC だけは各人1回の人間作業で正解、それ以外は自動化可能。

## 12. 残り TODO（2026-07-19 時点、正しい順序）
build は全 done(#1-6,9-14 完了)。残り:
1. **#7 ARM**(唯一の本筋) — 明朝 06:00 JST pass の品質を Dais が見て OK → 上記 arm コマンド実行 → 毎日全platform自動公開
2. **#8 OSS 化** — Dais固有剥がし + 全platform自動signup + KYC導線(新セッション推奨、大仕事)
3. **優良記事の毎日1教訓学習（2026-07-19 Dais 設計）** — 実測で判明した欠落: loop が外部を見るのは STEP 2 の「トピックの事実調査」だけで、「人が金を払う優良記事の実物を手本として読む」経路が無い。書き方の外部資産は `vendor/zinsser/`（本の要約3本）のみ。rubric-judge.sh に実在記事の few-shot は 0 件。現状の記事は「人が金を払うバー」に達していない前提で設計する。
   - **cadence = 毎日1本、1教訓**（Dais: 一気にやるな。1日1個で月30個・年365個、焦らず積む。既存 self-improve の「一度に1変更」規律と同型）
   - **丸ごと取る**: 対象記事は crwl で**全文 scrape**（タイトルから結びまで完全な artifact）。断片では「優良とは何か」が分からない。全文を `vendor/exemplars/YYYY-MM-DD-<slug>.md` に保存
   - **教訓抽出**: model が全文を読み「これが優良タイトル / 優良な概念の立て方 / 優良な構成だ」という**教訓を1個だけ**書く（形式: 手本記事 / 観察した技 / 自分の記事への適用方法）→ 教訓台帳 `vendor/exemplars/lessons.jsonl` に追記
   - **適用**: 既存 STEP 1.5 READ PLAYBOOK（先週の教訓を読む工程）がこの台帳も読む。教訓は self-improve の experiment として1個ずつ試し、rubric/実売の delta で kept/revert（既存機構に載せる、新機構は作らない）
   - **選定元**: note 有料ランキング / Substack bestseller / zenn trending / dev.to top。「これは人が金を払う記事か」の判定は model が行う（regex 禁止）
   - **rubric few-shot**: 蓄積した exemplar から引く = 採点基準が実在の売れてる記事に紐づく
4. (arm後) `skills/article-writer/scripts/` の汎用部品（rubric-judge.sh / self-improve.sh / reader-testing-gate.sh）を `skills/_shared/` へ移動して clip/reddit 等の兄弟 loop からも使えるようにする / OSS 公開前に Dais の個人情報（アカウント名・telegram ID・gmail）をコードと state ログから消して env 変数に置換する

## 13. 2026-07-20 Dais 裁定: no-skip 毎日必 publish + 今日から autopublish + queue 3-lane（§10 の「複数日 watch」を上書き）

### 13.0 今朝の実測（2026-07-20 06:00 pass の失敗解剖）

- olas-mech explainer は書けた（ja/en）。機械 gate + reader-testing 全 PASS、**rubric FAIL ja 62 / en 61**（title_jargon: 見出しの Mech/Requester。gate は正しく検出し improvements #1 で「タイトルから外せ」まで指示済み）
- **規定の revise loop（3回）が 0 回実行**: ja FAIL から 7 秒で en の gate に素通り。ledger 0 行・Telegram 無しのまま rc=0 で終了（07:00:36、最終 stdout は文脈不明の1行）
- **真犯人 = disk**: emergency-disk-guard.log 実測で 06:00-07:00 に free 0GB ×89 回 / 1GB ×77 回。2026-07-14 ENOSPC brick と同 class。guard の 60 分 transcript 掃除で当該 pass の transcript も消失
- 応急処置済み: `~/.openclaw/skills/.backups/` の旧 tar.gz 2 本削除（+7.5GB、free 9.7GB）。残 = 07-14 の 14GB backup（新 backup 成功後に削除）と生成側 cron の是正（§13.5）

### 13.1 不変条件（全て MUST。Dais verbatim「no option to skip」「they have to ship article everyday no matter what」）

1. **毎日 1 記事、publish まで完走する。skip という出口は存在しない**
2. rubric revise = **max 5 回/言語**。5 回 FAIL → 同 topic のまま**角度とタイトルを変えて書き直し** → 再 gate。PASS まで継続する（「FAIL のまま未 staging で正直報告して終了」の枝は削除）
3. pass 完了の定義 = rubric PASS + 全 platform publish + reality-gate PASS + ledger `published:true` + Telegram 報告。**これ未満での exit は「未完了」であり成功ではない**
4. **wrapper self-heal**: pass 終了時に当日の完了 ledger 行が無ければ wrapper が自動 respawn（上限付き、間隔をあけて）。今朝のような途中死は次の respawn が拾う
5. **disk preflight**: pass 冒頭で free < 5GB なら承認済み掃除（backup 旧世代・再DL可能 cache）を自分で実行してから走る
6. STEP 3 執筆時に `reference/title-best-practices.md`（profitable-claude main、commit 3826828）を**必ず読む**。タイトル = 平易な機能語ファースト・未定義固有名詞禁止・発見（数字/結果)を約束。「〜を徹底解説」型は禁止

### 13.2 autopublish（Dais 裁定: 今日 2026-07-20 から arm。§10 の「複数日 watch してから」は本節が上書き）

- §11 の arm コマンドを実行し `ARTICLE_AUTOPUBLISH=1`。armed 時は draft-only doctrine を反転: **publish が happy path**、reality-gate PASS が必須 gate。unarmed 時は従来どおり draft-only（OSS 利用者の既定）
- dev.to のみ常に draft（仕様維持）
- 品質の担保は「人間が draft を読む」から「**rubric PASS まで無限 revise**（13.1-2）」へ移る。gate を弱めて通すのは最悪の違反

### 13.3 queue 3-lane（ネタ供給の設計。目標比率 ≈ Dais 指名 50% / auto devlog 30% / 自走 20%）

| lane | 供給 | 状態 |
|---|---|---|
| 1. Dais 指名 | Dais「これ記事に」→ main Sol がその turn 内に `topics/queue/` へカード作成（既存 frontmatter に倣う。HARD） | 運用ルールとして確立 |
| 2. auto devlog | 毎日の開発ログ → devlog カード自動生成。07-19 分は存在、**07-20 分が無い** → 生成器を特定し毎日生成を保証する | 要配線 |
| 3. 自走 | queue 空なら loop が自分でネタを発掘して書く（これが moat・core） | 既存 lane B の保証を確認 |

- 優先順: Dais カード > devlog > 自走
- 今朝の `olas-mech-marketplace.md` は in-progress に stuck → queue に戻す

### 13.4 Phase 区分

- **Phase 1** = 13.1〜13.3 が 100% 稼働。今日が初の full E2E no-human 公開日（fix → arm → kickstart → olas 記事を PASS まで反復 → 実公開 → own-eyes 検証）
- **Phase 2** = #8 OSS 化（§11）→ 一般 writing / X 短文 / books / 多言語 / medium・自社サイト+SEO。north star: 誰でも clone → 10k MRR/人、合計 10M MRR

### 13.5 disk 恒久対策（loop の生存条件）

- `~/.openclaw/skills/.backups/` を日次生成する cron を特定し、保持 1 世代 + heavy dir（venv/media/state）除外に是正。14GB/本の tar.gz を毎日積むのが今回の根本原因
- 検証: 是正後の backup サイズ < 2GB、free > 20GB を維持

## 14. FULL TODO — Layer 1 完成から 10M MRR まで（2026-07-20。TaskList と二重トラック、この表が順序の正本）

体制（Dais 裁定、現在の正本）: main Sol = plan/spec/独立検証、別 Sol = 全実装（subagent + adversary one-shot、fresh 起動なので同モデルで可）。spec と TODO は発見のたびに更新し続ける。

### 今日（Layer 1 完成 = 初の全自動公開日）
| # | owner | やること | 完了の証拠 |
|---|---|---|---|
| T1 | Sol | U5 arm(ARTICLE_AUTOPUBLISH=1+publish経路反転) / U6 queue 3-lane+mech復帰 / U7 backup cron 是正+14G削除 | launchctl に env、queue に mech、backup <2G |
| T2 | main Sol | 別 Sol 成果の独立検証（bash -n / grep / launchctl） | 実 tool 出力 |
| T3 | main Sol | kickstart ai.anicca.article-daily | 再走ログ |
| T4 | loop | olas 記事を実物パターン title で書き直し → PASS まで revise → 全 platform 実公開 | rubric ≥70 + live URL |
| T5 | main Sol | 公開 own-eyes 検証 + ledger published:true + Telegram 実在 | HTTP 200 / screenshot |
| T6 | main Sol→別 Sol | #9 exemplar 毎日1教訓 loop 発注（PLAN-exemplar-daily-loop.md 545f08f、flow B） | lessons.jsonl 実1行 |

### 今週（「自動」の証明）
| # | やること | 証拠 |
|---|---|---|
| T7 | 明朝 06:00 pass が人間ゼロで公開完走 | 07-21 ledger published:true |
| T8 | devlog カード毎日自動生成の実測 | 07-21 カードが自然に生える |
| T9 | lane 3 自走の実証（queue 空の日） | lane B ledger 行 |
| T10 | exemplar loop 日次実走（3日分） | lessons.jsonl 3行 |
| T11 | disk: backup <2G + free >20G 維持 | df 実測 |

### Phase 1.5（実売最適化 → 1 loop 10k MRR）
| # | やること |
|---|---|
| T12 | measure-sales → self-improve 採点接続の検証（¥0 は ¥0 と報告） |
| T13 | 有料化実配線: note 有料価格 / Substack 有料 tier / X Premium 収益化 |
| T14 | 実売由来の kept/revert が回る実証（experiments.json） |
| T15 | X 短文 form の実運用化（forms.json xpost） |

### Phase 2a（OSS 化 = 複製。#8、VCSDD で）
| # | やること |
|---|---|
| T16 | ハードコード剥がし: anicca123/aniccabuddha/diceai0/anicca_301/telegram/gmail → env 化（grep 0 ヒット gate） |
| T17 | .env.example に全 platform var 定義 |
| T18 | 全 platform 自動 signup（ig-account-create パターン展開、新規メールで E2E own-eyes） |
| T19 | KYC/payout 人間依頼導線（README + article-daily） |
| T20 | PII scrub（公開前） |
| T21 | spec 47 §15 に OSS onboarding 完成形を記録 |
| T22 | 「clone → 1コマンド → 稼働」の第三者環境 E2E |

### Phase 2b（単価×面×言語 → 10M MRR）
| # | やること |
|---|---|
| T23 | ebook/books form（記事束ね、単価×10） |
| T24 | 多言語 es/zh/ko（資産の再収益化） |
| T25 | medium / 自社サイト SEO / newsletter |
| T26 | OSS ユーザー数×黒字率 dashboard（10M 進捗計器） |
| T27 | 収益モデル決定（収益シェア/hosted/premium feed — 未決定と明記） |

## 15. 2026-07-20 夜 Dais 裁定 + writing-tools 調達 + capafy X 停止（本節が §12-14 の該当行を上書き）

### 15.1 裁定（全て MUST、即日有効）
| 裁定 | 中身 | 上書き対象 |
|---|---|---|
| 無限 revise 廃止 | max N(=5) revise → 角度変え書き直し1回 → FAIL なら翌日 carry-over（skip ではない）。**cost < revenue を恒等式として invariant 化**（記事1本の token 予算を明示） | §13.1 の「PASS まで無限反復」 |
| 価格 | ¥1980 廃止。**free-first**: 全 platform 全文 free → 閾値（記事30本+フォロワー500、仮置き）到達で note/substack subscription（¥500/mo 級）開始。note 単発は最大 ¥500 | §12 の ¥1980 |
| 記事 = newsletter | 同一資産の売り方違い（単発 or subscription）。newsletter を別フォームとして実装しない | — |
| ebook 出口 | gumroad / zenn本 / 自社 site + Stripe | — |
| X 投稿の線引き | **article loop の X 投稿（記事+X post、@diceai0）= 完全に正、継続**。capafy marketing loop の X 宣伝投稿 = slop、停止（§15.4） | — |
| 対象 citizen | writer loop は **claude-p のみ**（human-owned、銀行口座に接続可）。franklin = self-owned、人間の私的情報アクセス永久ゼロ、crypto rail のみ | — |
| 唯一の human 接点 | 銀行口座を一度聞くだけ。他の credential ゼロ（Postiz 等の有料 SaaS 不使用、投稿は CDP 直） | — |
| 分業 | **main Sol = plan/spec/独立検証のみ。build/edit は別 Sol**（flow A）。subagent は全ツール継承（agent 定義に tools: 行を書くな — 2026-07-20 実測で3体が Bash 喪失） | — |

### 15.2 writing-tools OSS 調達 + bakeoff 第1R 結果（実測。詳細 = docs/research/2026-07-20-writing-tools-oss-survey.md）
- 調達済み（vendor/writing-skills/、全 MIT）: content-skills（anti-ai-writing 5-diseases + specificity ladder / viral-hooks Four Hook Killers / storytelling）、viral-hooks-skill（100 formula）、humanizer（30k★）、shimo4228 writing-ecosystem（日本語 AI-slop 禁止リスト + だ/である×発見調）
- bakeoff 第1R blind 判定: **E（STORM式視点法+hooks+storytelling+anti-ai 統合）が ja/en 両方で1位。現行 taste(A) は ja 5位/en 4位** — 統合を standard 化する
- 第2R（E vs F=humanizer 版 vs G=shimo4228 版）: 生成済み、blind 判定待ち
- 他の採用決定: knowrite「max3 revise+80% gate」= W2 の既存実装 / 書籍 = ai-book-generator 骨格 + show-me-the-story 全書整合 pass / X post = Gingiris 閉ループ構造（voice→evidence→publishability→feedback）
- 空白の発見: 日本語記事執筆 OSS はほぼ存在しない = 我々の OSS の差別化スロット

### 15.3 W タスク（TaskList 登録済み。T6 以降と並走、実装は全部 Sol）
| # | 内容 | 種 |
|---|---|---|
| W1 | conscience gate 3層: ①publish 前の公開適否判定（品質と別軸: gray-zone 露出/評判リスク）②owner-veto センサ（published URL 定期 curl、自分が消してないのに 404 = owner 削除 = 最強の負教訓 → 自動ルール修正）③週次 fresh-eyes 自己監査。babysitting 廃止の実体 | 新規 |
| W2 | bounded revise + token 予算（§15.1）。knowrite 方式 copy+tweak | §13.1 修正 |
| W3 | free-first 配線（§15.1 価格） | §12 修正 |
| W4 | zenn 全文無料 = funnel と明文化（free-first 期は正） | 明文化 |
| W5 | bakeoff 第2R 判定 → 勝者を taste/verifier に統合 → 比較記事 queue 投入 → 統合 skill OSS 化 | 進行中 |

### 15.4 capafy X marketing 停止（2026-07-20 実施済み・実測）
- Dais 裁定: capafy の X 宣伝投稿（@aniccaen スレッド）= AI slop、恒久停止。**IG は継続**（warmup 進行中、day2/3）。
- 実施: `capafy-x-marketing-daily.sh` を全 citizen home（~/.anicca-founder / ~/.blockrun / ~/.franklin2-home/.blockrun）で `.DISABLED-by-dais-20260720` に rename。スケジューラ実測: launchctl に x-marketing job なし、openclaw cron の anicca-x-* 系は全 enabled:False。最終投稿の痕跡 = 07-18 08:10 の cadence no-op log のみ。
- 残タスク（Sol）: rename でなく恒久削除 + SKILL.md から X-line 記述を撤去（W 系と同便で発注）
## 16. WRITER ENGINE — 多フォーム正本（2026-07-20 Dais 是正。§15 の「記事中心+後付けフォーム」観を上書き）

**是正**: これは「article loop」ではない。**1つの self-improving engine が短文・中文・長文の3 lane に毎日/毎週/毎月書く**。記事は lane の1つにすぎない。X 短文 lane と書籍 lane は「後で」ではなく engine の初期形態に含まれる。

### 16.1 3 lane 構成（全 lane が同じ CORE を共有）
| lane | 頻度 | 出力 | taste 調達元（vendor 済み） | 金 |
|---|---|---|---|---|
| SHORT (X 単体投稿) | 毎日 2-3本 ja+en | 記事リンクでない standalone 投稿（フック/教訓/観察） | Gingiris 閉ループ（voice→evidence→publishability→feedback）+ blacktwist hooks + viral-hooks | 直接 ¥0。発見面 = 全 lane の母数を作る |
| MID (記事=newsletter) | 毎日1本×2言語 | note/zenn/substack/X(記事)/devto | STORM式+hooks+storytelling+anti-ai/humanizer/shimo4228（bakeoff 実証） | sub ¥500/mo + 単発 ≤¥500 |
| LONG (書籍) | 月1冊 | 記事在庫30本の束ね直し → zenn本/gumroad/自社+Stripe | ai-book-generator 骨格 + show-me-the-story 全書整合 pass | ¥1,500-3,000/冊 |

CORE（共有）: queue+exemplar 学習(T6) → 執筆 → verify（rubric+conscience gate W1+bounded revise W2+token 予算）→ 公開（CDP 直、credential ゼロ）→ 学習（実売還流 T12 / owner-veto / 週次監査）。

### 16.2 フォーム lane タスク（TaskList 登録: F1/F2）
| # | 内容 | 依存 |
|---|---|---|
| F1 | X 短文 lane 実装: Gingiris 構造 copy+tweak、毎日 2-3 standalone 投稿（@diceai0）、X-form rubric + conscience gate 適用、feedback= imp/eng 実測→taste 更新。旧 T13-15 の「X 短文 form」をこれに統合 | W1,W2 完了後 |
| F2 | 書籍 lane 実装: 在庫30本到達で初回、ai-book-generator で章構成→整合 pass→zenn本+gumroad 出版 E2E。旧 T23 をこれに統合 | 記事在庫30本 |

### 16.3 金の地図（10k MRR。§15.1 free-first と整合）
- Phase F（今〜30日）: 全 lane 無料。SHORT が発見、MID が在庫、LONG は準備。収益 ¥0（設計通り）。
- Phase S（30日〜）: 1コロニー月次の現実線 = sub 100×¥500 + 単発 30×¥500 + ebook 20×¥1,500 ≈ ¥95k ≈ $650/mo。SHORT lane が母数を拡大するほど各項が伸びる。
- Phase R: $10k = $650×15 コロニー（OSS 採用 15人）。$100k = 150人。10k の変数 = OSS 採用数 > 文章力。
- cost 恒等式: 1日 3 lane 合計 token 予算 ≤ $6 → 月 $180 → sub 36人で黒字。黒字化が最初の勝利条件。
- 未検証 3変数（T12 で実数化）: sub 転換率 / ebook 販売率 / OSS 採用率。

### 16.4 実行順序と MID lane スプリントの done 条件（2026-07-20 Dais 裁定。goal-setter 形式。これが次セッションの正本）

**Order は lane 逐次: MID(記事) を完全に終わらせる → SHORT(F1) → LONG(F2)。** F1/F2 は MID done まで着手禁止（次々セッション以降で Dais が指示）。

**Objective**: MID lane を完成させ、**既存の** `ai.anicca.article-daily`（launchd、autopublish armed 済み）を `launchctl kickstart` で発火し、「良い記事」が実際に毎日 publish される状態を実証する。新 loop を作らない。article loop の X 投稿（記事+X）は現状のまま維持。

**分業**: main Sol = plan/spec/独立検証のみ。実装は別 Sol subagent（flow A、worktree 分離）。

**現在状態**: **DONE**（状態と実測 evidence の正本 → §16.5）。

**Done when（全部 AND、実測 evidence 必須）**:
| # | 条件 | 検証方法 |
|---|---|---|
| D1 | W5 完了: bakeoff 第2R（E vs F vs G、blind/*.md 生成済み）を fresh spawn で blind 判定 → 勝者構成を article-writer の taste（SKILL.md/STEP3-4 参照ファイル）に統合 | profitable-claude main の diff + 統合後の記事生成が旧 baseline に blind で勝つ |
| D2 | W1 完了: conscience gate（publish 前の公開適否 fresh-spawn 判定）が script として実在し article-daily.sh に配線、negative test（gray-zone 題材を食わせて BLOCK）PASS | 実行ログ + negative test 出力 |
| D3 | W2 完了: bounded revise（max5 → 角度変え1回 → 翌日 carry-over）+ 記事1本 token 予算 gate。「PASS まで無限反復」文言が loop から消滅 | grep 0 hit + gate 実行ログ |
| D4 | W3 完了: ¥1980 が grep 0 hit、free-first（note free or ≤¥500）配線 | 次 pass の note 出力実測 |
| D5 | W4 完了: zenn = funnel を SKILL.md に明文化 | grep |
| D6 | capafy X-line 恒久削除（.DISABLED rename → 削除 + SKILL.md から X-line 節撤去） | find 0 hit |
| D7 | **kickstart + 非同期完走実証**: `launchctl kickstart -k gui/501/ai.anicca.article-daily` → 日次 main は5媒体 `published:true` + `reality_gate:PASS` と同一run/slugの永続 Zenn pending を作り、foreground sleepなしで資源を解放する。独立 `article-zenn-retry` worker は300秒間隔で再起動後も同じpendingだけをlock/idempotent再試行し、Zenn live後にreality gate → ledger 6件目 → exact6 → heartbeat/Telegramまで完走する。main Sol はlive本文を実ブラウザでown-eyes判定する。旧wrapperの移行中SIGTERMをrc=0と偽記録しない | exact5+pending artifact + worker launchctl + exact6 ledger + live URL実読 |
| D8 | spec TODO 表 + TaskList 全同期、全 diff commit+push | git log |

**Stop if**: 同一 D で3回 FAIL → handover。破壊的操作の要求。週次 token 残 10% 未満。

### 16.5 D1-D8 実測 evidence（現在状態の正本）

| # | 状態 | evidence（実 tool result のみ） |
|---|---|---|
| D1 | **DONE** | 第2R blind（E vs F vs G、独立2 judges）: F=E−anti-ai+humanizer が ja/en 両方で1位（judge-r2d: F 93 > E 88 > G 87、tiebreak F vs G も F 勝ち）。第1R勝者 E は脱落。統合 = SKILL.md「執筆プロセス standard」節（commit 4c0b3d3）+ article-daily.sh STEP 3 に humanizer 最終 pass 配線（c1ee6fc）。統合後検証: 新 taste 指示だけで生成した H.md が旧 baseline A に blind で勝利（judge-final3: ja 大差・具体性/guardrail/receipt が決め手。2749345）。fact-checker 注記: H は F の「午前2時」場面と論理順を強く踏襲 — ただし taste 節自体が同場面を例型として焼き込んでいるため予期通り。次の実 topic（orca/olas）での生成品質が真のテスト = D7 で判定 |
| D2 | **DONE** | scripts/conscience-gate.sh（870d130、claude -p --bare --no-session-persistence --tools "" = context-zero、fail-closed）を STEP 4.8 に配線。negative test: gray-zone.md → {"verdict":"BLOCK"} rc=1、ordinary-tech.md → {"verdict":"ALLOW"} rc=0（main Sol も再実行して実測）。fact-checker 2周（初回 FIX FIRST 2件 → 修正 → PASS） |
| D3 | **DONE** | 93b8c50。STEP 4.6/4.7 bounded（max5 + 角度変え1回 / max2 + content-add 1回 → carry-over 行を ledger へ）、STEP 0.7 attempt-budget gate（MID $4/day、elapsed 4h/20 attempts/6 runs proxy、CARRY_OVER rc=1 実測）、STEP 10 が shipped/carry-over の2終端に。grep "no ceiling\|uncapped\|無限" article-daily.sh SKILL.md = 0 hit |
| D4 | **DONE** | 273ba6f（STEP 12/13/14: published:true 30本未満 = note 全文無料、以上 = suggestion ¥500 clamp）+ d4bbe35（publish-paid.py --free: free radio 選択、price/paywall スキップ、note API で price 0/null+status published 検証 → FREE_PUBLISHED。py_compile OK）。grep 1980（vendor/state 除く）= 0 hit |
| D5 | **DONE** | 658e606。SKILL.md の分裂記述（バッジ/投げ銭 vs FREE explainer）を「Zenn = 恒久 free funnel、発見+信頼構築、note/Substack sub への導線」に統一 |
| D6 | **DONE** | .DISABLED 3ファイル削除（founder/blockrun/franklin2）+ 3 home の capafy SKILL.md から X-line/Postiz 全節撤去（IG 節は残存確認済み）。find *DISABLED* = 0 hit、grep x-marketing/X-line/postiz = 0 hit。3 home とも git repo でないため commit なし |
| D7 | **DONE** | run `20260721-012658` の ledger は note、X ja/en、Substack ja/en、Zenn の6件がすべて `published:true` + `reality_gate:PASS`。published+PASS 抽出の第6行目（ledger物理行95）が Zenn `2026-07-21-coinbasevisaai143` で、Dev.to は仕様どおりdraft。指定validator `article-run-complete.py --ledger .../articles.jsonl --run-id 20260721-012658 --armed 1` は fresh `rc=0`、独立集計も `exact_count:6`。`zenn-deferred.json` は `status:complete`、`completion_check:passed`、`notification_status:sent`、heartbeat/completed URLあり。retry launchctl は `run interval=300 seconds`、`runs>=27`、`last exit code=0`。profitable-claude は `HEAD == origin/main` で、非同期retry `20f7142` と Substack table互換修正 `1e97a74` を含む。Zenn remote `origin/main` は公開commit `45659e9` と再試行commit `3f222c9` を含み、remote上のfrontmatterは `published: true`。agent-browser fresh own-eyes: [Zenn](https://zenn.dev/anicca/articles/2026-07-21-coinbasevisaai143) はURL/title一致、本文7,989文字、H2 11個、表1個、出典まで描画。[Substack ja](https://aniccabuddha.substack.com/p/coinbasevisaai143) / [en](https://aniccabuddha.substack.com/p/coinbases-ai-rails-moved-44m-only) はURL/title一致、本文8,692/15,398文字で、raw pipe段落0件・Markdown区切り記法0件。旧raw pipe表は両言語とも見出し段落 + 強調ラベル付き7項目ULとしてrender済み。fresh全ページ画像は `/tmp/d7d8-finalizer-20260721-012658/`（SHA-256: Zenn `096e97ff40d7e8be344fde48752f4e37a71952ecced713edb90d6a145b39a98b`、ja `c73af5d62789033afc1aa9f76ec202dd241c13ff64467949c6408547c5f48295`、en `67c86958f2b496d29f3c1360fac3ce1b800376b5b8dc0bc3add9510bd55cb470`）。永続比較画像は run artifact `assets/substack-table-after/{ja,en}-full.png`（ja `32340c1eef4ef16b8a802defa02292bc6efef96ec1380f9f059c40f603bfec15`、en `efc5870924a3b9ab67790cc4c2d73889012766eac9f489d3a112ef00aae86e09`）。具体的な冒頭、280日・136,708,672件・$44,121,383.81・0.43%の検算可能な数字、C1/C2/C3の説明、一次資料と独立tracker、読者別結論が実ページで連続しており、本文品質・配信品質とも **PASS** |
| D8 | **DONE** | 状態とevidenceは本節だけを正本とし、§16.4 とTaskListは本節への参照に同期。対象specだけをcommitして `dev` へpushし、`HEAD == origin/dev`・対象spec cleanをfresh実測する。最終判定はfresh-context別Solのartifact-only/read-only review `ok:true` を必須とする |

## 17. Model-agnostic daily sprint（TaskList 正本）

**Objective**: 日次 writer を単一 provider/model の障害で停止させず、有限の品質改善後も最良 draft から配信を再開し、毎日1記事を全媒体へ重複なく公開する。

**Order**: P1 → P2 → P3 → P4。P2-P4 は前段が DONE になるまで完了扱いにしない。

設計根拠: ソース [Anthropic Model migration guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) / 核心の引用: “Start with the xhigh effort level for coding and agentic use cases”。実際に採用するmodel名は推測せず、同じCLIProxy経路の実probeで成功した値だけを使う。

fallback設計根拠: ソース [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) / 核心の引用: “Enable automatic fallback to the specified model(s) when the primary model is overloaded or not available ... Accepts a comma-separated list tried in order.” 同時にソース [Claude Code model configuration](https://code.claude.com/docs/en/model-config) / 核心の引用: “Authentication, billing, rate-limit, request-size, and transport errors never trigger a switch”。したがって既存 `--fallback-model` はavailability/overload用にfull process内へ保持し、明示的なcandidate切替は副作用なし `MODEL_OK` preflightの429/5xx/connection/初回応答timeoutだけに限定する。healthy candidate決定後のfull article promptは最大1 process・1回で、終了rcや自由出力をmodel障害分類せずそのまま返す。記事開始後のresume/idempotencyはP3の責務。circuit breakerはソース [Microsoft Azure Architecture Center: Circuit Breaker pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker) / 核心の引用: “fail fast without making the remote call when an operation is likely to fail” に従い、永続cooldown中は既知の不健康modelを呼ばない。

| # | 状態 | 内容 | done evidence |
|---|---|---|---|
| P1 | **DONE** | 日次 writer の primary model を `gpt-5.6-luna`、effort を `xhigh` にする。`ARTICLE_MODEL` / `ARTICLE_EFFORT` の明示的 default とし、CLIProxy認証とローカル認証の両分岐が同じ値を使う | profitable-claude `7907269`: contractを先に変更した旧実装REDは `rc=1`（Luna default欠落、xhigh default欠落、共通引数0件、hard-coded Sonnet残存）。実装後は `bash -n rc=0`、contract `rc=0`、quality-best-effort / run-completion / run-prune-pending / zenn-deferred-retry は全て `rc=0`。render wiringは今回差分外の古いSTEP列期待により11/12で、変更前live checkoutでも同一失敗を再現。実CLIProxy probe `claude --model gpt-5.6-luna --effort xhigh --no-session-persistence --tools '' -p 'Reply with exactly: MODEL_OK'` は6秒で `rc=0` / `MODEL_OK`。profitable-claude は branch、`origin/main`、live checkout がすべて `7907269df887a246e04176efbe6346741691e0e9`、live checkoutの既存life/video差分は前後同一 |
| P2 | **TODO** | retryable infrastructure failure（429 / 5xx / timeout / provider unavailable）だけで別modelへ切り替える fallback と、失敗modelをcooldownする circuit breaker を実装する。品質・安全判定をmodel切替で迂回しない | 2回目のfresh reviewでsystem wrapper外側のauth retry/completion respawnがfull promptを再実行する反例を確認。temp HOME system RED 7ケースとcontract REDを追加し、P3前のblind respawnを安全停止する修正を検証中 |
| P3 | **TODO** | finite quality best-draft、platform別resume、run lock/idempotencyを現行実装と照合監査し、不足だけを実装する。品質上限到達は最良draftで先へ進み、既にliveの媒体は再投稿しない | 既存経路の監査表、欠落分のRED→GREEN、途中失敗から同一run再開、重複live URL 0件 |
| P4 | **TODO** | `ai.anicca.article-daily` をmanual kickstartし、日次writer自身が全媒体へ公開する最終E2Eを行う。全live URLとreality gateを実測し、その後の06:00 schedule起動も確認する | manual runの同一run exact6、全媒体live URL実読、ledger `published:true` + `reality_gate:PASS`、Telegram、次回06:00 launchd run evidence |
