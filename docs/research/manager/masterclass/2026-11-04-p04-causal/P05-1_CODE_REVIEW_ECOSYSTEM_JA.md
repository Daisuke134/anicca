# P05-1 深掘りコード調査｜人間行動AIとOntologyの既存エコシステム（2026-11-04）

**調査の目的**：Managerが持つべき知識と機能を「車輪の再発明なし」で組み立て、手元の公開OSSコードを読み、動作・権限・ライセンス・科学的な主張を区別する。

**実際に実施した範囲**：公式GitHubの6リポジトリのライセンスと部分的な実装読取、EDSL/P05-1/Graphiti型の隔離環境での実行、BCIO OWL解析、Listen Labs公式ドキュメントと匿名401確認、P05-1 4方式の人工データベンチマーク、Manager CoreのPython3.12/3.14互換テスト。本番エージェントや利用者データは変更・送信していない。

## 1. 論点ごとの現実のプレイヤー／知識ネットワーク

| 研究・企業コミュニティ | 代表資産 | 他との関係 | Managerが取り込む要素 |
|---|---|---|---|
| UCL・HBCP/BCIO（Michie, West, Hastingsほか） | BCIO／BCT／COM-B、RCT介入の標準記述 | Ontologyから実証研究を共通表現へ | 行動・動機・文脈・BCT ID |
| Expected Parrot（Hortonら） | MITのEDSLとCoop | Agent/Survey/Modelをプログラム化、モデルや人の回答の比較 | 調査DSL・マルチモデル・実験配列 |
| Zep / Graphiti | Apache2の時間付きGraphiti | episode→entities→facts→temporal/semantic retrieval。Zepは商用運用レイヤ | 期間・出典・矛盾・変更履歴 |
| Palantir | Object/Link/Action/Ontology SDK | 業務Ontologyを実行系へ結び付ける製品。SDKの一部はApache2、backendは商用 | semantic+kinetic分離、セキュリティ、操作の型 |
| Listen Labs | Human API構想、Listen Twins、調査API | 人へのインタビューと顧客予測パネル。公開v1 APIは調査の作成/起動/回答取得 | 実人間の独立検証・調査収集の外部選択肢 |
| Stanford Socrates / SocSci210 | 人間の実験回答データでのLLM追加学習 | 個人回答・分布・未見研究を比較 | 将来の行動モデルベンチマークと学習コード |
| MiroFish / OASIS (CAMEL) | AGPL3のGraph+persona+sim pipeline / Apache2のSNS模擬環境 | MiroFishはOASISを実行エンジンの一部として用いる | 人工集団・ソーシャルネットワーク実験 |
| PyWhy / DoWhy, DoubleML | 因果推論と推定・感度分析のOSS | Ontology/Graphとは別レイヤ。未測定交絡を自動修復しない | 処置効果推定、方法と仮定の明示 |
| Manager Core（自社既存） | 介入・状態遷移・audit/outbox/verify | 現状の権限・実行・証拠の境界を所有 | 内部契約を壊さず、read-only投影で統合 |

注意：人物・企業のつながりはすべて研究成果・公開実装との関係であり、提携、投資、協業が成立したことを意味しない。

## 2. 公式リポジトリとピン留めしたソース

詳細は `evidence/UPSTREAM_CODE_AND_LICENSE_AUDIT.json`。本レポートに第三者リポジトリの全コードは**コピーしない**。

| OSS / SDK | 確認したコード箇所 | ライセンス | 実行内容 |
|---|---|---|---|
| `expectedparrot/edsl` | `edsl/agents/Agent.py`, `edsl/surveys/Survey.py`, `edsl/language_models/Model.py` | MIT | **実際のedsl 1.0.9**で3人の架空Agentが1問に回答（固定test model・network block） |
| `getzep/graphiti` | `graphiti_core/graphiti.py` の `add_episode`/ `search` / `add_triplet`, `nodes.py`, `edges.py` | Apache-2.0 | **実際のgraphiti-core 0.31.2**のEntityNode/Edgeを生成（フルGraphiti ingest/searchは非実行） |
| `HumanBehaviourChangeProject/ontologies` | `bcio.owl`,上位体系、BCT領域 | CC BY 4.0 | 公式OWL2,634 classを解析、7識別子とSHAを検査 |
| `palantir/foundry-platform-python` | README, generated SDK metadata | Apache-2.0 SDKのみ | ソース・LICENSE検査。Foundry tenant無く実API無し |
| `666ghj/MiroFish` | `ontology_generator.py`,`graph_builder.py`,`oasis_profile_generator.py`,`simulation_manager.py`,`simulation_runner.py` | AGPL-3.0 | ソース読取のみ。Zep/LLM/OASISが必要で未実行 |
| `camel-ai/oasis` | `oasis/social_agent/`,`environment/`,`social_platform/`, action types | Apache-2.0 | ソース読取のみ。実SNSシミュレーション未実行 |

### Expected Parrot EDSL：最小コードを実際に動かした

公式の基本構造を踏襲：

```python
from edsl import Agent, AgentList, Survey, QuestionFreeText, Model

agents = AgentList([
    Agent(traits={"group": "synthetic_one"}),
    Agent(traits={"group": "synthetic_two"}),
    Agent(traits={"group": "synthetic_three"}),
])
question = QuestionFreeText(
    question_name="synthetic_feedback",
    question_text="What could improve an entirely fictional service?",
)
survey = Survey([question])
model = Model("test", canned_response="OFFLINE_TEST_MODEL_NOT_HUMAN")
results = survey.by(agents).by(model).run(
    disable_remote_inference=True,
    disable_remote_cache=True,
    cache=False,
)
print(results.select("answer.synthetic_feedback").to_dicts())
```

**行ごとの意味**：`Agent`は架空の回答者属性、`AgentList`は回答者集合、`QuestionFreeText`は自由回答式質問、`Survey`は質問の束、`Model('test')`は固定回答を返す検査用模型（本物の言語モデルや人ではない）、`.by`は調査対象・モデルを組み合わせ、`.run`は処理実行、`.select(...).to_dicts()`は指定回答を辞書形式で取り出す。テストではネットワークのソケット接続もブロックした。

**結果**：3件とも同じ固定文字列。これは機械的なデータフローの確認で、予測精度・人間らしさの証拠ではない。仮想環境Python3.12で `edsl==1.0.9`。外部のモデル・Listen・調査参加者への呼び出しは0。

### Graphiti：コードを正確に読む

`Graphiti.__init__` には graph driver、LLM client、embedder、cross-encoderがあり、デフォルト構成はOpenAI系サービスを想定。`add_episode()`はエピソードの入力と型抽出・Graph追加、`search()`はハイブリッド検索、`add_triplet()`はノード／関係を加える（不足時のembeddingとentity resolutionを含む）。したがって単純に `Graphiti()` を起動するだけで外部依存のないGraphができるわけではない。

今回**実際に動いたのは**実パッケージの`EntityNode`2件＋`EntityEdge`1件の生成・型シリアライズ。初回import時`httpx`が欠落していたため隔離環境に追加インストールして再実行した。Neo4j/FalkorDBや実際の`add_episode/search`は実行していない。これは「動いた範囲」と「読んだ範囲」を分けるためである。

### BCIO：独自の人間行動Ontologyを作り直さない理由

実OWL約2.1MBを解析し2,634クラス宣言を確認した。例：
- `BCIO_006133`: behavioural motivation
- `BCIO_050937`: behavioural goal
- `BCIO_050829`: purchasing behaviour
- `BCIO_007024`: self-monitor behaviour BCT
- `BCIO_051025`: intervention context
- `BCIO_003000`: behaviour change intervention

各IDはURIとともに使用し、ラベルや階層の更新時には元リポジトリのrevision/ライセンスを固定する。OWLの全ファイルを同梱してはいない。CC BYの表示と外部にimportされた語彙のライセンスに注意。

### MiroFish / OASIS：何を借りられるか

MiroFishのコードは `graph_builder → ontology_generator → oasis_profile_generator → simulation_manager → simulation_runner → report_agent`という処理群に分かれる。OASIS側には social agent, agent graph, social platform, database, recommendation logic, actionsが存在する。これらは研究構想を分解して理解するのに非常に有用。

しかし、**多エージェントのSNS内で投稿が拡散したことは、実際のX上で投稿が伸びることの証明ではない**。推薦アルゴリズム、実ユーザーの注意、ネットワーク構造などが異なる。将来は実SNSの結果との外部評価を必要とする。MiroFishはAGPL-3.0、OASISはApache2。AGPLのコードをサービス化・改変する場合の条件は製品公開前にレビューが必要。

### Palantir：コードを読むとOntologyの「価値」は別の層にある

Foundry SDKはApache2で公開されているが、Ontologyの本体バックエンドは同じライセンスで自由に持ち込めるわけではない。公式Ontology概念はobjects, links, actions, functions, dynamic securityという**semantic + kinetic**の橋渡し。Managerでは知識の照会と本当に動かすための**既存のauthority/outbox/verification**を分離し、処置前のWhat-ifに必要な意味の部分だけ連携する。

### Listen Labs：HTTPレベルで確認できたこと

公式公開API：`https://docs.listenlabs.com/api-v2/overview`。実際に**資格情報無しのread-only GET** `https://listenlabs.ai/api/public/v1/wallets` を試し、**HTTP 401 / `missing_api_key`**と応答。調査を開始したりユーザー情報を取得したりしていない。`POST /studies/create`、`POST /studies/{studyId}/launch`、`GET /responses/{linkId}`がドキュメントにあり、launchはwallet project creditsと権限を要する。

Human API・Listen Twinsについての宣伝・機能説明と、この公開調査APIで利用できる機能は**区別**する。現時点で公開の「Twin予測APIエンドポイント」を確認できていないので、Managerのモデル本体をそこへ依存させる設計はしない。本人調査が必要なら、正式な組織APIと参加者の同意に基づく適切な利用を検討する。

## 3. 今回の本当の研究結果：4方式の公正な人工ベンチマーク

**同じ4方式、同じ正解、同じ800問／規模、時点を固定したexact query**を実行した。

| 架空人物数 | イベント数 | 方式 | インデックス構築ms | 検索中央値µs | p95µs |
|---:|---:|---|---:|---:|---:|
| 100 | 491 | Flat | 0.002 | 252.667 | 275.500 |
| 100 | 491 | Dict | 2.046 | 0.333 | 1.208 |
| 100 | 491 | SQLite | 1.574 | 2.834 | 5.750 |
| 100 | 491 | Graph | 0.906 | 0.292 | 1.084 |
| 500 | 2451 | Flat | 0.007 | 1264.875 | 1364.916 |
| 500 | 2451 | Dict | 1.822 | 0.333 | 1.208 |
| 500 | 2451 | SQLite | 6.215 | 3.083 | 6.292 |
| 500 | 2451 | Graph | 4.971 | 0.333 | 1.167 |
| 2500 | 12252 | Flat | 0.021 | 6322.292 | 6911.625 |
| 2500 | 12252 | Dict | 10.333 | 0.500 | 1.625 |
| 2500 | 12252 | SQLite | 32.497 | 3.292 | 6.833 |
| 2500 | 12252 | Graph | 25.335 | 0.500 | 1.750 |

**全方式・各800問の正答不一致0**。23件の再現テストは別途成功。これらの数字は小規模・単一マシン・手作り質問・メモリ内の速度であり、Graphitiの本番Graph DBやユーザーの行動予測を評価していない。

解釈：**Python辞書はGraph投影と同じ速度で、インデックス構築はむしろ短い**。既存の契約・SQLiteがある以上、今は重たいGraph基盤を強制導入しない。Graphitiが本領を発揮する「自由テキストの知識抽出」「意味検索」「更新矛盾」「多段推論」を独立に比較する機会を作ってから決める。

## 4. End-to-end最小実験

`experiments/p05_1_integrated_offline_demo.py`：
```text
EDSL本物のSurvey実行（偽のAgent＋固定test model／ネットワーク接続を遮断）
→ 架空の質問回答
→ 5件の型付きイベント（SHA256、source_fact、valid/recorded時刻）
→ Manager Core準拠のP05-1 read-only temporal projection
→ Flat / Dict / SQLite / Graph から同じ6問へ回答
→ 正解が完全一致
→ 既存Manager StateMachine / InterventionPlan が NO_ACTION と判断
```

**結果**：各バックエンドの6問が一致、人工の証拠ステータス`OBSERVED_SYNTHETIC`, `INFERRED_NOT_VERIFIED`, `PROVIDER_RECEIPT_NOT_OUTCOME`, `INDEPENDENT_READBACK_SYNTHETIC`が混ざらず保持された。外部呼び出し・有償請求・実介入・個人情報0。

**これが示すのは、既存OSSとManager Coreのコンポーネントが実際に接続できること**だけで、Human Behavior Foundation Modelの科学的性能は測っていない。

## 5. 実Manager Coreの互換性バグも実際に見つけた

`products/manager/tests/test_collaboration_authority.py`の1つのテストが、Python3.12では成功し、3.14では4つのsubtest failureとなっていた。

原因は`dataclasses.replace`が`init=False`の改変を拒否するとき、Python3.12では`ValueError`、Python3.14では`TypeError`を送出する差。**どちらも権限昇格を拒否しており、危険な実行が許された問題ではない**。

テストを`assertRaises((ValueError,TypeError))`に変更した。変更後、双方で`44 passed, 15 subtests passed`。許可/実行の本番コードは変更していない。

関連ログ：`evidence/MANAGER_CORE_python312_AFTER_FIX.txt`, `evidence/MANAGER_CORE_python314_AFTER_FIX.txt`。

## 6. No human/user in loop の技術的意味を正確に定義する

「利用者の個人認証情報を毎回要求しない」「すでに許可された限定的な自律業務では人が逐一操作しない」は実装上の達成可能な指標。ただし、**サービス側の管理鍵・必要なアカウント・同意・法的義務・プラットフォーム規約を無かったことにはできない**。Listen Labsは組織鍵が必要で、Palantirはtenant認証が必要。一般利用者のメンタルヘルスに関わる支援や外部から見えにくい行動介入では、本人に何が行われるかを説明し撤回可能にする必要がある。

自社の公開repoは**自身が権利を持つコード、重み、評価ハーネス、コード生成過程や記録を公開可能な範囲で共有**する。第三者が保有する健康情報/権利のないモデル重みをオープン化するものではない。

## 7. 次の実装課題と厳密な測定

最優先はP05-2。既存の`effect_key`、`run_id`、`receipt_ref`、`official_readback_ref`等を結ぶ**参照専用trace**を作る。それが完成しても、実人間での効果は別のRCT/外部再現が必要。

**Graphiti本体を全面採用するかは保留**。使うのなら、free text evidenceから自動抽出された辺の正確さ・矛盾・false merge・検索再現率・訂正履歴・ランニングコスト・時間リークを、平坦な基準と**同条件**でテストする。比較相手が単純なdictで足りるならそれを採用する。

**外部モデル評価**：EDSL+本物のオープンウェイトモデルをローカルで動かす際、モデルのライセンス、匿名化されたデータ、研究単位Holdout、人間の独立正解、推論計算資源を固定し、「test modelが動いた」をモデルの精度と混同しない。

**Listen Labs API**：正式な組織アクセス、適切な同意と費用を確保できたときだけ実人間の調査に使用し、Twins API公開の有無を別に確認する。

## 8. 参照

- EDSL：https://github.com/expectedparrot/edsl ／ https://docs.expectedparrot.com/en/latest
- BCIO：https://github.com/HumanBehaviourChangeProject/ontologies
- Graphiti：https://github.com/getzep/graphiti
- OASIS：https://github.com/camel-ai/oasis
- MiroFish：https://github.com/666ghj/MiroFish
- Palantir：https://palantir.com/docs/foundry/ontology/overview/
- Listen Labs：https://docs.listenlabs.com/api-v2/overview
- Socrates：https://stanfordhci.github.io/socrates/
- DoWhy：https://github.com/py-why/dowhy
- 既存Manager Core：`products/manager/manager_core/`
- 仕様書：`products/manager/docs/specs/2026-11-04-manager-ontology-query-evidence-reuse.md`
- 実行結果・SHA：`evidence/` 配下、コード：`experiments/` 配下
