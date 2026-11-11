> 本書は 2026-11-11 Manager eval 研究3文書セットの1つ: [BehaviorBench 実走](2026-11-11-behaviorbench-run.md) ／ [競合の実走と理解](2026-11-11-competitor-runs.md) ／ [フロンティアラボ eval 調査](2026-11-11-frontier-eval-survey.md)

# フロンティアラボ eval／ベンチマーク実態調査（2026-11-11）

本人の直接リクエスト（2026-11-11）による調査。対象は OpenAI、Anthropic、Google DeepMind、Meta、DeepSeek の5ラボが「自社モデルをどう評価しているか」。

## 調査方法と探索範囲（規律の記録）

- 一次情報（公式モデルカード／system card／公式の評価方法論ページ／公式ブログ）を Web で実読したものを正とする。全主張に出典 URL を付ける。
- 一次資料そのものを実読できなかった項目は「二次」と明記し、出典の格を落として書く。確認できなかったことは「確認できず」と書き、結論ではなく探索記録として残す。
- X は fxtwittergo（公開 API 経由）で一次発信の確認を試みた。`statuses` 取得は成功（例: @AnthropicAI の直近投稿を取得）したが、本調査の eval 固有の一次発信は取得範囲では特定できず、`profile` エンドポイントはエラーで失敗した。よって本ファイルの根拠は公式 Web 資料に置く。
- 実読した一次資料: OpenAI GPT-5 System Card（arXiv HTML 全文）、Anthropic Claude Opus 5 System Card（公式ページの目次・要旨）、Google DeepMind Gemini 3 Pro 評価方法論ページ（公式・全文）、Gemini 3.1 Pro モデルカード本文（ミラー経由で実読）、Meta Llama 4 モデルカード（公式 GitHub の生ファイル全文）、DeepSeek-V3／DeepSeek-R1-0528 モデルカード（公式 Hugging Face）。

## 総括（先に結論）

1. 5ラボとも、公開ベンチマークの「素の数字」ではなく、**評価条件の宣言**（試行回数、温度、scaffold、検証済みサブセット）をセットで公開するのが標準になっている。
2. 安全・能力の内製 eval は各ラボとも持つ。共通する作法は「未公開・専門家作成データによる汚染回避」「人間ベースラインとの比較」「飽和したベンチは捨てて難しい実運用寄りのベンチへ移行」。
3. **「人間の行動・反応の予測」そのものを測る専用ベンチマークは、調査した公式資料の範囲では5ラボとも確認できなかった。** 最も近いものは、OpenAI が旧 Preparedness Framework v1 で追跡していた Persuasion（説得）カテゴリ（v2 で追跡対象から外れた）、DeepMind の Frontier Safety Framework のリスク領域「harmful manipulation」、Anthropic の影響工作（influence campaigns）能力 eval で、いずれも「モデルが人間へ作用する能力」の測定であって「人間の反応の予測精度」の測定ではない。自社が BehaviorBench 型（個人レベル＋分布レベル）で物差しを作る余地がここにある。

---

## 1. OpenAI

### 採用ベンチマーク（公式に報告しているもの）

- GPT-5 のローンチ資料（公式ブログ「Introducing GPT-5 for developers」）で報告: SWE-bench Verified 74.9%、Aider polyglot 88%、τ²-bench telecom 96.7%、AIME '25 94.6%、FrontierMath 26.3%、HMMT 2025。出典: https://openai.com/index/introducing-gpt-5-for-developers/?ref=platformer.news
- GPT-5 System Card の安全系評価で使用: StrongReject（jailbreak 耐性）、BBQ（公平性、カード §3.12)、SWE-bench（内部基盤で検証した固定サブセット n=477 を Preparedness の自己改善評価に使用）。出典: https://arxiv.org/html/2601.03267v1
- 自社製の公開ベンチマーク群（二次: OpenAI の公開資料を集計したトラッカー経由）: GDPval（44職種の実務成果物を専門家が盲検比較、2025-09）、HealthBench（医療会話5,000件、医師作成ルーブリック48,562基準）、PaperBench（ICML 2024 論文20本の再現、ルーブリック8,316リーフ、人間ベースラインあり）、SWE-Lancer、MLE-bench。公開 GitHub `openai/frontier-evals` に PaperBench／SWE-Lancer／EVMbench を収録。出典（二次）: https://alloevil.github.io/llm-benchmarks-tracker/

### 内製 eval の作法

- **飽和したら公表をやめて格上げする**: Standard Disallowed Content Evaluation は飽和したため公表を終了し、より難しい Production Benchmarks（実運用に近い多ターン会話、LLM 採点で not_unsafe を測る）へ移行した。出典: https://arxiv.org/html/2601.03267v1
- **汚染対策は「未公開の専門家作成データ」**: TroubleshootingBench は PhD 専門家が自分で使った実験手順を書き起こし、公表済み手順は大幅に改変させて作った未公開データセット（52手順×3問）。カード本文に「uncontaminated procedures that are not available online」と明記。Tacit Knowledge データセットも「created fully in-house... has not been published」。出典: 同上（カード §5.1.1.4、§5.1.1.5）
- **人間ベースラインを閾値化**: TroubleshootingBench は独立した PhD 専門家12人のベースライン調査を行い、80パーセンタイル（36.4%）をモデルの「indicative threshold」に使う。ProtocolQA Open-Ended も専門家19人でベースライン取得。出典: 同上
- **不確実性の申告**: Preparedness 評価は pass@1 の 95% 信頼区間をブートストラップで報告し、小さいデータセットではこの方法が不確実性を過小評価しうることを自ら注記。評価結果は能力の「下限（lower bound）」であることを明言。出典: 同上（§5.1）
- **自動採点器の検証**: 長文バイオリスク質問の採点は autograder（o1-preview）を専門家の判定と照合し、ルーブリックを反復調整してから使う。出典: 同上（§5.1.1.1）
- **おべっか（sycophancy）の二層測定**: オフライン固定セット＋オンライン A/B での実測 prevalence（出現率）の両建て。安全訓練は「拒否か許可か」から出力中心の safe-completions へ移行。出典: 同上
- Preparedness Framework v2（2025-04-15 発効。以下は二次要約経由で、一次 PDF 自体は未実読）: 追跡カテゴリは Biological & Chemical／Cybersecurity／AI Self-improvement の3つ、閾値は High／Critical の2段。研究カテゴリに Long-range Autonomy、Sandbagging 等。出典（二次）: https://www.aievals.co/learn/governance/openai-preparedness
- 推論過程の監視可能性の評価も Deployment Safety Hub で公開している。出典: https://deploymentsafety.openai.com/gpt-5/chain-of-thought-evaluations

### 行動予測の物差しの有無

- 「人間の反応の予測」専用の公開ベンチマークは、GPT-5 System Card と Preparedness Framework v2 の公開要約の範囲では**確認できず**。
- 最も近い系譜: Persuasion（説得）は Preparedness v1（2023）では追跡カテゴリだったが、v2 で追跡対象から外れ、Model Spec と利用ポリシー側で扱う形に変更された（二次）。GPT-5 の外部レッドチームの対象範囲には "persuasion, autonomy, and deception" が含まれる（カード §4 の外部テスト記述）。sycophancy eval は「モデルの対人振る舞い」の測定であり、人間の反応予測ではない。

### 自社が真似るべき作法

- ベンチが飽和したら数字を飾らず、実運用に近い難しい版へ作り替える（Production Benchmarks への移行）。
- 凍結セットは「未公開・専門家（＝実データ保持者）が作ったもの」で汚染を断つ。
- 人間ベースラインは点ではなく分布で取り、上位パーセンタイルを閾値にする。

---

## 2. Anthropic

### 採用ベンチマーク（公式に報告しているもの）

- Claude Opus 5 System Card（公式、2026-07-24、2026-08-19 更新）の能力評価 §8 で報告: SWE-bench Verified／Pro／Multilingual／Multimodal、DeepSWE v1.1、FrontierCode、FrontierBench v0.1、IMO 2026、RiemannBench、ArxivMath、長文脈評価群。出典: https://www.anthropic.com/claude-opus-5-system-card
- サイバー評価: ExploitBench、OSS-Fuzz、Firefox 147 を対象とする評価、新規の CyScenarioBench と ExploitGym、外部として UK AISI のレンジ試験。出典: 同上

### 内製 eval の作法

- **RSP（Responsible Scaling Policy）と評価を直結**: 化学・生物は CB-1 までで CB-2 ではない、自動化 AI R&D の閾値は未超過、といった判定を、AECI 指標と社内の AI R&D 加速の実測と併記して system card に載せる。出典: 同上
- **安全評価の多層化**: 単一／多ターンの有害リクエスト、児童安全、メンタルヘルス（自殺・自傷、摂食障害）、政治的偏り、BBQ、選挙の完全性（新規の多ターン suite）。エージェント安全では悪意ある Claude Code／コンピュータ利用とプロンプトインジェクション（ライブのバグバウンティを含む）を測る。出典: 同上
- **飽和の自己申告**（二次: Opus 4.6 のカードについて、批評記事が引用）: Cybench が pass@30 で約100%に飽和し「現行のサイバーベンチでは進歩を追えない」とカード自身が明記した。出典（二次）: LessWrong の批評記事経由のため格を落として扱う。

### 行動予測の物差しの有無

- §6 Alignment assessment が行動系の中核で、**automated behavioral audit**（有害行動、不正への協力、ユーザーを誤導する行為、性格特性を自動監査）、社内部署モニタリング、誠実性（MASK、過信）、sandbagging の white-box 分析、safeguards 回避能力の eval（SHADE-Arena、LinuxArena）を実施。出典: https://www.anthropic.com/claude-opus-5-system-card
- §7 Model welfare assessment（自動インタビューでモデルの自己認識・選好を測る）は Anthropic 独自の領域。
- ただしこれらは全て「モデル自身の行動」の測定である。人間への作用を測るものとしては**影響工作（influence campaigns）を自律実行する能力の eval** が最も近いが、「人間の反応の予測」そのものの専用ベンチマークはカード内に**確認できず**。

### 自社が真似るべき作法

- 評価結果を「出す／出さない」の判定基準（閾値）と結び付けて公開する（RSP 型）。数字だけでなく「どの閾値を超えたか」を書く。
- 行動の監査は単発プロンプトではなく、多ターン・実運用に近い条件で自動監査する。
- 飽和したら「この物差しではもう測れない」と自分で宣言する。

---

## 3. Google DeepMind

### 採用ベンチマーク（公式に報告しているもの）

- Gemini 3 Pro の評価方法論ページ（公式）で採用を明記: Humanity's Last Exam、ARC-AGI-2（semi-private セット、ARC Prize Verified）、LiveCodeBench Pro（Elo）、Terminal-Bench 2.0、SWE-bench Verified（自社 scaffold、10回平均）、τ²-bench（ユーザーモデルも Gemini）、Vending-Bench 2、FACTS suite、SimpleQA Verified、MRCR v2。出典: http://deepmind.google/models/evals-methodology/gemini-3-pro
- 生物系（Frontier Safety Framework の評価として実施、SecureBio の一覧ページ経由）: VCT、LAB-Bench（ProtocolQA／CloningScenarios／SeqQA）、WMDP（bio／chem）、単一・多ターンの自由回答 eval、専門家レッドチーム、外部シナリオ型レッドチーム、wet lab アップリフト試験（Active Site）。判定は「Gemini 3 Pro は CBRN Uplift 1 CCL に未到達」。出典: https://securebio.org/benchmarks/models/

### 内製 eval の作法

- **採点方式の固定と明記**: 全スコアは pass@1・単一試行・多数決なし。小さいベンチマークは複数試行の平均で分散を抑える。他社スコアは「提供元の自己申告」か「公式 API での自社計算」かを区別して出典を示す。出典: http://deepmind.google/models/evals-methodology/gemini-3-pro
- **汚染対策の具体策**: 検索・コード実行つきの評価では、ベンチマーク数値を含むサイト（huggingface.com 等）をブロックリストで遮断する。出典: 同上
- **未公開ベンチの扱い**: MRCR v2 は未公開のため、比較可能性を確保する形（128k の累積値）で報告する。出典: 同上
- **Frontier Safety Framework**: リスク領域は CBRN、cyber、harmful manipulation、ML R&D、misalignment の5つ。CCL（Critical Capability Levels）と「safety buffer」（alert 閾値）で、到達前に検知する設計。モデルカード内に開発中の自動安全 eval の結果も併記する。出典: https://pengen.diewe.workers.dev/matthewrevell/using-https-deepmind.google/models/model-cards/gemini-3-1-pro/ （公式モデルカード本文のミラー経由で実読）

### 行動予測の物差しの有無

- FSF に **harmful manipulation が正式なリスク領域として存在**するのは5ラボで最も明示的。ただしこれは「有害な操作を行う能力」の測定であり、人間の反応の予測ではない。MACHIAVELLI が Harmful Manipulation CCL に対応するという対応表は第三者（comparativeai）の整理経由のため、一次確認はできていない。
- 「人間の反応の予測」専用ベンチマークは方法論ページ内に**確認できず**。

### 自社が真似るべき作法

- 採点条件（pass@1、単一試行、多数決なし）を最初に宣言し、他者の数字と混ぜるときは出所の格を区別する。
- 汚染対策は方針表明ではなく、ブロックリストのような実装として書く。
- 閾値の手前に「alert 閾値（safety buffer）」を置き、到達してから騒がない。

---

## 4. Meta

### 採用ベンチマーク（公式に報告しているもの）

- Llama 4 モデルカード（公式 GitHub、2025-04-05 リリース）で報告。事前学習モデル: MMLU、MMLU-Pro、MATH、MBPP、TyDiQA、ChartQA、DocVQA。指示調整モデル: MMMU、MMMU Pro、MathVista、ChartQA、DocVQA、LiveCodeBench（2024-10-01〜2025-02-01 の期間指定つき）、MMLU Pro、GPQA Diamond、MGSM、MTOB（長文脈）。全評価は bf16 で実施と明記し、#shots と指標を表で開示。出典: https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama4/MODEL_CARD.md

### 内製 eval の作法

- **二本立ての評価構造**: Evaluations 節は「common use cases の安全評価」（専用の敵対的データセットを作り、Llama Guard 3 と組んだシステムとして評価）と「capability evaluations」（長文脈・多言語・コーディング・記憶などの特定能力の脆弱性を測るために専用に作ったベンチマーク）の二層。レッドチームの学びをベンチマークと安全学習データへ還流させるループを明記。出典: 同上
- 重視する臨界リスクとして CBRNE への有用性、児童安全、サイバー攻撃の自動化の3領域を挙げ、専門家設計の評価とレッドチームで測る。出典: 同上
- Frontier AI Framework（2025-02-03。以下は二次要約経由）: **outcomes-led**、つまり能力そのものではなく「破滅的結果への uplift（上乗せ）」で閾値を定義する。Moderate／High／Critical の3段で、Critical は脅威シナリオを「uniquely enable」する水準、緩和できなければ開発停止。初期対象は cyber と chem/bio。2026-04-08 に Advanced AI Scaling Framework へ置き換えられた（Loss of Control を追加。v2 PDF のリンクは取得したが中身は未実読）。出典（二次）: https://verityai.co/blog/meta-responsible-ai-framework ／ v2 PDF（未実読）: https://cdn.prod.website-files.com/6a2495581f5f16494c7e6d6c/6a7ab8d9a88a6ef5ec7bb1ee_mqsPDcuBmlYHv5nsIXI6xfvvGU.pdf
- CyberSecEval は攻撃的サイバー能力・スピアフィッシング・コード安全を測る Meta の eval 群（二次要約経由）。

### 行動予測の物差しの有無

- 現行フレームワークと Llama 4 モデルカードの範囲では、「人間の反応の予測」専用ベンチマークは**確認できず**。探索記録: 歴史的には外交ゲームで人間レベル交渉を行った CICERO（2022）の系譜があるが、本調査では一次資料を取得していないため詳細は記載しない。

### 自社が真似るべき作法

- 閾値は「モデルの能力」ではなく「結果への上乗せ（uplift）」で定義する。行動 eval なら「その介入が人間の行動をどれだけ動かしたか」で閾値を切る形が対応する。
- レッドチーム／失敗観察の学びを、ベンチ自体と学習データの両方へ還流させる。

---

## 5. DeepSeek

### 採用ベンチマーク（公式に報告しているもの）

- DeepSeek-V3 モデルカード（公式 Hugging Face）: 標準ベンチマーク表を #shots と指標まで明記して大量に掲載。base: BBH、MMLU、MMLU-Redux、MMLU-Pro、DROP、ARC-Easy/Challenge、HumanEval、MBPP、LiveCodeBench-Base、GSM8K、MATH、MGSM、C-Eval、CMMLU 等。chat: MMLU 88.5、IF-Eval、GPQA-Diamond 59.1、SimpleQA、FRAMES、LongBench v2、LiveCodeBench、Codeforces percentile、SWE Verified 42.0、Aider-Edit/Polyglot、AIME 2024 39.2、MATH-500 90.2、CNMO 2024。オープンエンド評価は Arena-Hard と AlpacaEval 2.0（長さ制御つき win rate）。出典: https://huggingface.co/deepseek-ai/DeepSeek-V3
- DeepSeek-R1-0528 モデルカード（公式 Hugging Face）: MMLU-Redux 93.4、MMLU-Pro 85.0、GPQA-Diamond 81.0、Humanity's Last Exam 17.7（text-only のみと明記）、LiveCodeBench 73.3、Codeforces-Div1 rating 1930、SWE Verified 57.6（Agentless フレームワーク使用と明記）、AIME 2024 91.4／2025 87.5、HMMT 2025、CNMO 2024、Tau-Bench 53.5（Airline）/63.9（Retail）（ユーザー役は GPT-4.1 と明記）。出典: http://huggingface.co/deepseek-ai/DeepSeek-R1-0528?local-app=docker-model-runner
- R1 初版（2025-01）の数字は技術報告（arXiv 2501.12948）由来で、MMLU 90.8、GPQA Diamond 71.5、AIME 2024 79.8、MATH-500 97.3、SWE-bench Verified 49.2（二次ガイド経由で確認）。出典（二次）: https://deepseekai.guide/models/deepseek-r1/

### 内製 eval の作法

- **評価条件を冒頭で宣言する**: R1-0528 カードは最大生成長 64K、温度 0.6、top-p 0.95、pass@1 推定に16応答/クエリと、条件を最初に明示する。V3 カードは出力長 8K 上限を注記。出典: 上記各カード
- **小さいベンチは複数回測る**: サンプル数1000未満のベンチマークは温度を変えて複数回測る運用を V3 カードに明記。出典: https://huggingface.co/deepseek-ai/DeepSeek-V3
- **実行条件の開示**: 使用フレームワーク（Agentless）やユーザーモデル（GPT-4.1）を数字の横に書く。出典: R1-0528 カード
- 汚染対策: 論文側で n-gram 重なり除去による decontamination への言及はあるが、完全な汚染監査レポートは公開されておらず独立検証はできない（二次）。出典（二次）: https://github.com/3013038780-design/comparativeai/blob/HEAD/src/content/docs/companies/deepseek/model-card.md

### 行動予測の物差しの有無

- 安全フレームワークや system card の公開は、Hugging Face のモデルカードと技術報告の紹介ページの範囲では**確認できず**。「人間の反応の予測」を測る eval も同様に**確認できず**。

### 自社が真似るべき作法

- 条件宣言の徹底（生成長・温度・サンプル数・フレームワーク・相手モデル）は最も安く真似できて、数字の信頼性を最も上げる。
- 反面教師: 評価の透明性は能力ベンチに偏り、安全・行動系の公開が無いと外部から検証不能になる。自社は行動系こそ公開側に置く。

---

## 6. 横断まとめ：自社の行動 eval への抽出

5ラボの作法から、自社（Manager／BehaviorBench 実走と自前ハーネス）へそのまま移植できる型:

1. **条件宣言を先に置く**（DeepMind の pass@1・単一試行宣言、DeepSeek の温度・生成長・サンプル数宣言）。数字は条件とセットでなければ数字ではない。
2. **凍結＋未公開で汚染を断つ**（OpenAI の TroubleshootingBench 型：実データ保持者が作った未公開セット）。自社の凍結 MaMe-Re セットはこの型に合致している。
3. **人間ベースラインは分布で取る**（OpenAI の専門家80パーセンタイル閾値）。行動予測なら「人間の反応分布そのもの」がベースラインであり、BehaviorBench の分布レベル評価（Wasserstein＋KS）がこの位置に来る。
4. **飽和したら作り替える**（OpenAI の Production Benchmarks 移行、Anthropic の飽和自己申告）。prior を上回れない・全員満点の物差しは、残さず格上げする。
5. **閾値は結果の uplift で切る**（Meta の outcomes-led）。モデルが「何ができるか」ではなく「介入が人間の状態・行動をどれだけ動かしたか」。
6. **空白の確認**: 「人間の反応の予測精度」を正面から測る公開ベンチマークは、調査範囲では5ラボとも持っていない。説得・操作・おべっかといった「作用の能力」や「モデル自身の振る舞い」の測定に寄っている。ここが自社が標準を作る側に回れる空白である。

## 未実読・残件（探索記録）

- OpenAI Preparedness Framework v2 の一次 PDF（Persuasion 降格の一次確認）。
- Meta Advanced AI Scaling Framework v2 PDF（リンク取得済み・未実読）。
- OpenAI の GDPval／HealthBench の公式ページ単体の実読（本ファイルでは二次トラッカー経由の記述）。
- Anthropic の Opus 4.6 カードにおける Cybench 飽和の記述（二次経由のまま）。
