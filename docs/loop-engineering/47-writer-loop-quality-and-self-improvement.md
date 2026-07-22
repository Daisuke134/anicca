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

旧導入順は完了または廃止。現在の実行順序は **§18.8 E1→E8だけ**を正本とする。

TaskList の現在状態は §16.5 と §18.8 を正本とする。D1-D8 と P1-P3 は **DONE**。旧 P4 は配信集合・runtime 境界が変わるため §18 の E1-E8 へ移管する。残作業の順序と状態は §18.8 だけを更新する。

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
| X 投稿（短文/フック） | @diceai0、日本語standalone 1本/日 | 発見・プロフィール導線 |
| 記事（現行） | note/ja、Zenn/ja、Substack/ja+en | 単発¥ + subscription |
| 電子書籍（長文） | Zenn Book / Gumroad / 自社Stripe | ebook単発売上 |

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

## 10. 履歴スナップショット（2026-07-19。当時の認識、現在状態ではない）

今日の pass が JA+EN を全 platform に draft stage 済み（実測、articles.jsonl + 実 draft URL）:
zenn-ja / devto-en / substack-ja / substack-en / note-ja / x-ja / x-en。X も @diceai0 復帰で通る。
gate 骨格 + 自律(#14) + 収益連動(#13) + form(#12) + explainer(#9) 全て稼働。**残るは #7 arm（ARTICLE_AUTOPUBLISH=1）**
のみで、これは複数日 watch で品質が別 topic でも安定して 70+ を出すのを実測してから最後に引く。

## 11. 旧 #7 arm / #8 OSS gap（履歴。現在の設計は §18）

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

## 12. 旧 TODO（履歴。現在の残TODO正本は §18.8）
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

## 13. no-skip裁定の履歴（§18がbounded quality + durable resumeとして現在化）

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

## 14. 旧FULL TODO（履歴。順序の正本ではない）

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
## 16. WRITER ENGINE — 3 lane baseline（現在の運用正本は §18）

**是正**: これは「article loop」ではない。**1つの self-improving engine が短文・中文・長文の3 lane に毎日/毎週/毎月書く**。記事は lane の1つにすぎない。X 短文 lane と書籍 lane は「後で」ではなく engine の初期形態に含まれる。

### 16.1 3 lane 構成（全 lane が同じ CORE を共有）
| lane | 頻度 | 出力 | taste 調達元（vendor 済み） | 金 |
|---|---|---|---|---|
| SHORT (X 単体投稿) | **毎日ちょうど1本、jaのみ** | @diceai0 の standalone 投稿。外部リンクなし。MID の同日 finding を280 weighted chars以内に圧縮 | `x-algorithm` + Gingiris 閉ループ + `recursive-improver` の social-post rubric（最大5版） | 直接 ¥0。プロフィール導線から MID の母数を作る |
| MID (記事=newsletter) | 毎日1題×2言語 | note/ja、Zenn/ja、Substack/ja、Substack/en、Dev.to/en、X Articles/ja、X Articles/enをすべてlive公開 | `ai-entity-article-writer` + STORM式+hooks+storytelling+humanizer/shimo4228（bakeoff 実証） | subscription 月額は設定値 + note 単発 ≤¥500 |
| LONG (書籍) | 月1冊、30本の新規MID在庫が条件 | 日本語1冊を Zenn Book + Gumroad + 自社Stripe の3出口へ同一版で公開 | `book-writer`。Nigh/show-me-the-story の中断再開・章整合 pass をMIT範囲で copy+tweak、PandocでEPUB/PDF | ¥1,500-3,000/冊。MRRとは分離集計 |

CORE（共有）: queue+exemplar 学習(T6) → 執筆 → verify（rubric+conscience gate W1+bounded revise W2+token 予算）→ 公開（CDP 直、credential ゼロ）→ 学習（実売還流 T12 / owner-veto / 週次監査）。

### 16.2 フォーム lane タスク（TaskList 登録: F1/F2）
| # | 内容 | 依存 |
|---|---|---|
| F1 | X 短文 lane 実装: 毎日ちょうど1本・日本語・@diceai0・standalone・外部リンクなし。`x-algorithm` + social-post rubric + conscience gate、日付単位のidempotency receipt、翌日imp/eng実測を実装 | §18 E1-E4 |
| F2 | 書籍 lane 実装: 直前の未使用MID在庫30本を選定→章構成→章別執筆→全書整合→EPUB/PDF→Zenn Book/Gumroad/自社Stripe exact3 publish | §18 E5 |

### 16.3 金の地図（strict $10k MRR。§15.1 free-first と整合）
- **MRR はsubscriptionだけ**を数える。note買い切りとebook売上は月次売上に含めるがMRRへ混ぜない。
- Phase F（最初の30本）: SHORT が発見、MID が検索在庫とemail subscriberを作り、LONGの材料を貯める。無料記事からsubscriber転換率を実測する。
- Phase S: 1 colony の基準を paid subscriber 100人 × ¥500相当 = **¥50,000 MRR** とする。単発記事・ebookは別ledger。
- Phase R: 計画レート ¥150/$ を固定して **30 colonies × ¥50,000 = ¥1,500,000 ≈ $10,000 MRR**。別解は15 colonies × paid subscriber 200人。達成を保証せず、subscriber転換率とOSS稼働colony数を週次実測する。
- cost gate: lane/runtime別のsubscription quota消費と外部実費をledger化し、1 colonyの粗利が正になるまで高価なmodelを増やさない。
- 未検証 3変数: visitor→free subscriber / free→paid subscriber / OSS install→稼働colony。§18のmeasurement contractで実数化する。

### 16.4 実行順序と MID lane スプリントの done 条件（2026-07-20 Dais 裁定。goal-setter 形式。これが次セッションの正本）

**Order は lane 逐次: MID(記事) を完全に終わらせる → SHORT(F1) → LONG(F2)。** F1/F2 は MID done まで着手禁止（次々セッション以降で Dais が指示）。

**Objective**: D1-D8 の履歴上のdone条件として、既存 `ai.anicca.article-daily` の当時のexact6公開を実証する。現在の配信集合、X本数、runtime、folder構造は §18 が上書きする。

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

## 17. Model fallback sprint（履歴。現在のTaskListは §18.8）

**Objective**: 日次 writer を単一 provider/model の障害で停止させず、有限の品質改善後も最良 draft から配信を再開し、毎日1記事を全媒体へ重複なく公開する。

**Order**: P1 → P2 → P3 → P4。P2-P4 は前段が DONE になるまで完了扱いにしない。

設計根拠: ソース [Anthropic Model migration guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) / 核心の引用: “Start with the xhigh effort level for coding and agentic use cases”。実際に採用するmodel名は推測せず、同じCLIProxy経路の実probeで成功した値だけを使う。

fallback設計根拠: ソース [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) / 核心の引用: “Enable automatic fallback to the specified model(s) when the primary model is overloaded or not available ... Accepts a comma-separated list tried in order.” 同時にソース [Claude Code model configuration](https://code.claude.com/docs/en/model-config) / 核心の引用: “Authentication, billing, rate-limit, request-size, and transport errors never trigger a switch”。したがって既存 `--fallback-model` はavailability/overload用にfull process内へ保持し、明示的なcandidate切替は副作用なし `MODEL_OK` preflightの429/5xx/connection/初回応答timeoutだけに限定する。healthy candidate決定後のfull article promptは最大1 process・1回で、終了rcや自由出力をmodel障害分類せずそのまま返す。記事開始後のresume/idempotencyはP3の責務。circuit breakerはソース [Microsoft Azure Architecture Center: Circuit Breaker pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker) / 核心の引用: “fail fast without making the remote call when an operation is likely to fail” に従い、永続cooldown中は既知の不健康modelを呼ばない。

| # | 状態 | 内容 | done evidence |
|---|---|---|---|
| P1 | **DONE** | 日次 writer の primary model を `gpt-5.6-luna`、effort を `xhigh` にする。`ARTICLE_MODEL` / `ARTICLE_EFFORT` の明示的 default とし、CLIProxy認証とローカル認証の両分岐が同じ値を使う | profitable-claude `7907269`: contractを先に変更した旧実装REDは `rc=1`（Luna default欠落、xhigh default欠落、共通引数0件、hard-coded Sonnet残存）。実装後は `bash -n rc=0`、contract `rc=0`、quality-best-effort / run-completion / run-prune-pending / zenn-deferred-retry は全て `rc=0`。render wiringは今回差分外の古いSTEP列期待により11/12で、変更前live checkoutでも同一失敗を再現。実CLIProxy probe `claude --model gpt-5.6-luna --effort xhigh --no-session-persistence --tools '' -p 'Reply with exactly: MODEL_OK'` は6秒で `rc=0` / `MODEL_OK`。profitable-claude は branch、`origin/main`、live checkout がすべて `7907269df887a246e04176efbe6346741691e0e9`、live checkoutの既存life/video差分は前後同一 |
| P2 | **DONE** | retryable infrastructure failure（429 / 5xx / timeout / provider unavailable）だけで別modelへ切り替える fallback と、失敗modelをcooldownする circuit breaker を実装する。品質・安全判定をmodel切替で迂回しない | profitable-claude `4bbcd7c` は副作用なし `MODEL_OK` preflightだけでcandidateを切替え、healthy model決定後のfull promptを1回だけ実行する。永続stateは`flock`付きatomic RMW、known secretはchunk境界を含めてlogからredactする。auth/billing/usage/ENOENT/EACCESとfull-pass終了結果は明示fallback対象外。実CLIProxyではSonnet preflightが20秒timeout→Luna選択→full `MODEL_OK` `rc=0`、proxy secret露出なし。2回目のfresh reviewでwrapper外側のauth retry/completion respawnがfull promptを再実行する反例を検出し、`f5567da` でP3前のblind replayを停止する。temp HOME system 7ケース（`rc=0` incomplete、partial+503、timeout、auth、ordinary failure、cooldown `rc=75`、Zenn handoff）はwrapper full invocationが各exact1、partial marker最大1、lock解放・alert/handoff・`exit 0`を実測。helper+system pytestは32/32 PASS、article-daily contract全PASS、`bash -n`・helper `py_compile`・`git diff --check` PASS、関連regression 17/17 PASS。`origin/main` とlive checkoutは `f5567dac760c45c9571fc6577a38dc0ea82b9bd0`、既存life/video差分のSHA-256は反映前後同一。platform別の安全な再開はP3の責務 |
| P3 | **DONE** | finite quality best-draft、platform別resume、run lock/idempotencyを現行実装と照合監査し、不足だけを実装する。品質上限到達は最良draftで先へ進み、既にliveの媒体は再投稿しない | profitable-claude `30942bbc9dec3ba69ad43a37da6209e4b86aa2a4`。TDDでcurrent `ARTICLE_RUN_DIR`+prior state/ledger、外部/final-symlink/`..` draft、missing env、`plan`→terminal競合、safety/hash/missing/ambiguous直後の`begin_resume`、partial ledger receipt crash窓、state/ledger URL矛盾、live-state ledger欠落repair、managed Substack staging bypassをそれぞれREDで再現してGREEN化。state/run/draft/ledgerはcanonical同一runへbindし、`begin_resume`は同一`flock`内で全条件を再評価してpending時だけattemptを増やす。current-runのpair別`published:true`+`reality_gate:PASS` receiptはstate write前crash後も再投稿せず、URL矛盾はambiguous停止、ledger欠落だけはstate receiptからidempotent repairする。初回・resume promptとSubstack stagingは3 envを必須化し、intent/planはshared guard経由。live checkoutでserial 93/93（61.79s）、`-n 7` 93/93（26.32s）、関連shell 13/13、article contract全PASS、Substack shell 8/8、`bash -n`、`py_compile`、`git diff --check` PASS。fresh-context artifact-only adversarial reviewは`ok:true` / findingsなし。`origin/main`=live checkout=`30942bb`、既存dirty fingerprintはtracked `cfc915c35a9dd75814d71898f80c55ab5b66f4e9d1cf7f7a557f8fbfa4819fb8` / untracked `d541f2ba4383732ddfe64e157c69ed526e323f533068b597c544409736fbda4e`で反映前後同一。P4のkickstart/live公開は未実行 |
| P4 | **MIGRATED → §18 E1-E8** | 旧exact6/Claude CLI経由のmodel aliasを前提にした最終E2Eは実行しない。X Post/ja、X Articles/ja+en、Dev.to/enを含む新exact8を、native Codexまたはnative Claudeで実装する | 旧run `20260721-191239` のnote/jaだけがlive。§18.7のincident evidenceと§18.8を正本にする |

### 17.1 P3 audit（正本）

| pair / concern | 監査前 | P3後のmechanical evidence |
|---|---|---|
| finite quality / best draft | rubric・readerは各lang 3評価上限、質問cache固定、quality advisory継続、identity/conscienceだけBLOCK。best-score draft復元はwriter契約 | 既存gate ownerの`fcntl`/atomic cap、terminal hash、quality advisory、安全BLOCK回帰を維持。publication stateはconscience ALLOW後のja/en hashを固定し、resumeで再draftを拒否 |
| note/ja | draft keyとnote API readbackはあるが、live intent/current-run guardなし | note keyをstable target化し、click前に`GET /api/v3/notes/{key}`。既liveはclickせずreceipt/ledgerだけrepair |
| x/ja・x/en | draft URLはあるがpair分離したdurable receipt/guardなし | 2 pairを独立保存。CDPで同じdraft URLを再openし、redirect/canonical・Publish/Published viewをreadback。unknownは再clickせずambiguous停止 |
| zenn/ja | slug/deferred artifact/API/lockは既に最も強い | 既存`zenn-deferred-control.py`をcopy+tweakしshared stateへ接続。exact5はgeneric model resumeより前にworkerへhandoff |
| Substack ja/en | 毎回new draft、POST成功後crash時のslug喪失でduplicate余地 | ja/en別draft IDを最初に保存・再利用し、`GET /api/v1/drafts/{id}`のexplicit `is_published`/`post_date`/slugでPOST前readback。managed stagingはdraft作成前にcurrent run/state/ledger/pairをshared guardで検証し、missing/mixed envとmissing fieldをnot-liveと推測しない |
| wrapper | P2安全策としてfull pass exact1、partial失敗は停止 | 全6 stable targetを最初のlive side effect前にguard経由で登録。canonical pair receiptを完了正本として、partial crashは残pairだけ、ledger欠落はrepair対象だけをsame run/draftで最大2回再入する。`begin_resume`はplan相当条件を同一lock内で再検証し、missing/ambiguous/safety/all-complete/cooldownは再入しない |

設計根拠: ソース [AWS Lambda Powertools idempotency utility](https://github.com/aws-powertools/powertools-lambda-python/blob/develop/docs/utilities/idempotency.md) / 核心の引用: “an operation does not cause additional side effects if it is called more than once with the same input parameters.” 同資料の “PutItem for locking and UpdateItem for completion” に合わせ、side effect前intentと完了receiptを分離する。ソース [Stripe Python README](https://github.com/stripe/stripe-python/blob/master/README.md) / 核心の引用: “Idempotency keys are automatically generated and added to requests ... to guarantee that retries are safe.” stable targetをpair別idempotency identityとして使う。ソース [Temporal Python SDK](https://github.com/temporalio/sdk-python/blob/main/README.md) / 核心の引用: “distributed, scalable, durable, and highly available orchestration engine”。再実行の判断をmodel記憶ではなくdurable stateへ置く。

## 18. Writer Engine v2 — X Post 1/day・X Articles ja/en・月次book・native Codex/Claude（現在の正本）

### 18.1 Overview

目的は「毎日6時にagentを起こす」ことではなく、**利用可能なsubscription CLIを1つだけ使っても、同じ公開契約を最後まで完走し、停止後も同じrunを重複なく再開すること**。モデルは文章と判定だけを担当し、schedule・状態遷移・投稿・reality readback・再送は決定論scriptが所有する。Xの短文投稿と長文Articleは別formであり、別slot・別artifact・別intent/receiptとして扱う。

#### 出力・言語・skill・頻度

| form | 作るもの | 言語 | canonical skill | 公開先 | schedule |
|---|---|---|---|---|---|
| SHORT / X Post | 280 weighted chars以内のstandalone X投稿。X Articleとは別の短文。画像は同日MIDの図を再利用可、外部リンクなし | **日本語だけ** | `x-algorithm` + `recursive-improver/social-post`。事実・voiceはwriter COREを共有 | @diceai0 に**exact1 live/JST日** | 12:00–23:55 JSTのdate-slot window。ready済み未投稿runをrun日昇順FIFOで1件だけ割当。12:00時点で0件なら5分workerがwindow終了まで最初のreadyを待つ |
| X ARTICLE | 同じMID本文の長文X Article。tweet/X Postとして数えない | **ja + en** | `ai-entity-article-writer` のsafe MID artifactを再利用。X Article publisherは文章を書き換えない | @diceai0 に**runごとにja exact1 live + en exact1 live** | jaはsafe pair確定後。enの`not_before`はjaのplatform readback `published_at + 6h` |
| MID | 同じfindingの日本語原稿と英語原稿 | ja + en | `ai-entity-article-writer`。humanizer、rubric、reader test、identity、conscienceをCOREから読む | note/ja、Zenn/ja、Substack/ja、Substack/en、Dev.to/en = **exact5 live** | 毎日06:00 JSTに1 run enqueue。safe pair確定後にlive publish |
| LONG | 直前の未使用MID 30本を再構成した日本語book、EPUB/PDF/Markdownを同じcontent hashから生成 | **日本語だけ** | `book-writer`。`show-me-the-story` の章記憶・中断再開・全書整合をcopy+tweak | Zenn Book、Gumroad、自社site+Stripe = **exact3 live** | 毎月1日09:00 JST。30本未満なら生成せずinventory receipt |
| LEARN | metrics snapshot、実験案、candidate taste | 出力言語に依存 | `recursive-improver` + held-out evaluator | 公開しない。採用済みtasteだけCOREへ昇格 | 日次22:30 metrics、日曜22:00 weekly decision |

healthy daily runの公開receiptは **MID exact5 + X Articles exact2 + X Post exact1 = exact8**。X Postは日本語1本だけであり、X Articles ja/enとは別に数える。Dev.to/enを含む全配信先はlive公開が成功終端で、draft/staged URLは内部中間状態に限り、日次完了にも売上導線にも数えない。X Post本文に外部リンクを置かず、同日にreplyも作らない。X Articlesはplatform readbackの`published_at`を基準に、enをjaの6時間後から6時間10分後までにlive公開する。X Postのdate slotはX Articlesの時刻から独立させ、12:00–23:55 JSTに最初にreadyになった最古runが当日slotを所有する。window終了までreadyが0ならEMPTY+alertとし、翌日以降の最初の未使用slotをFIFOで待つため、後続runは追い越さず同日に2本作らない。

#### Runtime contract

| role | native Codex runtime | native Claude runtime |
|---|---|---|
| writer / translator | `codex exec` + `gpt-5.6-luna` + `high` | `claude -p` + `sonnet` + `high` |
| per-draft judge | `codex exec` + `gpt-5.6-terra` + `medium` | `claude -p` + `haiku` + `high` |
| weekly self-improve proposer/reviewer | `codex exec` + `gpt-5.6-terra` + `xhigh`、fresh processを2本 | `claude -p` + `sonnet` + `high`、fresh processを2本 |
| publishers / state / scheduler | modelを呼ばない | modelを呼ばない |

`WRITER_RUNTIME=auto|codex|claude` とする。`auto` は副作用なし `MODEL_OK` probe、永続circuit breaker、設定された優先順 `codex,claude` でhealthy providerを1つ選ぶ。provider内のmodel fallbackとprovider間fallbackを混同しない。生成途中でproviderが枯れた場合は、次のresume workerが同じrun manifest・同じschema・既存artifact hashからもう一方で続ける。`claude` runtimeの実行中に`codex` binaryが無くても完走し、逆も同じ。Sol/Fable/API key/CLIProxyを必須経路にしない。

### 18.2 Acceptance Criteria

| AC | done条件 |
|---|---|
| AC1 daily cardinality | 1 runの完了条件はnote/ja、Zenn/ja、Substack/ja、Substack/en、Dev.to/en、X Article/ja、X Article/en、X Post/jaのexact8がすべて `published:true` + `reality_gate:PASS`。X Postは同一JST日exact1でFIFO date-slot ownerを持ち、X Articleはrunごとにja/en各exact1。draft/stagedだけのpairは0件。同じ入力の再実行でpublic side effectは0増分 |
| AC2 bounded quality | reader question setはrunの初回に1回だけ固定。ja/en各最大5 candidate。5回でquality閾値未達でもidentity/conscienceを通る最高点draftを公開する。quality理由のcarry-over終端を作らない |
| AC3 safety boundary | identity、虚偽、権利侵害、conscienceはqualityと別のblocking gate。全candidateがunsafeなら公開せずquarantine receiptを残す。availability/quality失敗をsafetyと偽装しない |
| AC4 durable resume | 06:00 jobはrunをenqueueして短時間で解放。5分workerが未完runを再開し、stale lockはPID/start-time/owner tokenを照合してowner不在時だけ回収。429、timeout、process kill、成功応答喪失の各fixtureで重複公開ゼロ |
| AC5 provider independence | `PATH`からClaudeを除いたCodex-only fresh homeでdaily exact8。Codexを除いたClaude-only fresh homeでもdaily exact8。片方のweekly limit中に`auto`がhealthy側へ切替。全LLM callがruntime adapter経由で、adapter外の `claude` / `codex` 直呼びはgrep 0 |
| AC6 monthly book | X Postを除くarticle exact7を完了した未使用MID topicが30本ある月に日本語bookを1冊だけ生成。章別source map、引用、重複率、前後整合、EPUB validationを通し、Zenn Book/Gumroad/self-site exact3のlive URLをreadback。再実行で2冊目を作らない |
| AC7 self improvement | 日次はmetricsをappendするだけ。週次にTerraまたはClaude側modelが1変更だけ提案し、held-out ja/en/form test、7日canary、keep/revertを実測。taste/rubricだけ自動昇格し、実行code変更はtest付きpatch artifactに留めproductionへ自己適用しない |
| AC8 clean OSS install | tracked codeは下記TO-BE treeだけ。fresh cloneで`./install.sh --runtime codex`または`--runtime claude`が動き、他providerのloginを要求しない。runtime state、browser profile、credential、generated bookはrepo外。旧skill copy・旧finalizer・hardcoded home pathは0件。X Article、X Post、Dev.to publisherは新SSOTに各1実装だけ存在する |
| AC9 measurement | dailyにX impressions/engagement、各記事view/free subscriber/paid subscriber、platform receiptを記録。monthlyにstrict MRRとone-off売上を別集計し、30-colony式の各変数を実数で更新 |
| AC10 notification | state transitionと同じtransactionでTelegram outboxへlogical eventをexact1 appendする。必須eventはRUN_ENQUEUED、RUNTIME_SELECTED/UNAVAILABLE、QUALITY_SELECTED、SAFETY_QUARANTINED、X_POST_SLOT_ASSIGNED/EMPTY、各pairのPLATFORM_LIVE/PENDING/FAIL、RETRY_SCHEDULED/RESULT、DAILY_COMPLETE、BOOK_INVENTORY_SHORT、`BOOK_BUILD_STATE(stage=plan|chapters|consistency|pandoc|epub,status=started|pending|pass|fail)`、BOOK_PLATFORM_LIVE/PENDING/FAIL、BOOK_COMPLETE、METRICS_COMPLETE/FAIL、WEEKLY_EXPERIMENT_KEEP/REVERT/FAIL。配送はat-least-onceとし、send receiptがないeventを5分workerが再送する。各messageにevent UUIDを表示し、送信成功後の応答喪失によるTelegram上の重複を識別可能にする |

### 18.3 As-Is / To-Be

| concern | AS-IS（実測） | TO-BE |
|---|---|---|
| X | X Articlesをja/enの2本公開するpromptはあるが、通常X Postは未実装で、2 formのslot/receipt分離がない | X Articlesはrun別ja/en pairをplatform `published_at`差6時間〜6時間10分で公開。X Postは独立した日本語exact1/JST日slotをFIFO所有。3 pairを別idempotency keyで重複禁止 |
| daily outputs | exact6にX Articles ja/enを含み、Dev.to/enはdraftだけ | note/ja、Zenn/ja、Substack/ja+en、Dev.to/en、X Articles ja+en、X Post/jaのexact8をすべてlive公開。draft-only成功終端は0 |
| runtime | top-level fallbackはあるが7 judge、platform agent、self-improveに`claude`直呼びが残る。Luna aliasもClaude CLI経由 | native `codex exec` / native `claude -p` adapter。全processが共通JSON schemaを返す |
| stop behavior | reader testが毎回新質問を作り、有限budget後に両言語carry-over。lockが残ると次回06:00もskip | 質問固定、最大5でbest-safeをship。incompleteはterminalにせずresume queueへ。ownerless lockは回収 |
| book | form定義だけ。`zenn-book`/KDPはpendingでpublisher E2Eなし | 30 MID inventory→plan→chapters→consistency→EPUB/PDF→exact3 publishを月次workerが所有。KDPは配信集合から削除 |
| source tree | active `profitable-claude` と古い `~/.openclaw/skills/ai-entity-article-writer` copyが分岐。存在しない `~/.claude/...` symlink記述あり | tracked SSOT 1個 + repo外data dir 1個 + installされたlaunchd plist。skill discoveryに依存せずmanifestでcanonical promptを列挙 |
| self improve |複数のdaily/weekly shellがあり、Sonnet直呼びと役割重複 | metrics collector、weekly experiment、promotion validatorの3責務だけ。Terra既定、Claude-only mappingあり |

#### TO-BE folder tree（tracked SSOT + runtime data + LaunchAgents）

```text
profitable-claude/
├── skills/
│   └── writer-engine/                         # 唯一のcode/content SSOT
│       ├── SKILL.md                           # 人間向け入口。詳細は下位正本への参照だけ
│       ├── install.sh                         # --runtime auto|codex|claude
│       ├── bin/
│       │   └── writer                         # enqueue|resume|book|learn|health|status
│       ├── config/
│       │   ├── forms.toml                     # xpost/xarticle/article/bookのlanguage・exact set
│       │   ├── runtime.toml                   # provider順・role→model/effort
│       │   ├── schedule.toml                  # 定期job + X Post 12:00–23:55 window + Article ja published_at+6h
│       │   └── destinations.toml.example      # account名・URLだけ。secretなし
│       ├── runtime/
│       │   ├── adapter.sh                     # probe/run/resume/structured-output
│       │   ├── codex.sh                       # native codex execだけ
│       │   ├── claude.sh                      # native claude -pだけ
│       │   ├── schemas/                       # draft/judge/proposal JSON Schema
│       │   └── circuit-breaker.py
│       ├── core/
│       │   ├── enqueue.py                     # JST date idempotency key
│       │   ├── orchestrate.py                 # durable state machine
│       │   ├── resume.py                      # pendingだけ再開
│       │   ├── locks.py                       # PID/start/owner-token lease
│       │   ├── ledger.py                      # intent→receipt→reality
│       │   ├── schedule.py                    # FIFO X Post date slot + X Article not_before
│       │   └── inventory.py                   # MID→bookの30本消費
│       ├── forms/
│       │   ├── xpost/
│       │   │   ├── SKILL.md                   # x-algorithm参照、ja 1/day
│       │   │   ├── prompt.md
│       │   │   └── rubric.json
│       │   ├── xarticle/
│       │   │   └── manifest.toml              # MID ja/en artifactをそのままexact2へ写す
│       │   ├── article/
│       │   │   ├── SKILL.md                   # ai-entity writerの統合後正本
│       │   │   ├── prompt-ja.md
│       │   │   ├── prompt-en.md
│       │   │   └── rubric.json
│       │   └── book/
│       │       ├── SKILL.md                   # book-writer正本
│       │       ├── plan.schema.json
│       │       ├── chapter.prompt.md
│       │       └── consistency-rubric.json
│       ├── gates/
│       │   ├── deterministic/                 # purity/SEO/citation/hash/EPUB
│       │   ├── quality/                       # rubric + fixed reader questions、max5
│       │   ├── safety/                        # identity/honesty/conscience
│       │   └── reality/                       # platform live readback
│       ├── publishers/                        # modelを呼ばない
│       │   ├── x-post/                        # create intent/readback/dedupe
│       │   ├── x-article/                     # ja/en別run slot、published_at差6h〜6h10m
│       │   ├── note/
│       │   ├── zenn-article/
│       │   ├── substack/
│       │   ├── devto/                         # enをlive公開、draft-only禁止
│       │   ├── zenn-book/
│       │   ├── gumroad/
│       │   └── stripe-site/
│       ├── notifications/
│       │   ├── telegram-outbox.py             # 状態変化をdurable append
│       │   └── telegram-send.py               # send receiptまで完了扱いしない
│       ├── learning/
│       │   ├── collect-metrics.py
│       │   ├── propose-experiment.py
│       │   ├── evaluate-canary.py
│       │   └── promote-or-revert.py
│       ├── vendor/
│       │   ├── LICENSES.md
│       │   ├── x-algorithm/
│       │   └── show-me-the-story/              # MITの必要部分だけ+upstream commit
│       ├── deploy/
│       │   └── launchd/
│       │       ├── ai.anicca.writer-daily.plist          # 毎日06:00 enqueue
│       │       ├── ai.anicca.writer-resume.plist         # 300秒ごと pending resume
│       │       ├── ai.anicca.writer-book-monthly.plist   # 毎月1日09:00
│       │       ├── ai.anicca.writer-learn-daily.plist    # 毎日22:30 metrics
│       │       └── ai.anicca.writer-learn-weekly.plist   # 日曜22:00 decision
│       ├── tests/
│       │   ├── contract/                       # provider直呼び0、schema、cardinality
│       │   ├── integration/                    # crash/429/stale-lock/receipt-loss
│       │   ├── e2e/                            # codex-only、claude-only、book exact3
│       │   └── fixtures/
│       └── docs/
│           ├── install.md
│           ├── operations.md
│           └── money-model.md
└── ...

~/.local/share/writer-engine/                  # WRITER_DATA_DIR、repo外
├── queue/                                     # dateごとのdaily/monthly job
├── runs/<run-id>/
│   ├── manifest.json                          # runtime/model/input/output hashes
│   ├── drafts/{ja,en}.md
│   ├── xpost/ja.txt
│   ├── xarticle/{ja,en}.md
│   ├── gates/
│   ├── intents/
│   ├── receipts/
│   └── notifications/
├── books/<book-id>/{plan.json,chapters,book.md,book.epub,book.pdf}
├── ledger/{publications.jsonl,metrics.jsonl,revenue.jsonl}
├── experiments/{candidate,canary,kept,reverted}/
├── locks/
└── archive/legacy-article-writer/              # 旧run/stateは削除せずread-only移行

~/Library/LaunchAgents/                         # install.shがtracked plistから設置
├── ai.anicca.writer-daily.plist
├── ai.anicca.writer-resume.plist
├── ai.anicca.writer-book-monthly.plist
├── ai.anicca.writer-learn-daily.plist
└── ai.anicca.writer-learn-weekly.plist
```

削除対象は、移行receipt作成後の旧 `article-d7d8-finalizer`、`orca-zenn-finalizer`、個別 `run-*-agent.sh`、古いOpenClaw skill copy、存在しないClaude symlink記述、repo内runtime state。X Articles/Dev.to publisherは削除せず新SSOTへ各1実装として移植し、通常X Post publisherを別formとして追加する。旧ledgerとrun artifactは `archive/legacy-article-writer/` へ移して消さない。

#### Full TO-BE execution ASCII

```text
                                  ┌──────────────────────────────┐
毎日 06:00 JST ──launchd────────>│ enqueue(date=JST, lane=MID) │
                                  └──────────────┬───────────────┘
                                                 │ 同日keyは1個だけ
                                                 v
                                  ┌──────────────────────────────┐
                                  │ runtime probe (no side effect)│
                                  │ codex healthy? ─yes─> Codex  │
                                  │       no                     │
                                  │ claude healthy?─yes─> Claude │
                                  └──────────────┬───────────────┘
                                                 │ neither healthy
                          Telegram UNAVAILABLE ←┤ queue保持、5分後resume
                                                 v
┌──────────────┐  research  ┌──────────────┐  ja/en  ┌─────────────────────────┐
│ topic queue  ├───────────>│ article core ├───────>│ deterministic + quality │
└──────────────┘            └──────────────┘        │ quality revise max 5     │
                                                    │ → best SAFE draft        │
                                                    │ safety FAIL→quarantine   │→Telegram
                                                    └────────────┬────────────┘
                                                                 │ safe pair
                  ┌──────────────────────────────┴──────────────────────────────┐
                  │                                                             │
                  v                                                             v
     ┌────────────────────────────┐                              ┌──────────────────────────┐
     │ MID live publish exact5    │                              │ Xは別form・別slot        │
     │ note ja                    │                              │ T+0h X Article ja        │
     │ Zenn ja                    │                              │ +6h〜6h10m X Article en │
     │ Substack ja + en           │                              │ X Post ja=12:00–23:55  │
     │ Dev.to en                  │                              └────────────┬─────────────┘
     └──────────────┬─────────────┘                                           │
                    │                                                         │
                    └──────────────────────────┬──────────────────────────────┘
                                               │ X Postはwindow内readyをFIFO割当
                                               │ each: intent→publish→readback
                                               │ draft-only terminalは禁止
                                               v
                                  ┌──────────────────────────────┐
                                  │ article exact7 reality PASS?│
                                  │ yes: book inventory +1      │
                                  │ + X Post = exact8 COMPLETE? │
                                  │ no : PENDING、5分workerへ    │
                                  └──────────────┬───────────────┘
                                                 │
                     ┌───────────────────────────┼────────────────────────────┐
                     │                           │                            │
                     v                           v                            v
           Telegram outbox               22:30 metrics              毎月1日09:00
           全stateと同transaction         日曜experiment             unused article exact7 >=30?
           UUID / at-least-once配送       keep / revert              no→receipt+Telegram
                                                                         │yes
                                                                         v
                                                              ┌────────────────────┐
                                                              │ plan→chapters      │
                                                              │ consistency pass   │
                                                              │ Pandoc EPUB/PDF    │
                                                              └──────────┬─────────┘
                                                                         v
                                                        Zenn Book + Gumroad + Stripe
                                                        exact3 live + readback + revenue
```

#### Strict $10k MRR ASCII

```text
X Post 日本語1本/日 + X Articles ja/en
      │ impressions / profile visits
      v
無料MID記事（ja検索 + en newsletter）
      │ visitor → free subscriber（実測）
      v
paid subscription ¥500相当/月 ───────────────┐
                                              │
1 colony: 100 paid × ¥500 = ¥50,000 MRR       │ strict MRRだけ
30 colonies: 30 × ¥50,000 = ¥1,500,000 MRR ──┴─≈ $10k（計画レート¥150/$）

30 MID記事 ──> 月次book ──> 単発売上 + 新規読者
                              ※ここはMRRに混ぜない
```

### 18.4 Test Matrix

| test | setup | expected evidence |
|---|---|---|
| Codex-only | fresh HOME、Claude binaryをPATHから除外、Codex subscription login | exact8 live、manifest runtime=codex、`claude` invocation 0 |
| Claude-only | fresh HOME、Codex binaryをPATHから除外、Claude subscription login | exact8 live、manifest runtime=claude、`codex` invocation 0 |
| Claude exhausted | Claude probe fixtureがweekly-limit、Codex healthy | full prompt前にCodex選択、同じrun exact8 |
| Codex exhausted | Codex probe fixtureがusage-limit、Claude healthy | Claude選択、同じrun exact8 |
| both unavailable | 両probe失敗 | public side effect 0、PENDING、5分workerで同じrun再試行 |
| quality never reaches threshold | 固定reader Q、5 candidateすべて閾値未満、1つ以上safe | highest-score safe hashを公開、carry-over row 0 |
| safety violation | 全5 candidateがconscience BLOCK | public side effect 0、quarantine + alert。quality失敗とは別code |
| X form cardinality | 同じrunを2回enqueue、X publish成功後に応答喪失 | X Post/ja public ID exact1、X Article/ja exact1、X Article/en exact1。英語X Post 0、reply 0。X PostとX Articleは別schema/hashで、3 form/lang slot間のID混同0、ledger repairだけ |
| X Post date-slot backlog | 前日runのX Postが未公開のまま当日12:00を迎え、当日runもready | 前日runが当日の未使用slotを所有し、当日runは翌日以降の次slotへFIFO待機。同一JST日のX Post public ID exact1、追い越し0、両runは最終的にexact8 |
| X Post late-ready | 12:00時点でready run 0、18:07に1 runがready。別fixtureは23:55までready 0 | 18:10の5分workerが同日slotを割当してexact1 + X_POST_SLOT_ASSIGNED outbox exact1。ready 0のfixtureは当日slotをEMPTYにしてX_POST_SLOT_EMPTY outbox exact1をUUID付き配送し、runは翌日以降の未使用slotをFIFO待機 |
| X six-hour span | X Article/jaをlive後、platform readback `published_at`を保存。workerを+5h55m/+6h/+6h5m/+6h10mで起動 | +6h未満はX Article/en作成0。enのreadback `published_at - ja published_at` は6h以上6h10m以下、runごとにexact1 |
| Dev.to live-only | Dev.to APIがdraft作成後にprocess kill、worker再起動 | 同じarticle IDをliveへ昇格してreadback。draft URLだけではrun COMPLETEにならない |
| platform partial | note成功後kill、Substack片言語timeout | note再click 0、残pairだけ再開、最終exact8 |
| stale lock | owner PIDなし、PID再利用、live ownerの3fixture | ownerなしだけ回収。live ownerは並行run 0 |
| monthly inventory | unused article-exact7 MID 29/30/31本。X Post receiptは入力から除外 | 29=skip receipt、30=1冊exact3、31=同月2冊目0。X Post障害だけではbook在庫を失わない |
| book retry | Gumroad成功後response loss | 同じproduct IDをreadback、重複商品0、exact3 repair |
| self-improve | candidateがheld-out悪化 / 改善の2fixture | 悪化=revert、改善=7日canary後keep、1周期1変更 |
| Telegram unavailable | Telegram send timeoutと、送信成功後の応答喪失をfixture化 | state transitionとlogical outbox eventは同一transactionでexact1。配送はat-least-onceで、全messageに同じevent UUID。応答喪失時の重複messageは同UUIDで識別可能 |
| Telegram book build failure | plan、chapter、consistency、Pandoc、EPUB validationを各1回FAIL | 各stage/statusのBOOK_BUILD_STATE logical eventがexact1でoutboxにあり、event UUID付きで配送。bookはPENDINGまたはFAILの実状態と一致 |
| clean install | fresh cloneで各runtimeを単独install | hardcoded `/Users/anicca` 0、secret tracked 0、旧agent 0 |

#### E2E Judgment

| Item | Value |
|---|---|
| UI変更 | なし。Writer Engine、publisher、launchd、runtime stateの変更 |
| Maestro | 不要。iOS UIを変更しないため |
| 必須E2E | Codex-onlyとClaude-onlyの各fresh homeでdaily exact8をlive readbackし、X PostのFIFO 12:00–23:55 JST日slot、X Articlesのplatform `published_at`差6h〜6h10m、Dev.to live、Telegram event UUID/send receiptを検証。monthly workerはarticle exact7在庫からbook exact3のlive URLとEPUB validationを検証 |

### 18.5 Boundaries

- subscriptionとplatformの両方が利用可能という外部依存なしに「必ず毎日live」は保証できない。保証するのは、**少なくとも片方のruntimeと対象platformがhealthyなら自動完走し、そうでなければ同じrunを失わず自動再開すること**。
- quality gateは公開を永久停止しない。最大5版でbest-safeを出す。安全・虚偽・権利・投稿先不明だけはpublishより優先して止める。
- X Postは日本語exact1/JST日で、英語X Postとreplyは作らない。12:00–23:55 JSTを当日slot windowとし、ready済みrunが未使用date slotをrun日昇順FIFOで所有する。12:00時点でready 0なら5分workerがwindow内で待ち、23:55まで0ならEMPTY+alertとしてrunを翌日以降の次slotへ送る。遅延runを後続runが追い越さない。X Articlesは別formとしてrunごとにja/en各exact1を公開し、platform readback `published_at`差を6時間以上6時間10分以下にする。X PostとX Articleを同じcardinality slotへ入れない。
- draft/staged artifactは再開用の内部状態として保持してよいが、note/Zenn/Substack/Dev.to/X Articles/X Postのいずれもdraft-onlyを成功終端にしない。対象platformがunavailableならpairをPENDINGのまま5分workerへ渡す。
- monthly bookは日本語1冊。30本未満の月に薄い本を水増ししない。KDPは配信集合に含めない。
- self-improveはtaste/rubricの実験を自動化するが、実行codeを自己改変してproductionへ直適用しない。
- revenue diagramは計画式であって売上予測ではない。strict MRRとone-off revenueを分離する。

### 18.6 Research basis（一次資料・実repo）

| source | 採用する核心 |
|---|---|
| [OpenAI Codex README](https://github.com/openai/codex) | “Run `codex` and select **Sign in with ChatGPT**.” subscription利用者のnative Codex経路。実機 `codex login status` は `Logged in using ChatGPT` |
| [OpenAI Codex manual — Permissions and safety](https://developers.openai.com/codex/codex-manual.md#permissions-and-safety) | automationは必要最小権限にし、`--ignore-user-config`でambient configを隔離する。CodexにClaude型tool allowlistがないため、judgeはread-only sandbox・rules/config無視・web search無効を明示する |
| [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) | `--print` はnon-interactive、`--json-schema` はstructured output、`--fallback-model` はprimary unavailable時のmodel fallback。provider間fallbackは別adapterで実装する |
| [NyxFoundation/speca runtime registry](https://github.com/NyxFoundation/speca/blob/8b7da09eaf87737c1cb3b281b520a4bf71a73b55/scripts/orchestrator/runtime_registry.py) | runtimeごとのcommand/model/capabilityをregistryに集約し、workflowからprovider差分を隔離する構造をcopy+tweak |
| [synaptent/aragora CLI agents](https://github.com/synaptent/aragora/blob/04071f594de9052ff9bb5e1e2e8bc90f6217758f/aragora/agents/cli_agents.py) | “Pass prompt via stdin to avoid shell argument length limits.” 長文promptをargvへ載せずfile→stdinで渡す境界をcopy+tweak |
| [SQLite Transactions](https://www.sqlite.org/lang_transaction.html) | `BEGIN IMMEDIATE`でwrite transactionを先に取得し、state更新とTelegram logical outbox eventを同一transactionで確定する |
| [Apple Daemons and Services Programming Guide](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) | user agentは`~/Library/LaunchAgents`へ置き、`ProgramArguments`をtokenized arrayにする。tracked templateからinstalled absolute pathへ展開する |
| [TylerKoster/AMC sqlite outbox](https://github.com/TylerKoster/AMC/blob/460f615/pilot/sqlite_outbox.py) | SQLite transactionとoutboxを一体化する既存構造を参照し、stdlib `sqlite3`へcopy+tweakする |
| [Nigh/show-me-the-story](https://github.com/Nigh/show-me-the-story)（MIT） | “断点续作: 进度随时落盘，关闭程序后重新打开自动恢复” と、章ごとの事実確認・全書整合passをLONGへcopy+tweak |
| [SimonWaldherr/AI-Book-Generator](https://github.com/SimonWaldherr/AI-Book-Generator)（GPL-3.0） | concept→outline→chaptersとmulti-provider分離を設計参照する。GPL codeはcopyしない |
| [Pandoc: Creating an ebook](https://pandoc.org/epub.html) | “pandoc can produce output in the EPUB electronic book format.” Markdown正本からEPUBを決定論生成 |
| [x-algorithm skill source](https://clawhub.ai/NextFrontierBuilds/x-algorithm) | “No external links in main post”。ただし同skillの2-3本推奨よりDaisの1本/日裁定を優先 |
| [wshuyi/x-article-publisher-skill](https://github.com/wshuyi/x-article-publisher-skill) | Markdown parse・rich-text paste・画像挿入をcopy+tweakする。ただし上流は “Only saves as draft, never publishes automatically” なので、live publish・public ID・`published_at`・本文readbackはWriter Engine側で追加する |

### 18.7 Current incident evidence

- 旧article/orca LaunchAgent 9本はbootout済みでplistをrepo外read-only archiveへ保存した。`launchctl list`は新writer 5本だけで、daily 06:00、resume 300秒、book月初09:00、learn daily 22:30、learn weekly日曜22:00。全plistは`RunAtLoad=false`、切替時kickstart 0。
- 旧`state/.article-daily.lockdir`を含むlegacy stateは新agentから参照されない。repo外schema migration済みで、旧sourceは削除せず保持する。E4未配線の`writer-resume`は安全に`rc=75`を返し、public side effect 0。
- stderrは `article-daily.sh: line 240 ... File name too long`。長いarticle promptをcommand pathとして解釈した境界不良があり、wrapperの終了表示だけでは成功判定できない。
- run `20260721-191239` はnote/jaの`published:true` + `reality_gate:PASS`が1件だけ。残媒体のverified receiptはない。
- native CLI probe: `codex login status` = ChatGPT login。`gpt-5.6-luna low` と `gpt-5.6-terra low` は各 `rc=0 / MODEL_OK`。`claude auth status`はOAuth loginだがSonnet probeは `rc=1 / weekly limit / resets Jul 24 06:00 JST`。E2 adapterはClaude probe失敗後にCodexを選び、full promptをhealthy runtimeへexact1送信する。
- E1の事故fixtureは`codex/writer-e1-incident-red` commit `db32520012e238e4d40a9d55837c39970bc95427`へpush済み。ownerless lock、長文prompt境界、Claude weekly-limit、partial resumeの4件は、production interface未実装を原因とする固有`rc=1`を`RED_SUITE_CONFIRMED 4/4`で固定する。
- RED meta-runnerは4ケースごとのwrong rc / wrong reasonを拒否する8件とexact-positive 1件がPASS。runtime契約は`Claude probe -> Codex probe -> Codex full`の完全時系列を要求し、extra probeとwrong orderも拒否する。fresh artifact-only reviewは`ok:true / findings:[]`。
- legacy run archiveは`$HOME/.local/share/writer-engine/archive/legacy-article-writer/20260721-191239`。source/targetは各235 files、manifest SHA-256は`2fced19a70f81b7135babb0454f0516488ffff1f86a31eebadfaa1f1e35827ea`で一致し、archiveのwritable entryは0。
- E1前後のledgerは96行、SHA-256 `856af4bf992bf0624c679a3b75c3fd5141c4fe7046a6cecf819f515fbc3023b0`で不変。既liveはnote/ja [公開URL](https://note.com/anicca123/n/nbf2012b9953e) exact1を本文readback済みで、新規投稿増分は0。
- E2はfeature commit `8bb2aaedf4657cb520874409034c2ee95ca298e4`へpush済み。native Codex/Claudeのprobe/run/schema/circuitを`skills/writer-engine/runtime/adapter.sh`だけに集約し、article-writerのprovider/model直呼びはproduction contractで0件。長文promptはfile→stdin、full promptはprovider間replay 0。
- E2の主担当fresh検証はPython `73 passed + 27 subtests`、article shell `22/22`、focused E2 `42 passed`。実Codex/Luna-low probeは`rc=0`、raw stdout `MODEL_OK\n` exact9 bytes、stdout SHA-256 `33625b290395a098681e593cfd6849615c972380c7a6c300a943cb1ea03505b9`、calls SHA-256 `c5e588456c4abee4829140dd0adf50f8a67586d411271771a0d6c1b85f420fbc`。
- E2のfresh artifact-only reviewは`ok:true / findings:[]`。half-open probeからfull完了までowner/generation leaseを保持し、lease中の別worker provider call 0、失効後の古いsuccess/failureはstate mutation 0かつ新state byte-identical、stale resultはfailed、SIGKILL後はlease回復、closed-state旧completionもCASでfenceする。legacy全circuit-openはprovider call 0、`rc=75`、`transient_circuit_open`をresumeへ渡す。ledgerは96行・同hashで投稿増分0。
- E3はfeature commit `7b55799e87e1dbadb919fb7b0b7e5846577493f0`へpush済み。旧`skills/article-writer`、legacy finalizer、個別agent、存在しないsymlink記述は0。X Article/X Post/Dev.to canonical publisherは各exact1で、note/Zenn/Substack、quality/safety gate、article contentも新`skills/writer-engine` SSOTへ移動した。
- E3のfresh clone/root installはCodex-only/Claude-onlyともPASS。tracked plistはexact5、file-only installはlaunchctl call 0、`--activate`再実行は旧9 bootout→新5 bootout→新5 bootstrap、kickstart 0、`--uninstall`は新5だけを外してdataを保持する。installed symlinkからhealth/status/migrate-state/plist entrypointを実行し、全suite `103 passed`、fresh review `ok:true / findings:[]`。
- actual legacy stateはrepo外`$HOME/.local/share/writer-engine/archive/legacy-article-writer/25bfbbdee4a079a790c35a1df9d32e63b2ea47aab135a95e19e4bad5db521983`へschema migration済み。source/archive manifest SHA-256は同じ`25bfbbde...1983`、archive 754 entries、writable 0、再実行は`already_migrated`、DB row/receipt exact1。旧ledgerは96行・SHA-256 `856af4bf992bf0624c679a3b75c3fd5141c4fe7046a6cecf819f515fbc3023b0`で不変、publication attempt/receiptは0。
- E4初回builder HEAD `d841c38` は全suite `130 passed`、fixture exact8、fault matrixを通したが、fresh artifact-only reviewは`ok:false`。fixture receiptだけで本番transport/readbackを迂回し、installed環境からmanual live exact8を実行できないため、E4はTODOのままにする。
- E4 fresh reviewのblocking正本は次の10契約: X Post独立生成、note/Zenn/Substack/Xのbuilt-in live transport + engine-owned readback、Dev.to生成artifact変換、run途中のprovider fallback、X Post日跨ぎFIFO、必須exact8集合一致、X 3 form/lang ID一意性、X Article実`published_at`差360〜370分、installed account/secret preflight、production `PLATFORM_FAIL` outbox。
- E4是正のうち、X Post独立writer→judge・最大5→best-safe・durable resumeは`5bf965c`、未公開X Postの翌日FIFO carryとX form/lang identity collision拒否は`5203b16`へpush済み。旧記事冒頭260字流用、後続runの追越し、同一X ID/URL 3枠流用はそれぞれRED fixtureで再現後にGREEN化した。残るtransport/readback/preflight/provider fallback/exact-set/Telegram契約を同じE4内でTDD是正する。
- 既存live部品は旧article-writerに存在するが、新engineのstdin JSON transport/authoritative receiptへ未接続。noteは`publish-note.sh` + `publish-paid.py`、Zennは`zenn-publish/publish-to-zenn.sh`、Substackは`publish-substack-mermaid.sh`、X Articleは`x-publish/publish-to-x.sh`、X Postは既存API/CDP publisherをcopy+tweakし、各platform匿名/API readbackをengine側で統一する。上流X Article skillはdraft-onlyなので、その自己申告をlive evidenceにしない。

### 18.8 Remaining TaskList（唯一の残TODO正本、必ず順番どおり）

| # | 状態 | 作業 | done evidence |
|---|---|---|---|
| E1 | **DONE** | incidentを固定test化。ownerless lock、line 240 `File name too long`、Claude weekly-limit、partial runをbehavioral RED fixtureにし、現run artifactをread-only archive。既live receipt確定後も新規投稿を実行しない | commit `db32520`、`RED_SUITE_CONFIRMED 4/4`、runner/時系列guard 11 PASS、archive 235 files + manifest `2fced19...` + writable 0、既live note/ja exact1、ledger hash不変・投稿増分0、fresh review `ok:true` |
| E2 | **DONE** | native runtime adapterをTDD実装。Codex/Claudeのprobe/run/schema/circuit breakerを統一し、全hardcoded provider callをadapterへ置換 | commit `8bb2aae`、Python 73 + subtests 27、shell 22/22、E2 42 PASS、adapter外直呼び0、実Codex/Luna probe `MODEL_OK`、race/lease/replay/legacy rc75 contract PASS、fresh review `ok:true`、ledger不変・投稿増分0 |
| E3 | **DONE** | TO-BE treeへ段階移行。stateをrepo外へschema migrationし、旧copy/存在しないsymlink記述/legacy finalizer/個別agentを撤去。既存X Articles/Dev.to publisherは新SSOTへ各1実装として移植し、X Post publisher、Telegram outbox、tracked plist 5本、install/uninstallを実装 | commit `7b55799`、fresh root Codex/Claude install、tests 103 PASS、旧path/tree 0、X Article/X Post/Dev.to各exact1、state hash `25bfbbde...1983`・754 entries・writable 0・再実行safe、launchctl新5のみ、fresh review `ok:true`、ledger不変・投稿増分0 |
| E4 | **TODO** | daily MID+X pipelineを実装。固定reader questions、最大5→best-safe、MID exact5 live、X Articlesはrun別ja/enを`published_at`差6h〜6h10m、X Postは日本語exact1/JST日のFIFO 12:00–23:55 slot window、exact8 intent/receipt/reality、draft-only終端0、全stateと同transactionのTelegram outbox、5分resume workerを配線 | crash/429/response-loss/date-slot backlog/late-ready/6時間clock matrix PASS、manual kickstart exact8、X Post/ja ID exact1、英語X Post/reply 0、X Article ja/en ID各exact1、Dev.to live、8 live outputのown-eyes、Telegram event UUID/send receipt |
| E5 | **TODO** | monthly book pipelineを実装。X Postを除くarticle exact7完了済みMID topicの30本inventory、book-writer、全書整合、Pandoc、Zenn Book/Gumroad/Stripe idempotent publishers | 29/30/31 test、X Post障害時も在庫維持、manual monthly kickstart、exact3 live URL、EPUB validation、revenue receipt、Telegram receipt |
| E6 | **TODO** | self-improveを1本化。22:30 metrics、週次Terra/Claude proposal、held-out、7日canary、keep/revert、code self-mutation禁止を実装 | 悪化revert/改善keep fixture、実7日experiment receipt、重複schedule 0 |
| E7 | **TODO** | OSS境界を完成。runtime別setup、config example、browser/account preflight、operations/money docs、license attributionを作成 | clean macOS userでCodex-only install+run、別fresh userでClaude-only install+run、secret/hardcoded home 0 |
| E8 | **TODO** | final fresh E2E。Codex-only daily exact8、Claude-only daily exact8、X Articlesのreadback時刻差6h〜6h10m、X Post ja FIFO 12:00–23:55 date slot exact1/JST日、全媒体live、monthly exact3、翌06:00 schedule、5分resume、Telegram、metrics/weekly jobをartifact-only reviewerが独立確認しspecをDONE同期 | 8 live URL/ID readback、英語X Post/reply 0、draft-only 0、daily ledger exact8、article exact7時点のbook inventory receipt、book ledger exact3、Telegram logical event exact1 + UUID付きat-least-once delivery、launchctl evidence、fresh review `ok:true`、全repo commit+push+clean |
