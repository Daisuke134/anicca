# LayerX Zenn 3部作 digest — Loop Engineering 記事の中心素材

日付: 2026-07-11
目的: Loop Engineering 記事の中心素材: LayerX FDE部 self-improvement 3部作の digest

ソースURL:
- 記事1: https://zenn.dev/layerx/articles/9f25ec86a31730
- 記事2: https://zenn.dev/layerx/articles/b36ceffe6b5e20
- 記事3: https://zenn.dev/layerx/articles/cd04dd1350bac5

---

## 記事3「『なんとなく改善』からの脱却。Langfuseで作る、精度を改善し続けられるAI開発基盤」

著者: yata / LayerX バクラク事業部　日付: 2026-04-09
URL: https://zenn.dev/layerx/articles/cd04dd1350bac5

- **コア主張**: 生成AI機能(バクラク勤怠のAI初期設定=就業規則PDFから有給付与等の設定項目を抽出提案)運用で「プロンプト変更がリリースサイクルに縛られる」「LLM出力の定量評価が難しい」の2課題。Langfuse(Prompts/Tracing/Datasets)で失敗収集→分析→データセット化→改善→CI検証→本番同期の継続改善サイクルを構築。

- **元の2課題**:
  - プロンプト更新がリリースタイミング依存で即修正不可
  - 複数LLMコール組合せで全体ログだけでは各コール個別I/O・レイテンシが見えずボトルネック特定不可

- **Langfuse 3機能**:
  - Prompts: バージョン/ラベル管理、デプロイと切り離し更新
  - Tracing: LLMコール単位でI/O・レイテンシ・コストを階層記録、OpenTelemetryベース、Go公式SDKなく社内で自作
  - Datasets: 精度評価テストケース管理、コール単位で監視改善

- **継続改善サイクル 6step**:
  1. 失敗ケース特定(KARTEアンケートの不満回答をSlack自動投稿 / AI出力と顧客実保存データの差分検出=編集された=期待値未達)
  2. 分析(人間が根本原因、LLM任せは個別最適化の危険)
  3. Datasets追加
  4. 精度改善(Claude Code SkillsのRED-GREEN型ループ: ベースライン評価→失敗パターン分析→戦略的修正(Few-shot/制約再定義/CoT誘導)→改善判定(ベースライン超え+既存成功のデグレなし、最大5回)→結果出力。スコアリングはLLM as a Judgeでなく通常のGoテストコード)
  5. CI自動評価(ローカル=個別改善、CI=全データセットで全体精度担保)
  6. プロンプト同期(環境デプロイ同時にLangfuseバージョンを本番反映)

- **反省点**: TracingのInput形式(system/userメッセージ配列)とDatasetsのInput形式(構造化オブジェクト)が不統一で都度変換の手間。テスト設計段階でフォーマット統一すべきだった。

---

## 記事2「自己改善エージェントはなぜ前提を覆せないのか ― 局所最適とハーネスでの脱出」

著者: 223(堤)　日付: 2026-06-17
URL: https://zenn.dev/layerx/articles/b36ceffe6b5e20

- **コア主張**: AI Workflow自動改善で90%→99%に届かない原因はagent能力不足でなく「単一候補を単一スコアで磨き続ける」ハーネス構造が探索を局所最適に固定していること。解決は探索構造の再設計であってagentを賢くすることではない。

- **アンカリング効果**(Lou&Sun 2412.06593): LLMは最初の要件定義/設計書に探索範囲を固定されやすい。CoT/Reflectionでも緩和不十分。

- **Degeneration-of-Thought**(Liang et al. 2305.19118): 一度自信を持つと自己反省だけでは新発想が出にくい。対策=Multi-Agent Debate(複数agentに異なる立場で議論させ多様な推論経路)。

- **PACEevolve(2601.10657) 3失敗モード**:
  1. Context Pollution=失敗履歴蓄積が次候補生成を偏らせ誤仮説が自己強化
  2. Mode Collapse=既知アイデア活用に偏り新規探索が枯渇
  3. Weak Collaboration=並列探索間の交叉が固定的で別系統成果を活かせない

- **Controlled Self-Evolution/CSE(2601.07348) 3問題**:
  1. Initialization Bias(初期解少数だと悪い領域から抜けられない)
  2. Uncontrolled Stochastic Operations(フィードバックに導かれない当てずっぽうな変更)
  3. Insufficient Experience Utilization(過去教訓が蓄積されない)

- **対処1: 複数候補並行 = GEPA**(Agrawal et al. 2507.19457): 候補プールから複数入力で実行→トレース+Scores Matrix保存→平均でなくParetoで選別(特定入力に強い候補も保持)→Reflective Prompt Mutation+System Aware Mergeで新候補。グローバルベスト1本収束を避ける。

- **対処2: アーカイブ再利用 = DGM**(Zhang et al. 2505.22954): 形式証明ベースの元祖Gödel Machineと異なり実測評価でアーカイブ運用。親選択はスコア比例+子候補数反比例(未探索優先)。SWE-bench 20.0%→50.0%, Polyglot 14.2%→30.7%。
  - 後続 **HGM**(Wang et al. 2510.21614): 「高スコア候補が良い子孫を生むとは限らない(Metaproductivity-Performance Mismatch)」→CMP(Clade Metaproductivity, 子孫成功率で系統の伸びしろ推定)+Thompson samplingで親選択。SWE-bench 56.7%(DGM超), CPU 517時間(DGM比1231時間削減)。

- **対処3: 多様性を評価に含める**:
  - MAP-Elites/Diverse Prompts(Santos et al. 2504.14367): 全体最高1つでなく特徴軸(few-shot数×推論深度など)ごとのチャンピオンを保持する地図。
  - GEA(Weng et al. 2602.04837, Group-Evolving Agents): DGMの木構造をグループ単位に拡張、性能軸+新規性軽量補正で親選択、グループ内でパッチ/ログ/失敗評価共有。SWE-bench 71.0%, Polyglot 88.3%。

- **限界**: Feedback Friction(2506.11930)=正解とエラー箇所を明示し最大10回再挑戦でも理論正答率に届かない、確信度高い誤答ほど抵抗強い。コスト=DGM/HGM数百〜1000時間超CPU、対策=評価サブセット化/早期打ち切り(CAPO racing)。セキュリティ=自由度が上がるとagentが評価データ/スコアリング機構自体を改変するリスク。

---

## 記事1「Agent Skills自動最適化の研究、中身はほぼ深層学習の訓練ループだった」

著者: 223(堤) / LayerX Ai Workforce FDE部　日付: 2026-07-08
URL: https://zenn.dev/layerx/articles/9f25ec86a31730

- **コア主張**: Anthropic公式Agent Skills運用手順(実行→測定→編集→測定)自体が訓練ループの形。各論文はそのループの各パーツ(訓練データ/損失関数/勾配/学習率/過学習監視)をテキストで自動化したもの。「検証信号の設計」だけ未解決。

- **訓練ループ対応表**:
  - モデルの重み = SKILL.md
  - 訓練データ = 実行トラジェクトリ
  - 損失関数 = 検証信号(スコアリング)
  - 勾配と学習率 = テキスト編集と編集量上限
  - 検証データ(過学習監視) = 「厳密改善時のみ採用」ゲート

- **Progressive Disclosure**: ①起動時=全skillのname/descriptionのみ ②使用時=SKILL.md本文 ③必要時のみ参照ファイル。スクリプトは実行結果のみcontextに入る。

- **Anthropic公式5ステップ**: Identify gaps→Create evaluations→Establish baseline→Write minimal instructions→Iterate。「文書を書く前に評価を作る」が核心。

- **Trace2Skill(2603.25158)**: 成功/失敗トラジェクトリ収集→サブエージェント並列パッチ提案→階層マージ。繰り返し現れる編集だけ採用(1回限りは過適合として除外=正則化)。Qwen3.5-35B作成skillがQwen3.5-122B性能を最大+57.65pt改善(WikiTableQuestions)。

- **MIND-Skill(2605.08670)**: 帰納agent(成功例からskill抽象化)+演繹agent(生成skillだけで元トラジェクトリ再現できるか逆検証、再構成損失/結果損失/ルーブリック損失の3種でLLMジャッジ採点、TextGradで最適化)。Qwen3.5-122B-A10Bで平均59.1(ACE 56.1, Trace2Skill 55.1を上回る)。

- **CoEvoSkills(2604.01687)**: skill生成器とSurrogate Verifier(代理検証器)が共進化。正解テストは両者から隔離、返却は合否のみ(oracle採点)。「自分は合格判定なのにテスト落第」の不一致をテストの甘さの証拠として難化。Claude Opus 4.6でpass rate 71.1%(skillなし30.6%, 人手53.5%超え)。

- **OpenSkill(2606.06741)**: 知識収集(検証アンカー=機械的正誤判定できる参照値も取得)→仮想テストで反復改善(最大3ラウンド)→最終評価でのみ隠し正解テスト使用。SkillsBenchでClaude Opus 4.6が43.6%, GPT-5.2が42.1%(自動手法内最良だが人手44.5%/44.8%未到達)。反復劣化: SocialMazeで反復3回82.7%→5回79.9%→10回78.0%(自作検証器Precision約57%と低い為)。

- **SkillOpt(2605.23904)**: モデル重み完全凍結、SKILL.md 1枚だけ学習パラメータ化。実行→診断(optimizer役が編集提案)→候補生成→検証タスクで厳密改善時のみ採用の4step。学習率=編集数上限、スケジューラ=コサイン減衰(序盤大胆・終盤微修正)。Slow/Meta Updateでエポックまたぎ長期方針をskill保護欄に記述しstep単位編集の上書き防止。最適化は訓練フェーズで完結、本番agentは読むだけ。

- **SkillGrad(2605.27760)**: SkillOpt拡張。①更新対象を1ファイルからskillフォルダ全体(メタデータ/本文/参照リソース3層)に拡張しどの層に書くか判断 ②勾配momentum(移動平均で更新方向安定化)のテキスト版として繰り返し失敗パターンを永続メモリに蓄積。

- **SkillRouter(2603.22455, 言及のみ)**: skill 8万件規模でrouting自体が問題、name/description限定表示でpass rate 31〜44pt低下。

- **SWE-Skills-Bench(2603.15401)**: 公開49本のSE向けskillを実GitHubタスク約565件で検証。39本はpass rate向上なし、全体平均+1.2%、明確改善は特化型7本のみ(最大+30%)、3本は最大10%悪化。

- **TextGrad(2406.07496)**。

- **結論**: 「評価問題は誰も汎用解法に成功していない。人間に残された最後の仕事かもしれない」。

---

## 関係性

記事1・2は同一著者223(堤)の姉妹編、記事3は別著者yata(バクラク事業部)の独立実務レポート。時系列 3(04-09)→2(06-17)→1(07-08)。

テーマ発展:
- 記事3 = 改善サイクルの実務基盤(Langfuse)
- 記事2 = 自動化しても局所最適に陥る構造的失敗の分析 + 探索アルゴリズム(GEPA/DGM/HGM/MAP-Elites/GEA)による解決
- 記事1 = 改善対象のSKILL.md自体が深層学習訓練ループと同型というメタ統一視点

共通結論: 3本とも「検証信号/評価の設計という人間の判断が残る本質的ボトルネック」に着地。
- 記事3 = 人間による根本分析
- 記事2 = Feedback Frictionというモデル内在限界
- 記事1 = 評価問題は人間最後の仕事
