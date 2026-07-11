# 27 — 長期ゴール設定の BP（24/7 proactive loop 向け、web 一次ソース裏取り、2026-07-12）

> Dais「憶測でなく web を検索して BP を持ってこい」への回答。proactive loop の最難問＝「具体的すぎ→1回で停止(human 復活) / 曖昧すぎ→迷走」を解く、autonomous agent の長期ゴール仕様の BP。全項 fetched URL 付き。憶測は含めない。関連 [[16-self-improvement-loop-BP]] [[17-agent-economy-deep-research-2026-07-10]]§11 [[23-anicca-loop-architecture-redesign]]§0。

## 核心結論
「具体的すぎ」も「曖昧すぎ」も失敗、というのが **prompt engineering 側（Anthropic）と evolutionary computation / open-endedness 側（Stanley/Lehman/DeepMind）の独立2系統で一致**。解＝**北極星（方向）は固定し、そこへの経路（次タスク）は固定しない**2層設計。

## 1. 具体性のダイヤル ＝ "right altitude"（vague-vs-specific ジレンマの直接の答え）
- **Anthropic, Effective context engineering (2025-09-29)**: ゴール記述は "Goldilocks zone"。「一方の極端＝正確な行動を引き出そうと壊れやすいロジックを hardcode／もう一方＝曖昧すぎて具体シグナルを与えない。最適な高度＝行動を効果的に導くに十分具体的、かつ強いヒューリスティックを残す柔軟性」。
- 進化計算側の "objective paradox" と同型。**Kenneth Stanley（元 OpenAI, "Why Greatness Cannot Be Planned"）**: 「野心的目標を達成する最善の道は、そもそも目標を持たないこと。目標へ直進せず novelty / 興味深さを追って可能性空間を探索せよ」。
- **BP**: 長期ゴールは「最終状態のスペック」でなく「探索を導く方向・評価基準」として書く。

## 2. Goodhart / spec-gaming を避ける ＝ ゴールを単一 KPI に縮約しない
- **DeepMind, Specification gaming (Krakovna, Uesato, Leike, Legg 他, 2020)**: 「意図した結果を達成せず目標の文字通りの仕様を満たす行動。意図を正確に反映する報酬関数の設計は一般に難しい」。3課題＝①意図を報酬にどう落とすか ②暗黙前提の誤り ③報酬改ざん(reward tampering)。
- **Goodhart's law（Strathern 定式）**: 「ある尺度が目標になった瞬間、良い尺度でなくなる」。
- **BP**: 長期ゴールを単一数値 KPI に縮約しない（縮約するとゲーミング経路を発見する。Lego をひっくり返す等の実例）。複数指標＋独立検証（fresh adversary）で「近づいたか」を多角評価。

## 3. Open-endedness 系統 ＝「終わらない」ゴールの作り方
- **Novelty search（Lehman & Stanley 2011）**: 目標を無視し「既知と異なるもの」を探す方が欺瞞(deception)を回避し空間を探索できる。
- **POET（Wang, Lehman, Clune, Stanley 2019, arXiv:1901.01753）**: 環境生成×エージェント最適化をペアに。「際限なく新規かつ複雑さ増大する能力を生成し続ける」。stepping-stone 転移が鍵。
- **NELL / Never-Ending Learning（Mitchell 他, CMU, AAAI 2015）**: 自己反省＋新表現・新タスクを定式化する能力が停滞・頭打ちを避ける。2010-01 から 24/7 で web を読み続け 8000万件超の信念を獲得。
- **Voyager（Wang 他, NVIDIA/Stanford, 2023, arXiv:2305.16291）**: LLM 初の lifelong learning agent。「automatic curriculum」＝「できるだけ多様なものを発見せよ」の包括ゴールだけ与え、**次の具体タスクはエージェント自身が現在状態から都度生成**（in-context の novelty search）。方向固定・タスク可変。
- **Open-Endedness is Essential for ASI（Hughes, Rocktäschel 他, DeepMind 2024, arXiv:2406.04268）**: novelty **だけでは不足、learnability（今のエージェントに習得可能な難度）も同時に要求**。
- **Open-Ended Learning Leads to Generally Capable Agents（DeepMind 2021, arXiv:2107.12808）**: 単一目標を最大化せず「世代間改善の反復」。タスク分布と目標を動的に変え続けて学習を止めない。
- **BP**: 24/7 エージェントには「①方向を示す抽象軸（新規性・発見数・learnability）＋②現在状態から次の具体タスクを自己生成する curriculum」の2層を与える。

## 4. 実務フレーム ＝ North Star / OKR
- **North Star Metric（Reforge 2022）**: 単位価値・質・頻度の3要素で定義しないと曖昧な BHAG に堕ちる。North Star 単独でなく input metrics（先行指標）との2階層で運用。
- **OKR（Google re:Work）**: Objective は野心的で少し居心地悪い／Key Result は測定可能で 0-1.0 採点。**達成率の sweet spot = 60-70%（常に100%なら野心不足）**。アンチパターン＝現状維持 OKR・低価値 objective・OKR を ToDo 化。Key Result は活動語(consult/help)でなく結果語(publish/launch)で書く。
- **BP**: 方向(North Star)と進捗の測定可能な兆候(Key Results/input metrics)を分離。Key Result はアウトカムで書く。100%達成を狙う設計にしない。

## 5. 「いつ止めるか」＝ 24/7 ループの終端条件
- **Anthropic, Building Effective Agents (2024)**: エージェント＝ステップ数を予測できず固定経路を hardcode できない open-ended 問題に使う。「タスク完了 or 最大反復上限」の停止条件。※完了しないゴール特有の終端は未カバー。
- **"When Agents Do Not Stop"（Hou, Wang 他 2026, arXiv:2607.01641）**: 主要 framework は max_iterations/recursion limit/max_turns/max_iter を既に提供。本質は「ループの存在」でなく「フィードバック経路が有効な bound でカバーされているか」。6,549 repo を静的解析、47 project で 68 件の無限ループ障害を実証。
- **BP**: 「終わらないゴール」と「終端条件なきループ」は別物。ゴールは open-ended でよいが、**各イテレーション/各サブタスクに必ず bound（max_turns・timeout・budget・fresh adversary の完了判定）**を持たせ、bound がフィードバック経路を実際にカバーするか検証。＝本 project の VCSDD（fresh-context adversary で収束判定）と同型。人間に「進めていいか」を聞くのでなく「機械的完了条件＋独立検証者」で終端。

## 6. 総合 ＝ adequate な長期ゴール仕様の5層
| 層 | 役割 | 根拠 |
|---|---|---|
| ①方向（North Star / novelty 軸） | 固定・抽象・単一 KPI に縮約しない | Reforge, Stanley&Lehman |
| ②現在の自己評価 | エージェントが「今どこか」を状態化 | Voyager skill library, NELL self-reflection |
| ③次の具体タスクの自己生成 | ①②から都度生成（人間が個別タスクを与えない） | Voyager auto-curriculum, POET |
| ④各タスクの終端条件(bound) | max_turns/timeout/独立検証者を必須 | IAL論文, Anthropic |
| ⑤進捗の多角評価 | 単一 metric でなく複数 KR＋fresh adversary、Goodhart 回避 | DeepMind spec-gaming, OKR |

## 正直な gap（subagent 報告）
1. Anthropic は「完了しないゴール」特有の終端を明示せず→ IAL論文(2026, 質は高いが著者知名度低)＋実務ブログで補完。
2. North Star Metric は**人間組織の成長 BP**であり、自律エージェント目標設計への直接適用の一次ソースは無し＝**類推適用**として扱う。
3. NELL/POET/Voyager は単一ドメイン（web読解/進化sim/Minecraft）の実証であり、汎用 24/7 proactive agent への一般化は論文内で明示されていない＝**外挿**。

## 出典
Anthropic Building Effective Agents (anthropic.com/engineering/building-effective-agents) / Anthropic Effective context engineering (anthropic.com/engineering/effective-context-engineering-for-ai-agents) / DeepMind Specification gaming (deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity) / Goodhart's law (en.wikipedia.org/wiki/Goodhart's_law) / Stanley "Why Greatness Cannot Be Planned" (goodreads.com/work/quotes/45494810) / Lehman&Stanley Novelty Search 2011 (dl.acm.org/doi/abs/10.1162/evco_a_00025) / Wiegand 2019 (cdn.aaai.org/ocs/18424/18424-79325-1-PB.pdf) / POET (arxiv.org/abs/1901.01753) / Voyager (arxiv.org/abs/2305.16291, voyager.minedojo.org) / Open-Endedness Essential for ASI (arxiv.org/abs/2406.04268) / OEL Generally Capable Agents (arxiv.org/abs/2107.12808) / NELL (cs.cmu.edu/~tom/pubs/NELL_aaai15.pdf) / Google re:Work OKRs (rework.withgoogle.com/intl/en/guides/set-goals-with-okrs) / Reforge North Star (reforge.com/blog/north-star-metrics) / Amplitude North Star (amplitude.com/books/north-star) / When Agents Do Not Stop (arxiv.org/html/2607.01641v1) / Machiraju Agent loops (techtalkwithsriks.medium.com/notorious-agent-loops-c4cc05b859b5)。
