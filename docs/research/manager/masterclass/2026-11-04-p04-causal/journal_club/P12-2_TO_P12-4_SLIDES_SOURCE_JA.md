# Phase12｜P12-2・P12-3・P12-4 詳細研究スライド原稿・講演ノート

**2026-11-08。独立した研究教材用30枚の新規構成**。既存Phase11の33枚、P12-1の16枚、旧34枚本番講演、118枚旧研究アーカイブを上書きしない。全ての架空数値にSYNTHETICと明示。学習の正本はROADMAP_STATUS_JA.md、実装正本は統合SSOTのMG-01〜MG-18。

## P12-2｜Long-Term Outcomes（Slide 01–10）

1. **なぜP12-2か**：予測正解→介入→長期の人間への価値は別の問い。講演：Accuracy、CTR、歩数、生活機能、ウェルビーイングを混同しない。
2. **Proximal vs Distal**：直後の反応と数週間〜数か月後の結果を区別。講演：MRTは主に近接効果、長期結果は独立に追跡。
3. **長期因果推論**：Delta_t=E[Y_t(1)-Y_t(0)]。講演：ITT・方策pi・時間依存交絡・本人の選択によるアウトカムを説明。
4. **Longitudinal Mixed Model**：Y_it=β0+β1A+β2t+β3At+b_i+epsilon。講演：β3は仮定に依存する傾きの差で、直ちに因果と呼ばない。
5. **Dropoutが結論を変える**：100×2群の架空例、観測者成功75%対60%。講演：母集団全体のITT差と異なる。
6. **Missing Outcome Bounds**：観測者のみ+15pp、欠測者について境界[-4,+26]pp。講演：95%CIではない。全数値SYNTHETIC。
7. **Welfare ≠ Engagement**：目標達成・Well-being・Functioning・Autonomy・Burden・Harmsの6軸。講演：一指標へまとめない。
8. **瞑想の有害事象も測る**：2025横断調査と2026デジタル実践二次解析の異なる母集団/定義。講演：割合を異研究間で比較しない。
9. **CONSORT 2025**：欠測/有害事象/介入提供/割付人数/データ共有。講演：心理/臨床研究の必要な倫理・停止・専門家支援。
10. **受入条件**：基礎数学・合成テストは教育、実人間RCT・長期の害・生活機能は未完。講演：MG-13とMG-17を実証として独立に管理。

## P12-3｜Scientific Communication（Slide 11–20）

11. **研究を発信する理由**：記事の量ではなく検証可能な知識。講演：情報利得、反証、訂正。
12. **3種類の成果物**：Technical paper、一般向け記事、書籍。講演：推定方法と読者が必要とする理解の深さを分ける。
13. **Evidence Graph**：Source DOI→Claim→Data/Model SHA→Experiment→Article→Book。講演：記事の文を逆追跡できる。
14. **FAIR**：Findable, Accessible, Interoperable, Reusable。講演：Git tag/commit、DOI、ライセンス、メタデータ。
15. **PRISMA & Living Review**：事前固定の検索/除外ルールと定期更新。講演：都合よい研究の選択を防ぐ。
16. **ICMJE 2026**：AIは学術誌の著者とならず、AI使用と人間の責任が必要。講演：無人事業と学術出版社の責任規程を区別。
17. **CRediT / Provenance**：誰がConceptualization/Analysis/Software/Validationを担当したか。講演：AI生成物の検証責任は別。
18. **自社メディアの公開Gate**：正本Markdown→SHA manifest→immutable content revision→CI→Netlify→HTTP readback。講演：ドラフトを公開済みと言わない。
19. **書籍の7部構成**：認知/因果/基盤モデル/エージェント/価値/社会/再現性。講演：過去の記事をそのまま束ねず理論をつなぐ。
20. **修正可能な知識**：訂正・Negative Result・外部Critiqueを履歴付きで受け入れる。講演：人気より研究の正しさ。

## P12-4｜Continual Intelligence（Slide 21–30）

21. **最終講義なのに終わらない**：文化・制度・本人の生活が変化。講演：固定Benchmarkだけで不変性を保証しない。
22. **Performative Prediction**：モデルθがデータ分布D(θ)を変える。講演：Perdomo 2020。過去のベストが未来のベストとは限らない。
23. **6つのDrift**：Covariate/Label/Concept/Policy/Measurement/System。講演：入力の分布シフトと性能悪化は別。
24. **JSD**：JSD=.5 KL(P||M)+.5 KL(Q||M)。講演：P=.5/.5、Q=.9/.1の架空2分布を比較し、原因を誤認しない。
25. **Label Delayの罠**：未観測結果はBrier=0にしない。講演：pending/unknownを明示しcoverageを併記。
26. **Champion vs Challenger**：NLL/Brier/TVD/Calibration/abstention/費用/害/権限を同条件で比較。講演：単一スコアで昇格させず、事前固定の候補採用条件を評価する。
27. **Safe Improvement Loop**：Observe→Verify→Evaluate→Propose→Shadow→Admit→Canary→Monitor/Stop。講演：実権限は元ホスト側で強制。
28. **Goodhart / Reward Hacking**：クリック最大化による通知疲労。講演：長期の本人の選択目標と安全性は別ガードレール。
29. **Continual Learning / Forgetting**：旧タスクと新タスクを別評価、Model Card、権利、Source Hash。講演：EWC/Replay/Adaptersは仮説と比較が必要。
30. **基礎学習の完了と続く研究**：P00〜P12の講義一巡 ≠ MG-01〜18の製品実証完了。講演：次は必要な実研究、外部評価、長期追跡を継続する。

### 原典
- JITAI/MRT https://pmc.ncbi.nlm.nih.gov/articles/PMC9755932/
- CONSORT 2025 https://www.bmj.com/content/389/bmj-2024-081123
- Cochrane risk of bias https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-08
- WHO-5 https://www.who.int/publications/m/item/who-ucn-msd-mhe-2024.01
- FAIR https://www.nature.com/articles/sdata201618
- Cochrane Living Review https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-21
- PRISMA https://www.prisma-statement.org/prisma-2020
- ICMJE 2026 https://www.icmje.org/recommendations/browse/artificial-intelligence/
- Performative Prediction https://proceedings.mlr.press/v119/perdomo20a.html
- Google Model Monitoring https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/model-monitoring/overview
