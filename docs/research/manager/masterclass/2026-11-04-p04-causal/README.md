# Manager Masterclass｜P04-1〜P05-5 因果推論・Ontology・行動と実行の接続

**更新：2026-11-04（Asia/Tokyo）。** このディレクトリは教育講義と架空実験の再現資料。**実人間への介入、実公開RCTの前向き効果予測、Manager Behavior Foundation Modelの科学的な優位性の実証ではない。**

**唯一の全ロードマップ・進捗正本：`ROADMAP_STATUS_JA.md`。** 本READMEやMANIFESTを講義の別SSOTとみなさない。P04-1〜6とP05-1〜5は講義・人工実験まで完了。次の講義はP06-1。P05-5の実務Shadowと限定本番実行は未達。P05-2ではListen Labs Study APIの実認証GETも確認（実介入なし）。P04-5の実在公開RCTに対する未見研究効果予測、P00-3の権限・同意、実世界での方策検証は未完了。


## Managerの中核仮説と実証すべき価値

[What-if Machine × Executor：中核仮説と科学的証拠の階段](MANAGER_WHAT_IF_EXECUTOR_THESIS_JA.md) に、製品・流通・本人の便益を**結果から独立検証する**研究方針を整理した。Managerそのものを企業へ売ることを先に必須にせず、Managerが作る製品やサービスの実際の成果で価値を示す。外向きの名称は「Manager」とするが、既存リポジトリ・APIの破壊的リネームは行わない。オープンソースと将来のオープンウェイトを目指し、第三者データの権利・個人の健康情報・同意・安全性は優先して保護する。

**60分発表の最後の4枚（31〜34）** と、詳細版の対応する3枚（46〜48）をこの構想に合わせて更新した。世界最大の利益、完全自動バズ、精神疾患の治療などは実証済みの成果として扱わない。発表では反証可能な研究仮説として紹介する。

## 2026年11月5日 13:00–14:00｜神経科学ジャーナルクラブ

**本番ではこちらの厳選34枚版を使う。** 来場者は学術/業界/専門知識に関係なく理解できるように、初学者・研究者・起業家・投資家を想定する。人間行動シミュレーションの専門知識を前提とせず、歴史、モデルの種類、代表的な研究・企業、ベンチマーク、因果と限界を基礎から説明し、Managerは最後の4枚・約6.3分に留める。

| ファイル | 内容 |
| --- | --- |
| [60分発表 PowerPoint](journal_club/AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx) | **34枚**、編集可能・全ページに日本語発表者ノート |
| [60分発表 PDF](journal_club/AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pdf) | **34ページ**、発表画面用 |
| [全34枚日本語読み上げ原稿](journal_club/SPEAKER_SCRIPT_60MIN_JA.md) | 1ページごとの自然な読み上げ文と元スライド・時間 |
| [60分の進行表](journal_club/RUN_OF_SHOW_60MIN_JA.md) | **43.0分講演＋15分質疑＋約2分の余裕**、章別時間・重要スライド・短縮ルート |
| [発表版を再生成](journal_club/build_60min_journal_club.py) | 過去の33枚を構築した歴史的script。現在の34枚は`build_p05_phase5_decks.py`の改訂が正本。別々に管理し、元ファイルを破壊しない |

**優先順位：** ①基礎と研究史 ②どの対象にどの模型を使うか ③既存研究・企業は何を主張しているか ④何を検証して何をまだ検証していないか ⑤最後にManagerが目指すこと。数式の厳密な導出・企業の細かい数字・P04-6の全シミュレーションは本番で列挙しない。質疑用の長い資料に残す。

## 全93枚の詳細保存版（本番で一挙上映しない）

| ファイル | 内容 |
| --- | --- |
| [詳細93枚PowerPoint](journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx) | 元82枚のManager対応46〜48を研究仮説に更新し、P04-6付録3＋P05-1付録2＋P05-2付録2＋P05-3〜5/展開付録4＝93枚。既存本文は維持 |
| [詳細93ページPDF](journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pdf) | 93ページ（元82＋P04-6研究3＋P05-1研究2＋P05-2研究2＋P05-3〜5/展開研究4）。新しい付録は画像レンダリングで統合し、元のページを維持 |
| [全93枚の日本語発表ノート](journal_club/SPEAKER_NOTES_JA.md) | 1〜93の全ページ分。PowerPoint内部にも全93枚のノートを保存 |
| `journal_club/build_p05_phase5_decks.py` | **研究89→93枚、本番33→34枚、一般向け用語とManager段階ロードマップ**。再実行は入力版の確認後 |
| `journal_club/build_p05_2_appendix.py` | **87枚→89枚のP05-2研究付録追加**。旧本番33枚は本アップデートで34枚に改訂 |
| `journal_club/build_p05_1_appendix.py` | **85枚→87枚の研究付録追加**。本番用33枚は不変 |
| `journal_club/build_p04_6_appendix.py` | 82枚版→85枚版への追加作成に使用。すでに85枚なら二重追加しない |
| `journal_club/build_p04_45_appendix.py` | **歴史的な74枚→82枚作成スクリプト**。現在93枚版への再実行はしない |
| `journal_club/export_p04_45_pdf.py` | **歴史的な74ページ→82ページPDF結合スクリプト** |
| `journal_club/RUN_OF_SHOW_JA.md` | 元のフル講義の履歴上の進行表。**2026-11-05本番は60MIN版の進行表を優先** |

## 講義の本文

| 資料 | 内容 | 学習の検証 |
| --- | --- | --- |
| `P04-1_JA.md` | 観察vs介入・DAG・潜在的結果 | 完全架空データ、14テスト |
| `P04-2_JA.md` | RCT・ATE・ITT・信頼区間 | 架空RCT、17テスト |
| `P04-3_JA.md` | 交絡・g-formula・IPW・AIPW・DiD | 架空30,000人、26テスト |
| `P04-4_JA.md` | CATE・効果異質性・方策選択・媒介 | 架空24,000人＋媒介20,000人、12テスト |
| `P04-5_JA.md` | study holdout・予測凍結・介入効果予測 | 架空180研究、11テスト。**実公開RCTの未見予測は未実施** |
| `P04-6_JA.md` | 事前登録・方策対方策RCT・意思決定価値・無計画な途中解析 | 架空40,000人＋A/A 750試行、16テスト。**実研究の事前登録・実介入は未実施** |
| `P05-1_JA.md` | Ontology・状態・時点・知識グラフ・Digital Twin・既存技術の徹底調査 | 既存Manager Coreを再利用し人工5イベントのread-only投影、26テスト成功。実行権限・実人間は未接続 |
| `P05-2_JA.md` | 既存Job/Effect/Receipt/RuntimeEventのID・証拠Trace、Listen Labs実API | 人工時点別Trace・39テスト／API安全性8テスト。TinyFish公式画面＋認証GET 2件HTTP 200。予測ID/判断ID未接続、実サービス改変なし |
| `P05-3_JA.md` | 複数エージェントの役割、権限・期限・撤回 | 既存Manager Coreで人工Grantによる6拒否条件の確認、本番は未受入 |
| `P05-4_JA.md` | 不明状態・二重実行防止・独立確認・復旧 | DurableOutboxの人工送信とUNKNOWN→PRESENT、P0のみ |
| `P05-5_JA.md` | Shadow・限定1回実行の条件と学習 | 既存Shadow41テスト成功、実務Shadow/本番S2未実施 |
| `MANAGER_MODEL_COMPANY_IMPACT_MILESTONES_JA.md` | モデル訓練・公開・会社への導入・人の便益の3本線 | **日付は条件付き仮目標であり実績・保証ではない** |

基礎単体テストは **122/122件成功**（P04-1〜6：96件／P05-1：26件）。さらに比較ベンチマークの23件が成功し、**P05-1時点の合計は145/145件成功**。基礎のログは`evidence/TEST_RESULTS_P04_1_TO_P05_1.txt`、旧P04-1〜6ログも保存。教材のテスト合格を実世界への有効性の証明と混同しない。

## P05-1の調査と実装結果

**結論：巨大なOntologyを一から作らず、既存のBCIO・PROV-O・JSON-LD・JITAI・既存Manager Coreを再利用する。** [日本語講義全文](P05-1_JA.md) には一次資料、先行研究の限界、プロトコル、既存コードのマッピング、将来の評価基準を整理。

- [既存のGraph Skill](https://github.com/Daisuke134/life-manager/blob/main/skills/graph-engineering/SKILL.md) はGraphを証拠のread-only projectionと位置付けているので、その方針を守った。
- `experiments/p05_1_ontology_readonly.py`は既存Manager Coreの`StateMachine`と`InterventionPlan`を再利用し、人工5イベントの知識グラフを構築する。実行・事業・個人情報とは接続しない。
- 26件の単体テスト、出典SHA、時系列、知らないことを知らないまま扱う制約、実行権限をGraphから生成しない制約を検証した。
- [実行結果](evidence/P05-1_READONLY_SYNTHETIC_PROJECTION.json)、[全122件のテストログ](evidence/TEST_RESULTS_P04_1_TO_P05_1.txt)。
- 実行・モデルの実世界の改善は未検証。**次の講義：P05-2「実験ID・行動ID・証拠の共通形式」。**

## P04-6の新規実行結果（完全架空）

- 対象40,000人。政策群への無作為割当：Manager型約19,835人／比較型約20,165人。
- 同じ事前特徴、同じ候補行動、同じ観測期間を設定。比較方策は有用な固定ヒューリスティックであり「世界最強のbaseline」とは認定しない。
- 主成果（完了マイナス通知人工費用0.02/回）は、Manager型平均0.33616／比較方策0.32003、差 **+1.613pt**（95%近似CI **+0.688〜+2.539pt**、p≈0.000635）。
- 人工の期待効果真値は**+2.00pt**。設定した世界での証拠に過ぎない。
- 効果ゼロの架空A/Aを750回反復し、最終1回の未補正検定による偽陽性**4.27%**、途中6回のいずれかで有意なら成功とした偽陽性**15.20%**。
- 結果生成前に`P04-6_PREANALYSIS_PLAN_SYNTHETIC.json`を保存し`P04-6_PLAN_FREEZE_RECEIPT.json`でSHA256を固定。**外部公開研究登録はしていない**。
- 全人工40,000人のCSVは`evidence/P04-6_POLICY_RCT_SYNTHETIC.csv`。結果は`evidence/P04-6_POLICY_RCT_SYNTHETIC_RESULTS.json`。

## ローカル再現

Python 3.11+とNumPy、PowerPoint編集はpython-pptx、PDF/追加スライド生成にはpypdf・Pillowが必要。

```bash
cd docs/research/manager/masterclass/2026-11-04-p04-causal/experiments
python3 -m unittest discover -p 'test_p0*.py' -v
python3 p04_6_preregistered_policy_value.py
python3 p05_1_ontology_readonly.py
```

本番発表版は`journal_club/build_60min_journal_club.py`で再生成。**詳細マスターを消す／発表で全93枚を使う運用はしない**。厳選34枚／詳細93枚を保持する。最後の3枚は update_manager_thesis_slides.py で仮説に沿う内容へ同期する。

## 監査

`evidence/P04-6_JOURNAL_CLUB_QA.json` に、33枚・33ページ、85枚・85ページ、発表版33枚の全ノート、詳細版85枚の全ノート、Manager対応46〜48を除く元79枚の本文保持、凍結予測ハッシュ、人工RCT計画ハッシュ、96テストの照合を記録。ファイルのSHA256とサイズは`MANIFEST.json`に保存する。**外部の研究ベンチマーク検証や実施権限の承認を行ったとは主張しない。**


## 2026-11-04追加｜既存コードと外部OSSの実行監査・4方式比較

- [P05-1実コード徹底読取・OSSエコシステム調査](P05-1_CODE_REVIEW_ECOSYSTEM_JA.md)：BCIO・EDSL・Graphiti・MiroFish/OASIS・Palantir SDK・Listen Labs公式APIのコード/ライセンスと実行範囲。各リポジトリのソースはvendorしない。
- [Manager Ontology/Query/evidenceの統合実装仕様](https://github.com/Daisuke134/life-manager/blob/main/products/manager/docs/specs/2026-11-04-manager-ontology-query-evidence-reuse.md)：実行境界、4方式比較、採用判断、P05-2受入。会社の大きな統合SSOTは別。
- **4方式のsynthetic同条件比較**：[元データと全測定値](evidence/P05-1_QUERY_BENCHMARK_SYNTHETIC.json)、[Pythonコード](experiments/p05_1_four_way_benchmark.py)。12,252イベント・800質問でFlat scan=6,322µs／Python Dict=0.50µs／SQLite=3.29µs／Graph Projection=0.50µs（検索中央値）。すべて正解一致、索引生成コストは別計測。Graphiti本体はこの性能比較に含まれない。
- **実際の隔離実行**：EDSL 1.0.9は3架空Agent＋test modelを通信禁止で成功、Graphiti-core 0.31.2は型のオフライン生成成功、BCIO OWLに2,634クラス宣言を確認。Listen Labsの無認証GETは401で、Twinsの公開APIは未確認。MiroFish/OASIS/Palantirの本番実行は未実施。
- [完全人工のEDSL→Manager Core→Graph/Dict/SQLite/Flat E2E](evidence/P05-1_OFFLINE_END_TO_END_SYNTHETIC.json)：5人工イベントと6問で4方式一致、権限不足のため既存Manager Coreが`NO_ACTION`。ネット接続・個人情報・実通知なし。
- [外部OSSピン留め・ライセンス・正本監査](evidence/UPSTREAM_CODE_AND_LICENSE_AUDIT.json)／[BCIO検査](evidence/BCIO_REAL_OWL_SNAPSHOT_AUDIT.json)。
- **Python3.14テスト互換修正**：`products/manager/tests/test_collaboration_authority.py`の`dataclasses.replace(init=False)`例外型がPython3.12でValueError・3.14でTypeErrorとなる差を許容。許可/実行の実装そのものは未変更。両版で44 tests＋15 subtests成功。
- **採用判断**：単純なqueryはまず既存のSQLiteとPython辞書を使う。Graphitiや新Graph DBを強制導入しない。時間付き知識抽出や意味検索が必要と分かった段階で、精度と費用込みで独立比較。P05-2の実装課題と実世界検証は残る。


## P05-2実験結果（2026-11-04）

[講義全文](P05-2_JA.md)、[共通スキーマを再利用する読み取り専用Trace](experiments/p05_2_evidence_trace.py)、[人工Traceの全結果](evidence/P05-2_SYNTHETIC_TRACE_RESULTS.json)、[安全なListen Labs API GETプローブ](experiments/p05_2_listenlabs_readonly_probe.py)、[API実認証GETの匿名結果](evidence/P05-2_LISTENLABS_AUTH_READONLY_SUMMARY.json)、[193件の全テストログ](evidence/TEST_RESULTS_P04_TO_P05_2.txt)。

**P05-2新規48件、旧P04〜P05-1の145件を含む193/193件成功。** APIキー・ウォレットID/残高・調査名/ID・参加者回答はGitHub・ログに保存しない。外部へのPOST/公開/料金・実参加者への介入はゼロ。**研究保存版89枚・89ページ**、本番発表版33枚は変更なし。次はP05-3。


## 2026-11-04 Phase 5最後のP05-3〜P05-5

[役割・権限](P05-3_JA.md)、[復旧・独立証拠](P05-4_JA.md)、[Shadowと実務導入](P05-5_JA.md)を既存Manager Coreの実コードで検証した。サンドボックスで6種類の権限外操作拒否、Outboxの二重実行0、処理後TimeoutのUNKNOWN→PRESENT照合、1回の人工provider送信と独立した人工sensor確認を再現。Liveの外部操作・有料呼出・本人への介入は0。Shadow無効はモデル呼出0、既存Shadow本体のユニットテスト41件成功。

[実行コード](experiments/p05_3_5_end_to_end.py)、[テストコード](experiments/test_p05_3_5_end_to_end.py)、[結果JSON](evidence/P05-3_5_EXISTING_CORE_OFFLINE_RESULTS.json)、[テスト229件](evidence/TEST_RESULTS_P04_TO_P05_PHASE5.txt)、[既存Shadow41件](evidence/P05_3_5_EXISTING_SHADOW_TESTS.txt)。

[独自モデルの訓練・Open-weight公開・会社運営・人間の行動変容の条件付き高速ロードマップ](MANAGER_MODEL_COMPANY_IMPACT_MILESTONES_JA.md)。**P05の講義は完了。P05-5の実会社S1/S2は未達**。学習はP06-1へ進み、別の根拠/許可Gateが整うまで会社の実権限を増やさない。

**34枚の本番プレゼン**：第6枚の一般向け概念解説と第33枚の3本並行ロードマップを加え、旧33枚目の締めは第34枚へ。43分＋15分質疑＋2分余裕。**93枚の詳細保存版**：P05-3/4/5とマイルストーンの4枚（90〜93）を追加し、全93枚の日本語原稿を維持。
