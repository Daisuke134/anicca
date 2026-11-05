# Manager — 既存行動基盤モデルと評価基盤の採用・再現計画
更新: 2026-11-06。実行した内容と未実行を厳密に区別する。これは研究資料でありROADMAP_STATUS_JA.mdとは別の進捗SSOTを作らない。

## 1. まず再利用する
Centaur (Binz et al., Nature 2025) はLlama 3.1 70BをPsych-101でQLoRA rank8により適応。Psych-101は60,092人、10,681,650選択、160実験を自然言語へ転写した人間の観測データ。Heldout参加者、予測不能なカバーストーリー変更、構造変更、未知ドメインに関する複数の一般化検査が報告されたが、すべての人間行動や実介入の改善を証明するものではない。公式LoRA 4bit推奨80GB GPU、BF16の統合モデルは160GB以上が必要。公式は https://github.com/marcelbinz/Llama-3.1-Centaur-70B と https://www.nature.com/articles/s41586-025-09215-4 。

Be.FM 1.5-4B (University of Michigan / Be.FM group) はQwen3-4B-Instruct-2507 baseのLoRA。survey/personality/economic game/taskに適応し公式モデルカードでは単一24GB以上のGPUで実行可能。Hugging Face APIで2026-11-06に確認: 公開model metadataにApache-2.0、gated=auto（Hugging Face個人アカウントでアクセス条件を受諾する必要）。https://huggingface.co/befm/BeFM1.5-4B 。Be.FM 1.5-70BはLlama-3.3-70B base/LoRA、Llama license、auto-gated。https://huggingface.co/befm/BeFM1.5-70B 。

BehaviorBench (Huang et al. 2026) は行動科学の既存ベンチマーク。MIT licenseの公式評価コード https://github.com/umich-foreseer/behaviorbench_eval をそのまま採用する。別配布された評価用データ https://huggingface.co/datasets/befm/BehaviorBench はCC BY-NC-ND 4.0のため、営利企業Aniccaが商業実験・学習に無条件利用できるわけではない。評価データと学習データを絶対に混ぜない。権利が未解消なら正式な営利用途のフル評価を実施しない。

BehaviorBenchはBig Five survey、MobLab economic games、scientific-workflow prediction、international economics contestの4つの主な系列を含む。20 scenarios（11 individual, 9 distributional）、公開leaderboardには28 models（2026-11閲覧時）。mean win-rateは平均の相対勝率であり「何％の人の行動を当てたか」と同義でない。公式Be.FM 1.5-70B=0.800、Be.FM 1.5-4B=0.787はこの採点方法・比較モデル集合に依存し、独立再実行ではない。https://umich-foreseer.github.io/behaviorbench/ と https://arxiv.org/html/2606.24162 。

## 2. 必要メモリと最安のクラウド経路
CPUソフト互換性: 公開GitHub repoのstandard hosted ubuntu-24.04 runnerは無料（GitHub公式）。新workflow manager-upstream-behaviorbench-smoke.ymlは外部のMITコードをSHA ddd646ed2bbecdb79094eb56763ee7664d2f8e1aに固定、uv sync --dev / pytest / official CLI help / HF license metadata-only auditを実行する。ベンチマークデータをダウンロードせず、高額GPUや既存Mac miniを利用しない。成功しても公式benchmarkのモデル得点ではない。
Be.FM 1.5-4B: Modal Starterは月$0+計算費、毎月$30のcompute creditが含まれる（利用資格/決済設定を確認）。Modal L4 24GB GPU $0.000222/sec ≒$0.80/hr、CPU/メモリ/ストレージ別。GPUの追加現金支出を抑える第一候補。割当を使えないときはRunpod RTX A5000 24GBが2026-10公式料金$0.27/hr（一部Communityはさらに安い）。どちらも在庫・価格変動と冷却開始時間に注意。https://modal.com/pricing https://www.runpod.io/pricing 。
Centaur 70B 4bit: 単A100 80GB GPUを公式に推奨。Runpod Secure $1.79/hr、Modal A100 80GB $0.000694/sec≒$2.50/hr。短い試行から始め、実際の必要VRAM、長さ、時間、ストレージ、権限をログ化。2h Runpod GPUのみ約$3.58。Mac miniに数十GBのモデルをダウンロードしない。
Model accessはHFのUIで利用条件を承認し、HF_TOKENをクラウドSecretへ登録する。秘密情報やカード番号をチャット・GitHub・スライドに掲載しない。本人の決済は公式サービスのcheckout経由。

## 3. 他社閉鎖型：実行可能な部分だけ学ぶ
humans& Ampersand v0.1は2026-10-20の公式model cardではGLM 5.3を基礎とした長期協働モデル。744B total/約40B active MoE、APIモデル名ampersand-v0.1。公開open weightsではなくAgents APIを利用する。2026-11公式の従量単価はuncached input $1.00/M tokens、cached $0.20/M、output (reasoning含む) $5.20/M。https://ampersand.humansand.ai/blog/model-card.html https://ampersand.humansand.ai/docs/PRICING.html 。自分で744B GPU群を買う理由はない。品質は実人間の自己選択行動改善と区別。
Persimmonは人の会話を模擬するuser simulator。公式 https://persimmon.humansand.ai/ はsign-in型、公式の独立ダウンロード可能weightsは未確認。Ampersandの学習時user simulationとAPI利用は別。
Listen Twins（2026-10-22公表）は実際の人の深いインタビューから1対1でデジタルツインを構築する顧客調査機能。メーカーの「分布精度93%」は企業公表の評価であり共通独立benchmarkスコアと同一ではない。https://listenlabs.com/whatsnew/introducing-listen-twins 。Listen Labsの顧客リサーチAPIはモデルweightsを公開するAPIではなく、権限のある調査/参加者の実データを扱うため同意・費用・規約が必要。

## 4. Implement into Manager now
Reuse: BehaviorBench MIT scorer、Centaur/Be.FM LoRA、Psych-101 Apache2トレーニングセット、BCIO/BCTTv1、既存P07-1/P07-2実データbaseline。
Wrap: 同一の研究単位分割/入力形/推論予算/シード、モデルカード、calibration、IDの匿名化、時間と内容のリーク監査、独立比較。
Build only gaps: 介入の識別済み因果効果推定、長期予測、相互影響/社会シミュレーション、同意と権限を制約したNO_ACTION含むpolicy、本人が望む行動・負担・害の外部検証。
BehaviorBenchは予測・戦略と研究知識を広く見るが、人間の苦しみが実介入で減ったかは測らない。従ってゼロから競合の総合leaderboardを再実装せず、必要ならBehaviorBench拡張プロファイルとしてManagerBench Intervention/Harm trackを作る。

## 5. GitHub repo name migration
Daisuke134/life-managerは公開repoでadmin accessがあり、Daisuke134/managerは2026-11-06のGETでnot found。**しかし即座のrenameは危険**。既存Anicca Netlify CIはraw.githubusercontent.com/Daisuke134/life-managerの不変コミットを利用し、marketing/blog overlayを取得する。GitHubの一般的なURL redirectがすべてのraw/CDN/API/third-party workflowを保証するわけではない。まず影響参照を一覧化し、新旧URLの動作・Netlify本番・blog・payment smokeをテストしてからrenameする。SSOT複製を避ける。アーカイブと秘密を失わない。

## 6. 実験の順序（実施済みの主張はreceiptsのみ）
B0. クラウド上で公式MIT evaluator install/test/CLIを実行。synthetic fixtureで採点器のソフト動作を確認。
B1. HF gated model tokenを適切に接続し、Modal/RunpodでBe.FM 1.5-4Bを1件forward-passする。Qwen3-4B baseを同じ入力・推論予算で比較。
B2. 利用が許可された真の外部人間観測データ（各licenseに従う）に対してheldout/horizon/分割・95%CIを固定した実採点。BehaviorBenchのNC/NDセットは権利処理後。
B3. Centaur A100 4bitを実行し、Psych-101形式（human response は << >>）で他の単純モデルと比較。公式testはgated/CC BY-NDで権利を確認。
B4. AmpersandのAPIを短い制御された無害な会話で検証、モデルの返答だけで他者への影響/長期便益を宣言しない。
B5. Persimmon/Listen Twinsは公開利用条件/価格/参加者権限が確定した範囲で評価。非公開weightを勝手に再現できたとしない。
B6. 実データで共有の行動モデルが単一タスクbaselineを超えたときだけ、Managerのopen-weight公開を検討。実介入の因果効果は追加のRCT/MRTを要する。

一次資料: https://www.nature.com/articles/s41586-025-09215-4 / https://arxiv.org/html/2606.24162 / https://arxiv.org/html/2505.23058 / https://github.com/umich-foreseer/behaviorbench_eval / https://huggingface.co/befm/BeFM1.5-4B / https://huggingface.co/datasets/befm/BehaviorBench / https://modal.com/pricing / https://www.runpod.io/pricing
