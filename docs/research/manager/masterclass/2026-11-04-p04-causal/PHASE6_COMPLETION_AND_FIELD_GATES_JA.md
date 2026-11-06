# Phase 6 統合報告（2026-11-05）— P06-1〜5を教える・動かす・検証する

**結論：P06-1〜P06-5の教育・再現可能なコード実験・研究証拠カードを実施。実事業での増分価値や本人への便益はまだ実証していない。** 学習順序・現在地の正本は`ROADMAP_STATUS_JA.md`。会社の実行権限とliveデプロイの正本は既存の運用SSOT。

## 何を実際に動かしたか

| 講義 | P06の問い | 実際の実装と観測 | なお欠ける実地受入 |
|---|---|---|---|
| P06-1 | 何を、何と比較するのか？ | 自社の公的案内サイト（公開Manifest＋6HTML）のread-onlyハッシュ検証、公式リンク4件到達、現行PlannerはNO_ACTION。研究対象を選定 | 正規権限のある実務S1 Shadow、実行対象と参加者 |
| P06-2 | What-ifモデルは簡単なルールより有用か？ | 人工24k学習／16k検証／40k独立方策RCT。最良の検証ルール比で純効用+1.422pt（95%CI+0.492〜+2.353pt）、28テスト | 実人間の未見予測、実事業の方策比較 |
| **P06-3** | 標本数と有効性判定はいつ行う？ | statsmodelsで基準25%／MDE3pt／80% power → 各群3395、15%脱落で全7990募集。Bonferroni4回判断なら各群4824。人工A/A 2400反復でのぞき見偽陽性11.92%、補正3.79%、最終1回4.79%。SRM検査。**21テスト** | 実募集、事前登録、同意/必要審査、事業の実割合 |
| **P06-4** | 利益と害を別々に測ったか？ | SciPyで架空EC 30,000人の購入/返金/変動費/苦情を計算。貢献利益+56.84円/割当（CI+36.55〜77.12）、苦情+0.942pt、**DO_NOT_SHIP**。**28テスト** | 実際の支払済み売上、返金、API費用と人の害、強い方策対照 |
| **P06-5** | 第三者が成果を確認できるか？ | P06-2〜4の凍結計画・結果9ファイルのSHA照合、公開本番サイトの独立readback、人工効果と実人間の結果を別の証拠カードに分離。結果：サイト配信VERIFIED、実利益/行動変容NOT_MEASURED、HOLD。**22テスト** | 実売上・実介入・効果研究の独立検証 |

**合計：P06-3〜5新規71件、旧P04〜P06-2の257件と合わせ、レビュー対象328/328件単体テスト成功。** この数に、未追跡の別実サイト下書き14件を誤って混ぜない。統計検定やモデル本体の独立な科学的妥当性は、テストの件数だけから判断できない。

## 再発明せず採用した技術

| 既存技術 | 研究における正しい使い方 | 参考 |
|---|---|---|
| **Statsmodels** | 二値指標の効果量と必要標本数（`NormalIndPower.solve_power`） | https://www.statsmodels.org/stable/generated/statsmodels.stats.power.NormalIndPower.solve_power.html |
| **SciPy** | Welch t、SRMの`chisquare`、A/Aモンテカルロ | https://docs.scipy.org/doc/scipy/reference/stats.html |
| **Statsig** | 本番での事前条件、mSPRT/Sequential testing、CUPED・feature gate | https://docs.statsig.com/experiments/advanced-setup/sequential-testing |
| **Spotify Confidence** | success/guardrail/qualityを全て満たさないとshipしないリスク判断 | https://engineering.atspotify.com/2024/3/risk-aware-product-decisions-in-a-b-tests-with-multiple-metrics |
| **Microsoft ExP** | Sample Ratio Mismatch、計測の異常・分析無効化 | https://www.microsoft.com/en-us/research/articles/alerting-in-microsofts-experimentation-platform-exp/ |
| **既存Manager Core** | 正規の公開Manifest、`verify_readback`、Authority/Outbox/Verifierの分離 | `products/manager/manager_core/` |
| **DoWhy/EconML/OBP** | 実データでの識別仮定・効果異質性・方策評価を発展させる | https://github.com/py-why/dowhy ／ https://github.com/py-why/EconML ／ https://github.com/st-tech/zr-obp |

新しいA/Bプラットフォーム、独自の統計ライブラリ、新規Graph DB、本番の書込みLedgerは作っていない。研究のPythonは**公開OSSを組み合わせる接着コード**に限定している。

## 3つの研究的な教訓

### ① データの量より、結果を見る方法が大切

`n=100`でp<.05、`n=200`でも確認、`n=300`でも…と繰り返し、ひとつでも有意なら止めると、全期間の偽陽性率が本来の5%より上がる。今回は2400反復で**11.92%**だった。安全上の緊急停止は別だが、良い結果の早期採用は統計補正が必要。

### ② 貢献利益が増えても、Guardrailが悪化したら採用しない

今回の完全架空世界では利益CIはプラスだが、苦情CIが許容幅を超えた。したがって**DO_NOT_SHIP**。これにより「最も利益が出る方策」ではなく、「本人・顧客・会社にとって受入可能な方策」を選ぶ必要を確認した。実際の精神的苦痛は今回測っていない。

### ③ 実行したこと・配信されたこと・誰かの人生が改善したことは別

実際の自社公開サイトはGETで確認でき、Manifestハッシュも一致。しかし`experiment_enabled=false`、`real_participants=0`、`beneficiary_outcome=NOT_MEASURED`。新しい本番S2を実施した証拠はない。会社の支払済み成果や反すうの改善は、対応する正規の外部結果と比較群を得るまで**null**にする。

## Phase 6の「完了」を二種類に分離

**A：講義・再現可能な教育用実験 — 完了**

P06-1〜5で「問い・候補→モデルあり/なし比較→実験設計→費用/害→出典付き実績カード」まで一通り説明し、人工の計算と公開サイト配信の読み取りまで検証した。**学習をP07-1へ進めてよい**。

**B：実会社でManagerが増分の価値を出したという実証 — 未達**

不足しているのは：
- P00-3：最初の本人/事業対象、権限、データ利用範囲、成果の確定。
- P05-5 S1：現在の会社運用とManager方策を同じデータ/予算で比較する実業務Shadow。
- P05-5 S2：自社保有で可逆な1件を、正規に許可されたExecutorで実行し、公式Receipt/独立GETを記録。
- P06-3実地：前向きに固定したPrimary/MDE/Stop/Guardrail、適切な母集団・同意・サンプル。
- P06-4実地：実際の支払い/返金/外注/API費用/不利益と本当の比較。
- P06-5実地：独立した受益者の成果・因果的な比較・費用込み増分利益の外部証拠。

**このBを完了したという虚偽の判定はしない。** 実会社に人間の自律的な意思決定を置き換える時期も、客観的に満たしたS1/S2/Guardrail/権限が揃うまで未定。

## P07への移行

次は**P07-1：行動学習・報酬・習慣・回避**。

P06で定義した証拠の階層とガードレールは、そのままP07の人間の行動や苦しみの研究へ持ち込める。ただし実人間の健康情報・反すう・気分尺度を扱うには、本人にとっての価値、目的別同意、撤回、リスク管理、必要な倫理審査と適切な研究デザインを先に用意する。

## 再現（Mac miniの隔離環境）

```bash
# 既存OSSを隔離して導入（新しい商用サービスは不要）
uv venv --python 3.12 --system-site-packages /private/tmp/manager-p06-statistics-20261105
uv pip install --python /private/tmp/manager-p06-statistics-20261105/bin/python \
    statsmodels scipy numpy pydantic jsonschema

cd docs/research/manager/masterclass/2026-11-04-p04-causal/experiments

/private/tmp/manager-p06-statistics-20261105/bin/python p06_3_trial_design.py
/private/tmp/manager-p06-statistics-20261105/bin/python p06_4_incremental_value.py
/private/tmp/manager-p06-statistics-20261105/bin/python p06_5_independent_proof.py

# 全Masterclassのレビュー対象328件のテストログ：
# ../evidence/TEST_RESULTS_P04_TO_P06_REVIEWED_20261105.txt
```

実APIや会社公開サイトの変化は**再実行の時点で異なる可能性**がある。ソースの取得日時とSHAを残し、以前と完全一致しなくても勝手に実験結果を差し替えない。

## 成果物一覧

`P06-3_JA.md`、`P06-4_JA.md`、`P06-5_JA.md`／各Python本体とテスト／`evidence/P06-3_*`、`P06-4_*`、`P06-5_*`／`evidence/TEST_RESULTS_P04_TO_P06_REVIEWED_20261105.txt`。

**講義の次はP07-1。実会社のS1/S2と人への実際の益は独立した受入条件として残る。**
