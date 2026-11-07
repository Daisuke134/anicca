# MG-01｜実ホストS1 Qwen3-4B対既存ルールの比較実験契約

2026-11-07。実行開始時の唯一のカーソルはMG-01。実モデル・課金・独立readbackを受入後、唯一のカーソルは**MG-02**へ更新。これは新たな独立ロードマップではなく、元のMG-01一件の実行証拠と追試条件である。

## 実際に得られた結果（公式GitHub Actions）

- [実行run #42393800213](https://github.com/Daisuke134/life-manager/actions/runs/42393800213)：正式workflow完了・success。モデルファイル2,497,280,736bytes/SHA256を照合した本物のforward passが1回。
- 実サイトのManifest SHA256 bd670bee1cdb6dda2cd90f35352ba1b820eb181650521759e578fa4b8ac83dff、source f8e11d27b9f98b511d6fdc55e2781cacbe26f8a5。公開6HTMLを比較前後の2回、別のMacでさらに1回GETしSHA一致。
- 従来のルール判断 NO_ACTION、Qwen3-4Bの判断 REVIEW_ONLY、**不一致**。モデルは具体的な修正箇所の根拠を示していない。自動修正に転用せず、Qwenのモデル昇格は明示的に拒否。
- 正本の処理時間：既存ルール0.004287秒、モデル起動+推論46.606165秒、元ホストGET0.293709秒。公式GitHubジョブ全体135,000ms。
- GitHub Actions公式Billing/Timing APIではUbuntuのbillable=0ms、ジョブ1件。GitHub公開リポジトリの標準runner掲載料金=0ドル/分であるが、銀行/個別請求明細の確認はしておらずinvoice=null。実際の運用コストをゼロと一般化しない。
- モデルのプロンプトは公的サイトの公開リンクだけ。実人間の登録・行動介入・メンタルヘルス状態取得・通知・ホスト書込・承諾省略は**全0件**。利用者の便益、汎化、因果効果、長期の業務改善はNOT_MEASURED。
- MG-01は**公開サイト限定の技術的S1比較が成立した**ことだけを受入。ほかの一般化したモデル・製品品質は未達。次は統合SSOTのMG-02「データの目的・本番権限・撤回/停止」の一本のみ。
- [Qwen・既存ルール比較JSON](MG01_S1_REAL_QWEN_VS_INCUMBENT_42393800213.json)、[公式Billing JSON](MG01_S1_OFFICIAL_GHA_BILLING_42393800213.json)、[13条件の受入JSON](MG01_TECHNICAL_S1_ACCEPTANCE_20261107.json)、[最新の一つのカーソル](MANAGER_SINGLE_CURRENT_CURSOR_20261107.json)。

---

## 何を実行するのか

- 自社公開ホスト https://daisuke134.github.io/life-manager/manager-support/ を公式のHTTP GET（固定origin、リダイレクト禁止、サイズ上限）で読み取り、Manifest/6 HTMLのSHA256を検証する。
- **同じ実ページの情報**に対し、従来のOwned Catalog Plannerルールと、実際に重みを読み込んだQwen3-4B-Instruct-2507が、それぞれ NO_ACTION または REVIEW_ONLY を選ぶ。モデルには既存ルールの判定を渡さず、公開ページ・公式リンク・現ページへのナビゲーション情報だけを与える。
- 実モデルは既存実績のあるllama.cpp b12137 とQwen3-4B Q4_K_M GGUF（2,497,280,736 bytes、SHA256 2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e）を使う。公開モデル重みの再配布なし。
- 実行時間は単調増加時計で計測。GitHub Actionsの公開リポジトリ・標準Ubuntu runnerの掲載料金は0ドル/分（GitHub公式 https://docs.github.com/en/actions/concepts/billing-and-usage ）。実請求明細が取得できなければ請求実績はnullとする。
- モデルによるサイトへの修正、PR作成以外の外部作用、通知、顧客データ取得、行動介入は0件。公開情報だけを対象にする。
- モデル評価終了後に、別の独立公開GETを再実施。元のManifestや6ページに差分があれば、モデル一致率を採用せず明示的に無効化する。

## 計測・比較

観測した元ManifestのSHA、source commit、ページ数、既存方式の判断と所要時間、Qwenの判断とモデル推論（重みロード込み）時間、元ページGETの所要時間、再読取の一致、GitHub run IDを記録する。

**有効なモデル判断を1件取得しただけでは、人間行動の予測精度・実際の業務成果・因果効果・幸福の向上を実証したことにはならない。** 頑健性・複数業務・長期効果は別の受入条件。ゼロUIとは専用Manager画面や都度の確認不要という製品方針であり、非公開データの本人許諾を省略する権限ではない。

## 継続するMG-01の完了条件

実サイトへの読み取り権限・検証済みの公開bytes、固定同一入力、モデルと現行方式の実際の比較、実行時間と公式の費用根拠、独立の再読取、外部作用0を一つの公式GitHub Actions証拠で確認するまでMG-01を完了にしない。実モデルがNO_ACTIONを返しても、得られたのは技術的Shadowの成果であり、利用者への便益は未測定。

元の会社の運用SSOTもP00〜P12の学習索引も別々の実装TODOへ分離しない。この記録は実測レシートの索引に限る。

## 対象ファイル

products/manager/evals/manager_mg01_s1_live.py / test_manager_mg01_s1_live.py / .github/workflows/manager-mg01-s1-qwen-public-host.yml。GHA実行後に公式artifactと観測結果をreadbackして追記する。
