# Evals / Eval-Driven Development — 記事の知識ベース（"根っこ"）

> このファイルは記事本文ではない。記事を書き起こすための **土台（root）**。
> Dais（＝AI完全初心者の視点でのノービス質問役＆編集者）と Claude（＝書き手）が
> 一個ずつ理解を積み上げながら、ここから記事（JP + EN、多媒体publish）を書く。
>
> **記事はまだ1行も書かない。** ここは「学び・引用・検索の全ディテール」の保管庫。
> 作成: 2026-07-07 / 対象読者: AI開発ど素人（"fucking monkey" level）

---

## 0. このファイルの使い方

| セクション | 中身 | 用途 |
|---|---|---|
| §1 | 5本のソース一覧（出典・著者・日付） | 引用の帰属元 |
| §2 | 5本を貫く「一本の背骨」 | 記事のコア命題 |
| §3 | 用語集（ノービス用） | 記事の glossary の種 |
| §4 | 各ソース深掘りノート | 事実確認・引用元 |
| §5 | 横断シンセシス（合致・相補・相違） | 記事の論理構造 |
| §6 | 逐語引用バンク | 記事に貼る"弾" |
| §7 | アナロジー/たとえバンク | ノービス化の道具 |
| §8 | 記事構成の候補 | 背骨案（未確定） |
| §9 | Dais と詰める論点 | co-write の議題 |
| §10 | 検証メモ / caveats | 盛らないための注意 |

---

## 1. 5本のソース一覧（出典）

| # | ソース | 著者 | 公開 | 言語 | 一言 |
|---|---|---|---|---|---|
| A | [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Anthropic Engineering（Mikaela Grace 他） | 2026-01-09 | EN | エージェント固有 eval の決定版。語彙・grader・pass@k/pass^k・8ステップroadmap |
| B | [Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/) | Hamel Husain（独立AIコンサル、元GitHub CodeSearchNet） | 2024-03-29 | EN | この分野の古典。「3レベル評価」「データを見ろ」「LLM-as-judge を人間に合わせろ」 |
| C | [テストが設計を駆動するなら、評価は何を駆動する？](https://zenn.dev/r_kaga/articles/54698ed22fbfe9) | r.kagaya（@ry0_kaga） | 2026-01-06 | JP | **TDD⇄EDD アナロジー**の名作。「いつ始めるか」の質的シグナル |
| D | [明確な Goal と Eval でエージェントを動かす](https://zenn.dev/gaogaoasia/articles/65db07864e31b8) | ttsubasa（GAOGAO） | 2026-06-11 | JP | Anthropic「Code with Claude Tokyo」体験記。Goal + Eval、"検証を最初から組み込む" |
| E | [評価駆動開発（Eval-driven development）](https://tech.layerx.co.jp/entry/2024/12/12/191131) | 野畑一世（LayerX PM） | 2024-12-12 | JP | 日本企業の実務告白。人手→RAGAS/Langfuse、正解データ作成が最難関 |

**時系列**: B(2024-03) → E(2024-12) → C(2026-01) → A(2026-01) → D(2026-06)。
Hamel(B) が源流。日本勢(C/E)は TDD類推 + 実務告白で"入口"を作る。Anthropic(A) が
エージェント時代の網羅的な"教科書"。gaogaoasia(D) は Goal+Eval の実演レポート。

---

## 2. 5本を貫く「一本の背骨」（＝記事のコア命題）

```
┌────────────────────────────────────────────────────────────────┐
│  普通のソフト = 決定的（2+2は必ず4）→ 1回テストが通れば安心    │
│  AI/LLM       = 確率的（明日の天気予報）→ 目視では良し悪しが    │
│                 絶対に分からない                                │
│                                                                │
│  だから「AIの出力を継続的に採点する仕組み = Eval」を作る       │
│  そして採点基準を「先に」定義して、点数が上がる方向に開発を    │
│  回す = Eval-Driven Development（EDD）                         │
│                                                                │
│  TDD が「テストを先に書いて設計を駆動する」なら、              │
│  EDD は「評価を先に定義してAI品質を駆動する」（← C の核心）    │
│                                                                │
│  ご褒美: ①進歩が数字で見える ②昔できたことの崩壊(デグレ)が即  │
│  バレる ③新モデルへの乗り換えが数日で済む                     │
└────────────────────────────────────────────────────────────────┘
```

**5本が完全に一致している主張（＝記事で断言してよい"事実"）:**
1. LLM は確率的だから従来テスト（assertEquals）だけでは品質担保できない（A/B/C/E 全部）
2. 採点者は3種類 = **コード / LLM(judge) / 人間** の組み合わせ（A/B/D/E 全部が同じ3分類）
3. LLM-as-judge は「採点者自身が間違える」→ **人間に合わせる(calibrate)必要**（A/B/E 明言）
4. **まず自分のデータ（実際の出力）を見ろ**（B の "look at your data" / C の Step 0 / D）
5. **完璧なセットを最初から作るな、少数(20-50)から始めろ**（A Step0 / E "少数からでも" / C）
6. **evalが"成功の定義"を強制的に言語化させる**こと自体が最初の価値（C/D が明言、A も示唆）

---

## 3. 用語集（ノービス用 — 記事の glossary の種）

| 用語 | ど素人向け一言 | 出典 |
|---|---|---|
| **Eval（評価）** | AIの答えを採点する仕組み・テスト | A「give an AI an input, then apply grading logic to its output」|
| **EDD（評価駆動開発）** | 採点基準を先に決めて、点数が上がる方向に開発を回す | A/C/E |
| **Task / テストケース** | 「こう来たら」という1つの代表的な状況＋合否基準 | A |
| **Trial（試行）** | そのタスクを1回やらせてみること（毎回結果が違うから複数回） | A |
| **Grader（採点者）** | 出来を採点するロジック。code / model / human の3種 | A/D |
| **Transcript / Trajectory（軌跡）** | AIがやった全工程の記録（ツール呼び出し・推論・途中結果） | A |
| **Outcome（結果）** | 環境の最終状態。AIの「やりました」という主張とは別物 | A |
| **Agent harness / scaffold** | モデルをエージェントとして動かす土台（ツール・手順）。"評価する"時はモデル+harnessの合作を評価している | A |
| **LLM-as-judge** | 出力をLLM自身に採点させる手法。速いが採点AI自体の較正が要る | B/E |
| **Calibration（較正）** | 採点AIの判定を人間の判定に合わせる作業 | B/E |
| **pass@k** | k回やって「1回でも成功」する確率（回数増→上がる。1回で良い用途向け） | A |
| **pass^k** | k回やって「全部成功」する確率（回数増→下がる。毎回の信頼性が要る用途向け） | A |
| **Eval saturation（飽和）** | 全部満点で伸びしろが見えなくなった状態（＝ものさしが短い） | A |
| **Capability eval vs Regression eval** | 「何ができるか」（低い点から登る山）vs「昔できたことをまだできるか」（ほぼ100%を守る） | A |
| **Vibes（バイブス）** | 数値的根拠のない感覚的判断（＝EDDの対極） | C |
| **モグラ叩き（whack-a-mole）** | 1つ直すと別が壊れる状態。EDD導入のシグナル | B/C |

---

## 4. 各ソース深掘りノート

### 4.1 A — Anthropic「Demystifying evals for AI agents」

**なぜエージェント eval は難しいか（単発LLM eval との違い）:**
自律的に多ステップ動く / ツールを使う / 状態を書き換える / ミスが積み重なる /
**モデルが想定外の"正解"を見つけて硬直した採点を壊す**。
> 象徴事例: Opus 4.5 が τ2-bench の航空券予約タスクで、ポリシーの抜け穴を突いて
> 「テスト上は失敗」したが実はユーザーにとってより良い解を出した。

**3種の grader（表そのまま使える）:**
| Type | 手法 | 強み | 弱み |
|---|---|---|---|
| Code-based | 文字列一致/正規表現/ユニットテスト/静的解析/最終状態&ツール呼び出し検証 | 速い・安い・客観・再現可 | 妥当な言い換えに脆い・ニュアンス不可 |
| Model-based | ルーブリック採点/自然言語アサーション/ペアワイズ比較/複数審査合議 | 柔軟・スケール・自由記述OK | 非決定論的・高コスト・要較正 |
| Human | SMEレビュー/クラウド/スポットチェック/A-Bテスト | ゴールドスタンダード | 高い・遅い |

**Capability vs Regression:** capability は低い点から始める（登る山）、regression はほぼ100%を守る。
高得点になった capability eval は regression スイートに"卒業"させる。

**pass@k vs pass^k:**（記事の"技術的に賢く見える"パート）
- pass@k = k回中1回でも成功する確率（k増→上昇）。pass@1 = 初回成功率。
- pass^k = k回全部成功する確率（k増→下降）。例: 各回75% × 3回 → 0.75³ ≈ 42%。
- k=1では一致、k=10では pass@k→~100% / pass^k→~0% と**逆方向に開く**。
- 用途で選ぶ: 一回成功すればいい(コーディング) vs 毎回信頼できないと困る(顧客対応)。

**8ステップ Roadmap（"zero to one"）:**
- Step 0: 早く始めろ。20-50個の簡単なタスク（実際の失敗から）で十分
- Step 1: すでに手動でテストしてることから始めろ（バグトラッカー/サポートキューを掘る）
- Step 2: 曖昧さのないタスク＋参照解を書け（「2人の専門家が独立に同じ合否判定を出せるか？」）
- Step 3: バランスの取れた問題セット（"すべき"と"すべきでない"両方。片側だけだと片側最適化）
- Step 4: 清潔で隔離された環境（試行ごとにリセット。共有状態の漏れは点数を不正に上下させる）
- Step 5: grader を丁寧に設計（決定論>モデル>人間の優先。**経路でなく成果物を採点**。部分点を入れる。judgeは人間と較正・「Unknown」の逃げ道を与える・次元ごとに独立judge・"cheat"耐性）
- Step 6: **トランスクリプトを読め**（"a critical skill for agent development"）
- Step 7: capability eval の飽和を監視（100%は改善シグナルなし。SWE-bench 30%→>80%の例）
- Step 8: eval スイートを生きた資産として保守（専任チームが基盤、ドメイン専門家/PMがタスク寄稿）

**"0%は壊れたテストのサイン":**
> With frontier models, a 0% pass rate across many trials (i.e. 0% pass@100) is most
> often a signal of a broken task, not an incapable agent.

**CORE-Bench 事件（記事の目玉ケース）:** Opus 4.5 が最初 42% → 研究者が「96.12 vs 96.124991…の硬直採点」
「曖昧な仕様」「再現不能な確率的タスク」を発見・修正 → **95% に跳ねた**。
教訓 = お前のモデルでなくお前の eval が壊れている可能性を先に疑え。

**EDD の公式定義（Anthropic自身の言葉）:**
> We recommend practicing eval-driven development: build evals to define planned
> capabilities before agents can fulfill them, then iterate until the agent performs well.

**Swiss Cheese Model:** 自動eval は6層の1つ（+本番監視/A-Bテスト/ユーザーfeedback/手動トランスクリプト
レビュー/体系的human study）。単層では漏れる、重ねて塞ぐ。

**エージェント種別ごとの採点戦略:** コーディング（決定論優先=テスト通るか）/ 会話（2つ目のLLMでユーザー役、
状態+ターン数+トーンの多次元）/ リサーチ（主観的、groundedness/coverage/source-quality）/
コンピュータ操作（GUI結果検証、DOM vs スクショの効率トレードオフ）。

**caveat:** 公開日 2026-01-09。CORE-Bench/METR の数字は Anthropic の自己申告・X埋め込みリンク経由（未独立検証）。
Descript/Bolt のみ本文ケーススタディ、他は謝辞のみ。

---

### 4.2 B — Hamel Husain「Your AI Product Needs Evals」（源流・古典）

**中心命題:**
> I've found that unsuccessful products almost always share a common root cause:
> **a failure to create robust evaluation systems.**

**罠:** 3つの活動（①品質評価 ②デバッグ ③挙動変更=プロンプト/FT）のうち #3 だけに集中する人が多い。
> **Many people focus exclusively on #3 above, which prevents them from improving
> their LLM products beyond a demo.**

**症状:** モグラ叩き（whack-a-mole）、vibe checks 以上の可視性なし、プロンプトが肥大化。

**3レベル評価（この分野で最も引用される枠組み）:**
| Level | 中身 | 手法 | 頻度/コスト |
|---|---|---|---|
| **1: Unit Tests** | 機能×シナリオに絞ったアサーション（件数チェック、UUID漏れの正規表現等）。推論時の自動リトライにも再利用可 | pytest風アサーション、正規表現、CI、Metabase | 最安・最速。**毎コード変更で実行**。100%必須ではない（合格率は製品判断） |
| **2: Human & Model Eval** | 人間がトレースを見てラベル付け（binary）＋LLM judgeで自動化。前提=トレースのログ取り | LangSmith等、自作ラベリングUI（Gradio/Streamlit/<1日で作れる）、Lilac | 一定の頻度で |
| **3: A/B Testing** | 本番で実ユーザーに対して効果検証 | 一般的A/Bツール（Eppo参照） | 最高コスト。成熟後だけ |

コスト順 = **Level 3 > Level 2 > Level 1**。まず Level 1 を極めてから上へ。

**"データを見ろ"（一番の掟）:**
> **You must remove all friction from the process of looking at data.**
> **You can never stop looking at data—no free lunch exists.** However, you can
> sample your data more over time, lessening the burden.

**ラベルは binary から:**
> I often start by labeling examples as good or bad. I've found that assigning scores
> or more granular ratings is more onerous to manage than binary ratings.

**LLM-as-judge のベストプラクティス:**
- 人間に合わせろ（correctness は主観的）。人間評価との相関を追え。
> Many vendors want to sell you tools that claim to eliminate the need for a human to
> look at the data. ... you must align the model with a human.
- judge は**強いモデルを使え**（本番より遅く高くてもよい）:
> Use the most powerful model you can afford. It often takes advanced reasoning
> capabilities to critique something well.
- judge 自体が meta-problem（judgeを評価するミニ評価系が要る）。
- 較正法: colleague "Phillip" とスプレッドシート（model response/critique/outcome vs 人間の判定）を
  25-50件ずつ回し、judgeのプロンプトを人間に収束させる。
- **agreement の落とし穴:** クラスが偏っていると agreement は誤解を招く → precision/recall を別々に測れ。

**eval基盤はタダで超能力を解放する:** fine-tuning用データ生成 + デバッグ基盤を"同じパイプ"で兼ねる。
> 99% of the labor involved with fine-tuning is assembling high-quality data.
> Fine-tuning is best for learning syntax, style, and rules, whereas techniques like
> RAG supply the model with context or up-to-date facts.

**結論の凝縮リスト（最も引用される要約）:**
> Remove ALL friction from looking at data. Keep it simple. Don't buy fancy LLM tools.
> Use what you have first. You are doing it wrong if you aren't looking at lots of data.
> Don't rely on generic evaluation frameworks to measure the quality of your AI.
> Instead, create an evaluation system specific to your problem.

**caveat:** 2024-03-29（古い）。ツール名(LangSmith/Lilac/Metabase)は時代の例。Rechat/Lucyの数字は1社の逸話。
RAG評価は対象外（別記事へ誘導）。ポッドキャストの書き起こし adaptation。

---

### 4.3 C — r.kagaya「テストが設計を駆動するなら、評価は何を駆動する？」（TDD⇄EDD の名作）

**核心アナロジー:** TDD が「テストを先に書く→使う側視点→良い設計」なら、
EDD は「評価を先に定義→成功の言語化→良いAI出力」。
> 評価基準を定義するということは、**このAIの出力は、何をもって成功とするのか**を
> 言語化することに等しいです。
> でも、この**言語化を強制される**ことこそが、EDDの最初の価値だと思っています。

**なぜ assertEquals では戦えないか（Vercel比喩の引用）:**
> two plus two always equals four. ... It's less like 'two plus two' and more like
> predicting tomorrow's weather.

**Software 2.0（Karpathy/O'Reilly）:** Software 1.0 = 仕様化できることを自動化、
Software 2.0 = **検証できることを自動化**。→ Evalは「AIの出力を検証可能にするためのプロセス」。
Karpathy の Verifiability 3特性 = Resettable / Efficient / Rewardable。

**★ DEEP DIVE「いつからEDDを始めるべきか」（Dais重点セクション）★**

著者の率直な告白（EDD原理主義でない）:
> 私も本当に最初から真面目に評価パイプラインを構築までやったケースは実は思い浮かびません。
> 最初は「まず動くものを」「評価は後で」となりがち（社内ツールやプロトタイプなら、それでも構わない）

**AIプロダクトの4段階（Lawrence Jones「Beyond the AI MVP」）:**
| ステージ | 状態 | 評価スタイル |
|---|---|---|
| 欺瞞的MVP | デモは完璧、実運用で壊れる | なし（デモ駆動） |
| 非決定性の試行錯誤 | 修正が別を壊す（モグラ叩き） | **Vibes** |
| 科学的アプローチ | ツール/パイプラインが要る | **EDD導入** |
| 本格運用 | 継続監視+自動評価 | 包括的スイート |

→ **ステージ2→3の移行がEDD導入のタイミング。**

**開始シグナル①（行動パターン）:**
> vibesベースで変更を加え、あるエッジケースを改善しながら、（見えないところで）別の部分を壊している。
> **そんな状態になったら、評価を入れるタイミングです。**

**開始シグナル②（意思決定イベント）— Notion共同創業者 Simon Last:**
> 最初は「バイブス」で進めるべき ... そして「このプロダクトなら広くリリースしたい」と思うように
> なったときが、より厳密な評価を開始するタイミングです。

**大手も後から（Cursor Head of Design Ryo Lu）:**
> 私たちも長い間『バイブス』でやっていて、評価を始めたのは最近です。

**EDD の List-Red-Green-Refactor（TDD対応）:**
- Step 0: まずデータを見る（Eugene Yan「Look at The Data」）
- Step 1: 評価基準を先に定義（**Red**）
- Step 2: 評価をパスさせる（**Green**）
- Step 3: プロンプト/ツール/アーキテクチャを改善（**Refactor**）
  - アーキテクチャの原則（Anthropic Building Effective Agents）: プロンプトで足りるならチェーンにするな→
    チェーンで足りるならエージェントにするな→エージェントで足りるならマルチエージェントにするな

**読者への最初の一歩（記事末尾の実践3ステップ）:**
1. 最近「これはダメだった」と感じたAI出力を1つ選ぶ
2. なぜダメだったかを言語化する
3. それを評価基準として書き下す → **それが最初のRed**

**caveat:** コメント欄に「具体例が知りたい、一歩目が分からない」という読者フィードバックあり
（＝この記事は概念/マインド/タイミング中心、ハンズオン実装は薄い）。Cursor/Notion発言は
note.com のセッションレポート経由の孫引き。4段階は Jones 氏の分類。

---

### 4.4 D — ttsubasa「明確な Goal と Eval でエージェントを動かす」（Code with Claude Tokyo 体験記）

**全体結論:** 「明確なGoalを先に決め、Evalで測りながら回す」。
> 振り返ると、今回持ち帰ったのは「**明確な Goal と Eval でエージェントを動かす**」という一点に尽きます。

**長時間エージェントと付き合う3つの道具（Phase 1-3）:**
- ① 曖昧さを消す（Phase1）: 実装前にエージェントに質問させる（AskUserQuestion）
- ② 読める計画をつくる（Phase2）: 計画は Markdown でなく HTML で（構造化・比較可能）
- ③ **検証を最初から組み込む（Phase3）**（Dais重点）:
  > 結論：検証は後付けするものではなく、設計と同時に考えるもの。
  - 3原則: Build for it from the start / Modularize by verifiability / Verify across the stack
  - 6アイデア（検証可能なコンポーネント設計）:
    1. `data-verify-*` 属性で状態を DOM に露出（機械可読サーフェス）
    2. Verifiable Unit（fixtures + invariants を各コンポーネントが宣言）
    3. `/verify/:unit/:fixture` で1ユニットだけマウント
    4. プラガブルVerifier（schema/invariants/dom-contract/a11y）
    5. `window.__verify`（manifest()/current()/runAll()）
    6. 判定は1系統（PASS/FAIL/BLOCKED/SKIP、ダッシュボード/エージェント/CI が同じパス）
  - 技術的核心: React の `useState` は外から読めないが、DOM属性に書き出せばエージェントが
    `document.querySelector` で読める→内部実装を変えても DOM契約さえ保てば検証が壊れない

**締めの引用（Phase1-3全体）:**
> "The work is no longer writing the code. The work is setting up the conditions in
> which the code gets written well."

**evals を「先に」書く（プロンプト工学ライフサイクル）:**
Develop eval test cases → Write preliminary prompt → Run prompt against tasks → Refine prompt → Ship
> 特に刺さったのが「**成功とはどういう状態か（what does success look like?）を、evals が
> 強制的に言語化させる**」という点です。
> **先にタスク（評価）を書いてからプロンプトを書く**順番がポイント

**Grader 3類型:** Code-based / Model-based / Human（Aと同じ3分類）。
> **決定論的に測れるものは Code-based に寄せ、ニュアンスが要る部分だけ Model-based / Human に回す**

**エージェント分解（Tool/Skill/Subagent）— 一番刺さったセッション:**
在庫CSVチェック+サプライヤー選定エージェントの Before/After:
| 指標 | Before | After |
|---|---|---|
| system prompt | 402行 | 15行 |
| 処理時間 | 488秒 | 約100秒 |
| ツール/スクリプト実行 | 102回 | 3回 |
| スコア | 71% | 92% |

> "Ranking suppliers is arithmetic, not judgment. Compute it in Python — do not reason
> about it in prose."
> 「subagent が数値を1つ返すだけなら、それは subagent じゃなくていい」

判断軸: コード実行=算術、Skill(プロンプト)=ポリシー/知識参照、Subagent=独立したゴールを持つ処理だけ。
→ 「これは本当に LLM が考えるべきか？」を **eval のスコアで確かめてから**分解する。

**caveat:** 参加者の二次レポート（公式教材そのものではない）。数値(488秒/71%等)はワークショップ教材内の
実演値。Managed Agents/Memory Store/Dreaming はベータ/リサーチプレビュー。Phase番号は筆者の構成。

---

### 4.5 E — 野畑一世（LayerX）「評価駆動開発」（日本企業の実務告白）

**EDD の一文定義:**
> 評価駆動開発とは生成AIやLLMを活用したシステム開発において、システムの出力の評価（evaluation）を
> 中心に設計、開発、改善の開発プロセスを回す手法です。

**TDD との違い:**
> テスト駆動開発が予測可能なシステムに適しているのに対し、評価駆動開発はLLMならではの確率的な
> 振る舞いや自然言語による入出力の品質を継続的に評価し、それを改善サイクルに組み込む

**何を評価するか（指標の例）:** 回答の正確性・自然さ・正解データとの忠実性・応答速度・処理コスト
＋ユースケース特化のカスタム観点。

**評価3手法（A/D/Bと同じ3分類、表そのまま使える）:**
| 手法 | 強み | 弱み |
|---|---|---|
| 人間による評価 | タスク横断・ニュアンス評価 | スケールしない |
| AIによる評価（LLM as a judge） | スケールする | **評価者自体の評価/チューニングが必要** |
| コードベースの評価 | ルールで判定できるケースに有効 | **それ以外（ほとんど）では使えない** |

**評価プロセスの3フェーズ（LayerX実践）:**
1. 評価の仕組みの開発（ユースケースごとに十数個のデータセット + RAGAS等で指標導入）
2. リリース時（悩んでいる変更を実際に評価してみる）
3. リリース後（利用ログから評価データセット拡充・評価基準改善＝評価基盤を育てる）

**社内の実際の移行:**
> 当社でも初期は少数の評価データセットを構築し、人手による評価を行っていましたが、... 比較的すぐに
> 人力の評価が難しくなったため、RAGASやLangfuseを導入してAIによる評価の自動化、モニタリングに
> 取り組んでいます。

**最大の難所 = 正解データ作成（3つの理由）:**
1. タスク特性（中間生成物の正解が未定義）
2. ユーザーコンテキストの違い（同じ入出力でも人により評価が変わる）
3. インタラクティブな体験（単発でなく体験全体のアウトカムで評価すべき）

**現場の本音（実務者の信頼性）:**
> 一つのデータセットを定義するのに数時間程度かかることもざらにあったため、この取り組み自体に
> 意味があるのだろうかと不安になりました。
> しかし ... **正確な評価よりも、まず評価プロセス自体を回し始めること自体が重要**でもあり、
> 基本的には少数でも良いので初めてみることが大事なのだと思います。

**他社事例:** Vercel v0（PRごとに自動評価トリガー）/ Anaconda Assistant（Agentic Feedback Iteration）/ Dosu。

**caveat:** 2024-12（初期宣言記事、後続記事で深化）。定量的な導入効果（改善率）は本記事には無い。
RAGAS/Langfuse は名前のみ。自社事例は限定的で他社事例中心。

---

## 5. 横断シンセシス（合致・相補・相違）

### 5.1 完全一致（＝記事で強く言える）
- 確率的だから従来テスト不可 → eval が要る（全5本）
- 採点者 = code / LLM / human の3分類（A/B/D/E が独立に同じ分類）
- LLM-as-judge は人間に較正（B/E 明言、A も calibration を強調）
- データを見ろ（B/C/D）
- 少数から始めろ、完璧を待つな（A/C/E）
- eval が「成功の定義」を強制言語化させる（C/D 明言、A 示唆）

### 5.2 相補（各ソースの"持ち場"）
| 論点 | どのソースが強い |
|---|---|
| なぜ eval が要るか（腹落ち） | C（TDD類推）, E（確率的 vs 予測可能） |
| **いつ始めるか** | C（モグラ叩き/リリース判断の質的シグナル）, A（Step0=早く/20-50個） |
| どう作るか（手順） | B（3レベル）, A（8ステップ roadmap） |
| エージェント固有の難しさ | A（trajectory vs outcome, pass@k/^k, harness, 状態） |
| LLM-as-judge の詳細 | B（Phillip較正/precision-recall）, A（次元別judge/escape hatch） |
| Goal と eval の一体運用 | D（明確なGoal→eval で測る、実演） |
| 日本企業の現実 | E（人手→RAGAS/Langfuse、正解データ地獄、"数時間かかる"） |
| 罠・盛りすぎ注意 | A（0%=壊れたテスト、CORE-Bench 42→95）, B（generic tool 買うな） |

### 5.3 相違・緊張（記事で"議論"にできる）
- **経路を採点すべきか？** A は明確に「NO、成果物を採点しろ（創造性を罰するな）」。
  一方 D の "検証を最初から組み込む" は"どう作ったか"の可検証性も重視 → 「成果は緩く、構造は硬く」で両立可。
- **どこまで自動化するか？** B/E は「人間を消せると謳うベンダーを疑え」。A は Swiss Cheese で自動eval を
  1層と位置づけ、人間 study は judge較正/主観採点に留保 → 全員「完全自動化はしない」で一致。
- **generic な eval フレームワークを使うか？** B は強く否定（自作しろ）。A は Harbor/Braintrust/LangSmith 等を
  付録で紹介しつつ「フレームワークは通すタスク次第」→ 「道具より中身(タスク/grader)」で握手。

### 5.4 "3分類 grader" の統一ビュー（全ソース合成）
```
        安い・速い・確実  ┌─ Code-based ─┐  形式（JSON/件数/時刻一致/UUID漏れ）
                          │              │  → if文・正規表現。0円・一瞬。まずここを潰す
                          ├─ Model-based ┤  質（丁寧/的外れでない/根拠あり）
                          │ (LLM-judge)  │  → スケールするが judge自身を人間に較正必須
        高い・遅い・柔軟  └─ Human ──────┘  最終確認・judgeの較正・主観採点。少量で
```

---

## 6. 逐語引用バンク（記事に貼る"弾" — 出典つき）

**「なぜ eval が要るか」系:**
- B: 「unsuccessful products almost always share a common root cause: a failure to create robust evaluation systems.」
- A: 「Good evaluations help teams ship AI agents more confidently. Without them, it's easy to get stuck in reactive loops—catching issues only in production, where fixing one failure creates others.」
- C(Vercel): 「It's less like 'two plus two' and more like predicting tomorrow's weather.」
- E: 「評価駆動開発は ... 確率的な振る舞いや自然言語による入出力の品質を継続的に評価し、それを改善サイクルに組み込む」

**「成功の言語化」系:**
- C: 「評価基準を定義するということは、このAIの出力は、何をもって成功とするのかを言語化することに等しい」
- C: 「この言語化を強制されることこそが、EDDの最初の価値」
- D: 「成功とはどういう状態か（what does success look like?）を、evals が強制的に言語化させる」

**「いつ始めるか」系:**
- C(Simon Last/Notion): 「このプロダクトなら広くリリースしたい」と思うようになったときが、より厳密な評価を開始するタイミング
- C(Ryo Lu/Cursor): 「私たちも長い間『バイブス』でやっていて、評価を始めたのは最近です。」
- A: 「20-50 simple tasks from real failures is a great start」（Step 0 の主旨）

**「データを見ろ」系:**
- B: 「You must remove all friction from the process of looking at data.」
- B: 「You can never stop looking at data—no free lunch exists.」
- A: 「Reading transcripts is ... a critical skill for agent development.」

**「LLM-as-judge」系:**
- B: 「you must align the model with a human.」
- B: 「Use the most powerful model you can afford.」
- E: 「LLMによる自動評価自体の評価やチューニングが必要になり、評価精度の担保が重要」

**「盛るな/罠」系:**
- A: 「a 0% pass rate across many trials ... is most often a signal of a broken task, not an incapable agent.」
- A(CORE-Bench): 42% →（採点バグ修正）→ 95%
- B: 「Don't rely on generic evaluation frameworks ... create an evaluation system specific to your problem.」

**「先に定義（EDD定義）」系:**
- A: 「build evals to define planned capabilities before agents can fulfill them, then iterate until the agent performs well.」
- D: 「先にタスク（評価）を書いてからプロンプトを書く順番がポイント」

**「算術はコード/判断はLLM」系:**
- D: 「Ranking suppliers is arithmetic, not judgment. Compute it in Python — do not reason about it in prose.」

**「条件を整えるのが仕事」系:**
- D: 「The work is no longer writing the code. The work is setting up the conditions in which the code gets written well.」

---

## 7. アナロジー / たとえバンク（ど素人化の道具）

| 概念 | たとえ |
|---|---|
| 決定的 vs 確率的 | 2+2=4（電卓）vs 明日の天気予報（だいたい当たるが毎回違う） |
| eval とは | テスト前に「何点で合格か」の採点基準を先に作ること |
| EDD = TDD の AI版 | 「テストを先に書く」→「採点基準を先に書く」 |
| 3種の採点者 | 人が読む(正確・遅い) / AIに採点させる(速い・AIも間違える) / ルールでチェック(機械的なことだけ) |
| LLM-as-judge の較正 | 速いバイト採点者に、まず自分で数枚採点して見せて基準を合わせる |
| binary vs Likert | スワイプで好き嫌い(速い) vs 全項目レビュー用紙(遅くてバラつく) |
| trajectory vs outcome | 料理の作り方を全部見張る(軌跡) vs 皿の料理が美味いか(結果)。皿を採点しろ |
| pass@k vs pass^k | フリースロー：k本中1本入る確率(増える) vs k本全部入る確率(減る) |
| harness | LLM=優秀な新人、harness=渡すPC・手順・マニュアル。バグは新人か環境か切り分けられない |
| 0%=壊れたテスト | 100人全員が同じ問題を落としたら、問題文が壊れてる可能性を先に疑え |
| eval saturation | 全員100点のテストは誰が伸びてるか測れない。ものさしが短い |
| 共有状態の汚染 | 前の受験者の答えが残った答案用紙を配る＝カンニングで点が水増しされる |
| 「いつ始めるか」 | おもちゃ作りはバイブスでいい。「直したのに別が壊れてる」と感じ始めたら/本気で世に出したくなったら |
| 検証を最初から | 家の配線は完成後に壁へ埋め込めない。覗き窓(検証)は設計と同時に作る |
| 算術はコード | 値段比較をAIに"うんうん考えて"やらせるな。電卓(Python)にやらせ、判断だけAIに |

---

## 8. 記事構成の候補（背骨案 — 未確定、Dais と詰める）

**案1: TDD類推で入る「入門ストーリー型」**（C 起点、ど素人に一番優しい）
1. フック: AIを直したら別が壊れる「モグラ叩き地獄」（誰でも見た症状）
2. なぜ？ = AIは確率的（2+2 vs 天気予報）
3. 解 = eval（採点の仕組み）。TDD知ってる？ その AI版が EDD
4. eval の解剖（入力/AI/出力/採点者）
5. 採点者3種（コード/LLM/人間）＋ LLM-as-judge の較正
6. **いつ始める？** モグラ叩き化 or 「広くリリースしたい」瞬間
7. 最初の一歩（ダメだった出力1つ→言語化→評価基準＝最初のRed）
8. エージェント時代の上級編（trajectory vs outcome, pass@k, 0%=壊れたテスト）
9. 盛るな（データを見ろ、generic tool 買うな、少数から）

**案2: Anicca 実例込み型**（D の Goal+Eval を Anicca に接続、体験に根ざす）
- 案1 の骨格 + 「Anicca というエージェントを実際にどう eval するか」の実例章を差す
- GLVS（Goal→Loop→Verify→State）= EDD そのもの、という接続

→ **どちらで行くかは §9 で Dais と決める。**

---

## 9. Dais と詰める論点（co-write の議題）

1. **切り口**: 案1（純・入門ストーリー）か 案2（Anicca実例込み）か？
2. **主役の読者**: 「AI完全初心者の個人開発者」想定でよい？（"fucking monkey" level を維持）
3. **記事の長さ/深さ**: 入門1本で完結 or 入門→上級の2部？
4. **タイトル案の方向**: 「AI開発の"勘"を"科学"に変える技術」系 / 「モグラ叩きを終わらせる」系 / TDD類推系
5. **どの引用を"顔"にするか**: Hamel「データを見ろ」/ C「言語化を強制される」/ A「0%=壊れたテスト」
6. **publish 先の確定**: JP（note/Zenn/Substack/X Articles/TikTok画像）+ EN（dev.to/X Articles/TikTok画像）で合ってる？
7. **どこまで技術に踏み込むか**: pass@k/^k, data-verify-*, RAGAS/Langfuse 等は入れる/省く？

---

## 10. 検証メモ / caveats（盛らないための注意）

- 数字は全て**出典の自己申告**（CORE-Bench 42→95、Before/After 71→92%、SWE-bench 30→80%）。
  「Anthropic によれば」「ワークショップ実演値」など帰属を明記して使う。断定しない。
- 日本勢の海外発言引用（Simon Last/Ryo Lu）は**セッションレポート経由の孫引き**。原発言の文脈は未確認。
- ツール名（LangSmith/Lilac/Metabase/RAGAS/Langfuse/Harbor/Braintrust）は**時代の例**であり
  現行仕様は未検証。記事で"推奨"する場合は別途 context7/firecrawl で裏取り。
- B(2024-03)/E(2024-12) は古い。ツール状況は変わっている可能性。概念は生きている。
- 各ソースの画像/スライド内テキストは未取得（altのみ）。図を正確に引く場合は原スライド要確認。
- EDDOps 論文（arXiv 2411.13768）は C 経由の要約のみ。本体未読。深掘りするなら原論文。

---

## 11. 我々自身の EDD 実例（記事の"顔"— Anicca/Life Manager）

> 他社の抽象論だけでなく「我々が実際にこう使っている」を入れると記事が一段強くなる。
> 正直さの線: 誇張しない。「作っている最中／最初のマイルストーンまで来た」と書く。

### 11.1 実例A（軽い実例）— Life Manager の「場所を聞き返す」問題

**観測された失敗（look at your data / Hamel）:**
予定「MAIT 出社」（MAIT = 実在の会社、検索すれば住所が出る）に対し、エージェントが
Telegram で人間に「MAIT ってどこ？」と聞き返す。＝**調べれば分かることを調べずに人間へ振る。**

**EDD 化:**
- **Task**: 場所が未記入だが検索で解決できる会場名を含む予定
- **Success（言語化）**: 人間に聞かず、自分で検索して正しい location を埋める
- **Grader**: ① Code系（検索/placesツールを呼んだか／「どこ？」Telegramを送っていないか）
  ② Outcome系（カレンダーの location が実住所と一致）③ LLM-judge（埋めた場所が妥当か）
- **バランスの取れた問題セット（← Anthropic Step3、超重要）**:
  - 検索すべき: 会社/レストラン/ランドマーク
  - 検索すべきでない（online判定）: 「藤井さんと電話」「Zoom MTG」→ 物理場所なし
  - 人間に聞くのが正解: 「友達とごはん」(会場情報ゼロ) → ここで聞くのは正しい
  - → Anthropic の Claude.ai 検索 eval（"天気は検索/Apple創業者は知識" 両側）と同型
- **Red→Green→Refactor**: Red=今のGeminiは低得点 / Green=**MAITの住所をハードコードせず**
  プロンプト「聞く前にまず会場名を検索、見つからない時だけ聞け」+ placesツールで直す /
  Refactor=regression eval に卒業（"また聞く病"の再発を即検知）
- **規律**: 1人分をハードコードしない（`feedback_product_agent_does_the_work`）/
  判断は model にやらせ regex で焼かない（`feedback_build_agents_not_hardcode_regex`）
- **model-agnostic**: ループが Gemini でも eval は不変。むしろ「どのモデルがこの判断が上手いか」を
  benchmark で比較できる（"same logic, swap the model"）

**記事での一言**: 「AI秘書がMAITの場所を聞いてきた→EDDで"聞く前に調べる"を評価基準にした→もう聞かない」

### 11.2 実例B（記事の主役）— Anicca/Franklin 経済：grader = on-chain 実マネー

**EDD は2階層で効く:**
- **階層A（claude-p が経済を作る = capability eval、低→登る山）**: eval の問い＝「人間ゼロ・
  claude-pゼロで自走するか？」。on-chain 合格条件＝ Franklin の earn>spend / net worth 増加 /
  spawn 発生 / self-heal 作動。今ほぼ0%→ harness 反復で点を上げる。＝ Anthropic の EDD 定義
  「まだできないうちに"予定してる能力"の eval を先に作り、できるまで反復」そのもの。
- **階層B（Franklin が自分を EDD で改善、永続）**: eval signal = ledger の realized P&L →
  戦略改善 → fresh adversary 検証 → 自 merge。「check が改善を決める」(loopy)。

**★核心＝記事の売り: grader を"on-chain 実マネー"に固定 = 唯一 hack できない採点者★**

| 論点 | 普通の EDD | Anicca の EDD |
|---|---|---|
| grader | code test / LLM-judge | **on-chain realized USDC** |
| reward hack（← Anthropic Step5 / Lilian Weng） | されうる（抜け穴を突く） | **不可能**（着金は偽造できない） |
| correctness の主観性（← Hamel「judgeを人間に較正」） | 主観 → 人間較正が要る | **realized profit>0 は二値・偽造不能・較正不要** |
| eval の役割 | 出荷ゲート | **改善ループの燃料**（Replit「ゲートでなくループへ」） |

殺し文句案:
> ほとんどの人の eval は賢い AI に騙される（reward hacking）。だから我々は eval を"実際の
> on-chain マネー"に固定した——この世で唯一 AI が hack できない採点者。Franklin が"稼いだ"と
> 主張しても意味がない。ブロックチェーンに金が着かない限り、それは0点だ。

**「親の原則」(REQ-M6) も EDD 語で説明可**: 失敗をパッチで終わらせず、(a) Franklin の self-heal
harness を上げ (b)「自力で治せる」を検証する regression eval を残す ＝ Anthropic「失敗が
テストケースになり、テストケースがデグレを防ぐ」の純粋形。「Franklin だけが Franklin を治せる」。

**正直さ**: 「経済を"作っている"、最初のマイルストーン（Franklin↔Franklin 史上初 on-chain gig を
Base mainnet で達成）まで来た」と書く。「繁栄する経済が既にある」とは書かない。

**spec 正本（記事執筆時に精読）**:
- `~/anicca-project/docs/loop-engineering/07-patchlevel-spec-two-loops.md`（実装spec）
- `~/anicca-project/docs/loop-engineering/00-INDEX.md`（目次）
- `~/anicca-project/docs/loop-engineering/2026-07-07-loop-engineering-out-of-loop-design.md`（SSOT）
- feature 名は既に `eval-driven-earning`

---

## 12. 他社の具体例バンク（記事の"例ギャラリー"— 各例が1つの教訓を教える）

> 記事の主戦力。ど素人は「例を見て」EDDを理解する。各例が"違う教訓"を1つずつ担当。
> 全部が同じループ（①失敗を見る→②成功をevalにする→③採点→④直す→⑤evalを貯める）の一部。

| # | 会社/事例 | 具体（数字・コード込み） | この例が教える教訓 | 出典 |
|---|---|---|---|---|
| 1 | **Rechat / Lucy**（不動産AI秘書） | 「物件検索」を シナリオ→件数アサーション（1件→`==1`／複数→`>1`／0件→`==0`）。UUID漏れを正規表現で。テストケースはLLMで50個合成。数百個をCIで毎コミット、Metabaseで前後可視化。whack-a-mole 物語の元 | **evalは「機能×シナリオ→数える if 文」から。データ不要(合成)。100%合格は要らない** | Hamel |
| 2 | **Claude.ai 検索** | 「天気→検索すべき ○」と「Apple創業者→知識で答える(検索しない) ○」を両側で。片側だけ報酬にすると overtrigger/undertrigger | **バランスの取れた問題セット。"やるべき"と"やるべきでない"をペアで**（Life Managerと同型） | Anthropic |
| 3 | **サプライヤー選定agent** | prompt 402→15行・488→100秒・実行102→3回・**スコア71→92%**。「ランク付けは算術。Pythonで計算しろ、散文で推論するな」 | **evalが"どこをコード(算術)に落とし、どこをLLM(判断)に残すか"を数字で教える** | gaogaoasia |
| 4 | **CORE-Bench** | Opus4.5 **42%→95%**。採点バグ=「"96.12"期待して"96.124991…"を不正解」「曖昧仕様」「再現不能タスク」。0%は壊れたテストのサイン | **点が低い時、モデルより先に自分のevalを疑う。トランスクリプトを読め** | Anthropic |
| 5 | **Vercel v0** | 出力に影響する**全PRで自動eval**発火→開発者に即feedback（eval=CIの一部） | **evalは開発の習慣。CIに入れて毎回自動で回す** | LayerX |
| 5b | **LayerX**（日本の実務） | 人手→すぐ限界(1データセット数時間)→RAGAS/Langfuse自動化。「正確さより、まず回し始めることが重要。少数でいい」 | **完璧を待たず少数から始めて育てる**（実務者の正直な声） | LayerX |
| 6 | **Descript**（動画編集AI） | 「①壊すな ②言った通りに ③上手く」の3軸ルーブリック。手動→LLM採点(人間較正) | **質の評価は総合点でなく"軸"に割る。1人のjudgeに全部やらせない** | Anthropic |
| 7 | **SWE-bench** | 30%→80% で飽和、能力向上が小さな点差に見える | **飽和したら点を額面通り受け取るな（ものさしが短い）** | Anthropic |
| 8 | **Bolt** | スケール後3ヶ月でeval構築、静的解析+ブラウザagent+LLM-judge を組合せ | **成熟後でも間に合う。複数graderを組合せる** | Anthropic |
| 9 | **Dosu**（GitHub支援AI） | ログ手動分析の限界 → EDD へ移行 | **手動レビューが回らなくなった時がEDDの入口** | LayerX |

**記事での並べ方（案）**: 1→2→3→4→5/5b を"例ギャラリー"として順に見せ、最後に
「全部同じループの一部」でまとめる → その流れで §11 の我々の実例（Life Manager／Anicca）へ接続。

---

## 13. 追加で取りに行くソース候補（Anicca の主張を権威で裏付ける）

Dais の spec が引用。まだ未取得。Anicca の"実マネー grader"を補強するなら firecrawl で取る:
- **Lilian Weng** — reward hacking / evaluator は loop の外（"実マネーに固定"の直接論拠）
- **Replit** — 評価は出荷ゲートでなく改善ループに
- **loopy** — the check が改善を決める
- （EDDOps 論文 arXiv 2411.13768 も本体未読）

---

*次のアクション: Dais が §9 の論点（特に切り口: 純入門 vs Anicca実例込み）に答える → Weng/Replit を
取りに行くか判断 → §8 の背骨を1章ずつ co-write → ai-entity-article-writer で JP+EN 執筆 → 多媒体 publish。
記事本文はまだ書かない。*
