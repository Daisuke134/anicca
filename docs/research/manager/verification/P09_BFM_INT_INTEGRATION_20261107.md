# 【最新版：Phase 9統合とHeartSteps対象数の再現】

P09-1〜5の研究PR #9292はGitHub正規CI合格後、2026-11-07の本番mainへマージされた（コミット b73dfcb2387495bc2d4c32e5c473f5c5a9cb82f1）。INT-02は原著の42研究日・除外条件を再構成し、**8,274→7,540→6,061の元論文の対象数と3,594通知（内訳2,015/1,579）に完全一致**。初日効果比1.659、平均比1.147、日次減衰0.982。ただし元GEE/WCLS全推定器と元アウトカム平均253歩は未達。最新証拠はINT02_AUTHOR_COHORT_RECONCILED_20261107.md。BFM-02はQwen3-4Bの非対話モード・厳密な回答抽出を修正、クラウドの真のA/B正答率を取得するまでは「成功」と言わない。Be.FM/Centaurの利用権・計算資源はBFM_MODEL_ACCESS_AND_RIGHTS_20261107.md。

---

# Manager P09 → BFM-01/02 → INT-02：実行、再現性、残るゲート

2026年11月7日JST。正式会社SSOTの実装順と講義P00〜12の索引を変更しない。研究のPythonモデル評価・Github Actionsでの実モデル推論・実人間の公開論文再解析を統合した**実測に基づく中間報告**。未完了の事項を完了と扱わない。

## P09-1〜5の実行状態（既存PR #9292）
- 研究ブランチPR https://github.com/Daisuke134/life-manager/pull/9292 にあるP09-1〜5の実験・講義を再実行した。人工単体テスト19/19 PASS。実データはNature 2026 Source Data Figure1の70研究とMaMe-Reの25万?ではなく**100,000組**の日本語のミーム人間評定。生画像や無断の個人データは学習しない。
- P09-1：Natureの3356方向付き比較、1678反転対。StudyHoldoutと校正・bootstrapの独立再計算。これは元のRDS個票をRで完全再現したという意味ではない。
- P09-2：36研究の未知研究校正でzero-shot RMSE0.08154、5件部分プーリングRMSE0.08026。36研究中19改善/17悪化。
- P09-3：公開済み研究と未公表群の単純な代理分割でRMSE0.05244→0.08334。90%を目標にした区間は半幅0.24248で広い。Conformalの真のOOD保証なし。
- P09-4：1個の共有校正傾きだけの二領域モデルに負の転移を確認。Nature RMSE0.04541→0.08452。7B BFMの忘却を訓練した証拠ではない。
- P09-5：MaMe-Reの50未使用お題20,000組でRidge RMSE0.18469、過去平均0.18460（**専用の単純基準を超えられない**）。
- 本ターンの再実行は同じ公開元データを使用し、Source SHAの再確認、19テストPASS、対応スコアを再確認。技術レポート：[PR #9292実データレポート](https://github.com/Daisuke134/life-manager/blob/docs/manager-cultural-humor-p09-20261106/docs/research/manager/masterclass/2026-11-04-p04-causal/P09-2_TO_P09-5_REAL_EVAL_20261107_JA.md)。

## BFM-01 実モデルForward pass
[固定クラウド実行・出力の検証](BFM01_20261107.md)。Github Actions 42365475377でQwen3-4B 4bitモデル重みとllama.cppバイナリのSHAを検証し、実CPU Forward passを実行、6秒、架空の配分ゲームの生成回答0。元の4BモデルであってBe.FM adapterを読み込んでいない。GPT4/Be.FM/Centaurの正しい人間行動予測の比較結果でもない。

## BFM-02 凍結した人間評価での実モデル比較
[BFM-02研究計画とrun](BFM02_20261107.md)。CyberAgent AI Lab MaMe-Re（context, score, image descriptionのみCC BY 4.0）の250文脈×400候補、各ペア5評定・2325名の元データ。直前のP09-5と同じ160train/40validation/50holdout文脈を固定し、最後の50から24文脈をモデル出力を見る前に抽出。候補は学習側の過去評定だけで選定、24組（12組は過去の評定の差が大きい、12組は近い）。漫画画像・漫画台詞はプロンプトに使わない。
Qwen3-4B GGUFの実CPU推論結果を、人間二択の直接投票ではなく、それぞれのコマに対する独立の5票集約（0.0,0.2,...1.0）の差を用いた比較という**限定的な代理目標**で採点。無効生成を不正解に含め、元の各ミームの過去平均を同じデータで強い基準にする。大規模なHumorBenchやCentaurの結果と混同しない。結果は実際のActions artifact readbackで追記する。

## INT-02：公開MRTとRCTを実際に再解析
[HeartSteps 2019原著との対応、実測値、制約](INT02_20261107.md)。公式公開データにあるランダム選択フラグと補正済み配信を分ける。8274行/37人、判断番号0〜209かつavailableとした6,119件（元論文6,061件との差58）。実際の選択・配信記録不一致7件。Centered OLSの初日比1.6844、日減衰0.98079、21日目比1.12094。参加者クラスタbootstrap 95%区間[1.25166,2.23448]。元論文の推定1.66、0.98と近いが、**原著の3群割付・GEE/WCLS・6061観測を完全に再現しておらず、元の+35歩のITTを再現したと主張しない**。既存RCT Benchの3試験をsource-pinnedで再解析したが、欠測と原尺度の検証が不十分なため因果効果の最終結論は出さない。

## 権利・クラウドの制約（推論可能性と商用利用は別）
- Be.FM1.5-4BはHFモデルカードのApache表記とリンク先の制限が矛盾し、モデルがgated。HF_TOKENとModal cloud credentialは整わない。**未許諾で商用モデル・派生学習・本番へ転用しない。**
- Centaur 70BはNature2025論文と公開モデルカードを再確認。70Bは通常重みだけで140GB程度のbf16、単独のfree GithubCPU環境では適切なモデル比較に必要な計算資源がない。別条件の小さなQwenベースラインをCentaurとして扱わない。
- 原著のPsych-101/BehaviorBenchの一部データには非商用・権利制約がある。見られるページや公開データだからといって全データで商用訓練可能としない。
- 弊社の実利用者への介入、同意・撤回・倫理レビューと長期アウトカムは独立したフェーズ。現状0名、介入0件。

## 追加で必要な再現・受入条件
1. Be.FM：アクセス、ライセンスの権威ある正式解消、同一Qwenベースとの同条件推論・推定値比較、研究単位holdout。
2. Centaur：合法な70B重み、GPU/メモリ・費用上限、公式Psych-101 holdout契約、LLMと行動モデル同条件比較。
3. HeartSteps：原著の6,061対象・三群の原割付・元の共分散構造と推定対象の一致、ミッシングネス検証、独立のRCT再現。
4. P09：個人・研究・時間・文化の真の未知対象に拡張し、予測精度と不確実性に加え古いタスクの退行を監査する。
5. 製品：ユーザーが自ら選ぶ目標・STOP/NO_ACTION・使用権利・実際の便益/害/費用の独立検証を満たす。

**判定:** Learning/partial empirical execution YES. Production-ready universal BFM, human welfare effect, full original-paper reproduction NO. 次の講義はP10-1、既存BFM-01/INT-02の実装ゲートは未完了。
