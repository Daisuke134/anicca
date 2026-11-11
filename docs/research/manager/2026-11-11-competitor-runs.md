> 本書は 2026-11-11 Manager eval 研究3文書セットの1つ: [BehaviorBench 実走](2026-11-11-behaviorbench-run.md) ／ [競合の実走と理解](2026-11-11-competitor-runs.md) ／ [フロンティアラボ eval 調査](2026-11-11-frontier-eval-survey.md)

# 競合モデル・競合プロダクトの実走と理解 — 2026-11-11

本人の直接指示（2026-11-11 14:31–14:34 JST）による Manager eval 拡張。
順序は本人の確定どおり: **実走 → 理解 →（数字が出てから）記事**。走らせていない対象について
記事は書かない（本人が「disrespect」と明言）。数字は分母・条件・出典つきでのみ記録する。
ベンダー自己申告の数字は「ベンダー申告」と明記し、自社実測と混ぜない。

既走行中の土台（本書は二重実行せず接続するだけ）:
`behaviorbench-run-2026-11-11.md`（Be.FM 1.5-4B run3 / Qwen3-4B run2、ローカル推論
サーバー 127.0.0.1:8000、ハーネスは `behaviorbench_eval/`）。

## サマリー

| 対象 | 正体 | 走行可否 | 数字 |
|---|---|---|---|
| 人間ベースライン | BehaviorBench 内の実人間200人/ゲームの分布そのもの | **実走（算出）済み** | §1（全9ゲーム） |
| MiroFish | OSS 群知能ソーシャルシミュレーション（OASIS ベース） | 条件付き可（§2） | 実行結果を §2 に追記 |
| Simile | 行動基盤モデルの企業（Stanford 発） | 不可（公開アクセスなし） | 公開論文の数字を §3 |
| Artificial Societies | 合成オーディエンス SaaS（YC W25） | 不可（有料＋要サインイン） | ベンダー申告を §4 |
| Aaru | 合成人口シミュレーション企業（旗艦モデル Lumen） | 不可（公開 API なし） | ベンダー申告を §5 |
| Humans& | 人間中心フロンティア AI ラボ（モデル Ampersand） | 不可（API キー取得にサインイン必須＋有料） | §6 |

---

## 1. 人間ベースライン（実走＝算出済み）

### 設計
BehaviorBench の game_behavior 9ゲームは各「1プロンプト × 実人間200人の行動」で構成される。
この実人間分布そのものを予測側に立てる split-half アームを、人間同士の到達点（上限の物差し）
として算出した。モデルアームと同じハーネス自身の関数 `wasserstein_with_ks_test` と
同じ clip / normalize 設定（tasks_config.yaml）で採点した。

- プロトコル: 200人の行動を無作為に分割し、50人を「予測サンプル」、残り150人を参照分布とする。
  200回反復（seed=20261111）の平均±標準偏差。KS pass は p≥0.05 の割合。
- モデルアームとの条件差（明記）: モデルは「50サンプル vs 全200人」で採点される。
  人間アームは予測側が参照に含まれない独立分割（50 vs 150）であり、自己採点の有利さを含まない。
- スクリプト: `bb-work/human_baseline_split_half.py`、生結果: `bb-work/human_baseline_games.json`

### 結果（Wasserstein 距離は小さいほど良い。KS pass は高いほど良い）

| ゲーム | 人間 n | 人間行動 平均±SD | 人間アーム W ± SD | KS統計量 | KS pass率 |
|---|---|---|---|---|---|
| bomb | 200 | 45.56 ± 23.09 | 4.46 ± 1.75 | 0.103 | 0.99 |
| dictator | 200 | 24.71 ± 19.19 | **3.43 ± 1.59** | 0.103 | 0.98 |
| guessing | 200 | 35.47 ± 21.51 | 4.46 ± 1.78 | 0.109 | 0.98 |
| public_goods | 200 | 8.91 ± 6.07 | 5.62 ± 2.49 | 0.084 | 1.00 |
| push_pull | 200 | 0.57 ± 0.50 | 6.85 ± 5.14 ※ | 0.000 | 1.00 |
| trust_banker | 200 | 55.90 ± 37.40 | 4.51 ± 2.04 | 0.107 | 0.98 |
| trust_investor | 200 | 42.19 ± 39.89 | 6.23 ± 3.67 | 0.113 | 0.96 |
| ultimatum_proposer | 200 | 44.92 ± 18.33 | 3.75 ± 1.42 | 0.095 | 0.98 |
| ultimatum_responder | 200 | 33.29 ± 17.80 | 3.66 ± 1.34 | 0.103 | 0.99 |

※ push_pull は行動が 0/1 で、設定上の normalize（[0,1]→[0,100]）により W が100倍スケールで
表示される（実質の分布差は約 0.069）。KS 統計量 0.000 はハーネスの bin 幅 10 の平滑化により
0/1 の両値が同一 bin に落ちるためで、人間アーム・モデルアームに等しく適用される仕様。

### 同条件のモデル数字との接続（dictator、n=50 サンプル）
- 人間アーム: W = 3.43 ± 1.59、KS pass率 0.98
- Qwen3-4B（run2 実測）: W = 20.275、KS統計量 0.690、KS pass = 0
  （モデル行動は全50サンプルが 40.0 に一点集中。人間分布の平均 24.7・SD 19.2 と大きく乖離）
- Be.FM 1.5-4B: run3 で dictator は未実行（2026-11-11 14:45 JST 時点で pers_score_pred 実行中）。
  到着次第 `behaviorbench-run-2026-11-11.md` 側に記録される。

読み: 分布レベルの物差しでは「人間並み」は W≈3–6・KS pass ≈1.0 の帯であり、
現行の汎用モデル（Qwen3-4B）は dictator でその約6倍の距離にいる。

### Big Five 側（個人レベル）に人間アームが作れない理由
surv_resp_pred / pers_score_pred の公開データは同一人物の再測定（test-retest）を含まないため、
「人間が自分自身をどれだけ再現できるか」はこのデータからは算出できない（未算出、と明記する）。
文献側の上限値は §3 の Park et al. (2024) が一次情報として存在する（2週間後の自己再現との比較で 85%）。

---

## 2. MiroFish

### 確定した正体
- オープンソースのマルチエージェント・ソーシャルシミュレーションエンジン。
  リポジトリ: github.com/666ghj/MiroFish（本日 shallow clone で実在と中身を実測。約84K stars と
  複数の二次情報が一致）。ライセンス **AGPL-3.0**。
- 仕組み: 種文書 → 知識グラフ化 → ペルソナと記憶を持つエージェント生成 → Twitter 型と
  Reddit 型の2つの模擬プラットフォーム上で投稿・反応を多ラウンド回す → レポート生成。
  シミュレーション核は CAMEL-AI の **OASIS**（Apache-2.0）。
- 開発者は Guo Hangjiang（BaiFu）。Shanda Group のインキュベーション支援を README が明記。
- **予測精度の公開検証は存在しない**（複数の独立レビューが一致: 公式リポジトリに backtest なし。
  唯一の第三者実測（2026-05-14 の取引日）では S&P500 の方向を外し、当日の上昇上位5銘柄を1つも当てなかった）。
- 注意: mirofish.my 等の同名有料サイトはプロジェクト公式ではない（独立サービス）。

出典: https://mirofish.co.uk/guides/what-is-mirofish ／ https://intnews.it/en/en-mirofish-swarm-ai/ ／
https://geeksaroundglobe.com/mirofish-fact-or-hype ／ リポジトリ実物（bb-work/mirofish/）

### 走行の形（実物コードの実読で確定）
- 本体パイプライン（文書→グラフ→ペルソナ生成）は **Zep Cloud の API キーが必須**
  （`app/config.py` が未設定をエラー扱いし、graph_builder / simulation 準備の全体が Zep 経由）。
  Zep は無料枠があるが、キーの取得は app.getzep.com でのサインアップ（ブラウザ操作）が必要で、
  本委任の実行環境からは取得できない。
- 一方、シミュレーション実行段（`backend/scripts/run_twitter_simulation.py` 等の OASIS ランナー）は
  Zep を import せず、simulation_config.json ＋ twitter_profiles.csv ＋ OpenAI 互換 LLM で単独実行できる。
  → **実行段のみを、プロファイルを自作して走らせる**のが無料で可能な実走形。
- 条件の違い（明記）: これは MiroFish のフルパイプライン（自動ペルソナ生成を含む）ではなく、
  その心臓部である OASIS 実行段の実走である。MiroFish のタスク形式はソーシャルシミュレーションであり、
  BehaviorBench の被験者単位の予測タスクとは形式が異なるため、BehaviorBench の数字とは同列に並べない。
  実走で得るのは「何エージェント・何ラウンドが・どれだけの時間とトークンで回り、何が出力されるか」の運用実測。

### 実行ステータス
- 依存: 固定版 camel-oasis==0.2.5 は Python <3.12 必須で本機（3.12）に入らない。
  後継 0.2.6 + camel-ai==0.2.78 を --no-deps で導入し不足分を補う形で準備中。
- LLM: ローカル推論サーバー 127.0.0.1:8000 は Be.FM run3 が使用中（単一書き手の原則で触らない）。
  run3 の終了後に同サーバーで実行する。
- （実行結果はここに追記する）

---

## 3. Simile

### 確定した正体
- 人間行動の基盤モデルを作る企業。CEO は Joon Sung Park（Stanford の Generative Agents
  論文の筆頭著者）。実在の人物のデジタルツインを作り、企業が価格・製品・メッセージの
  意思決定を実顧客の前にシミュレーションで試すための基盤を提供する。顧客として
  CVS Health、Wealthfront、Banco Itaú、Suntory、Gallup が公式サイトに明記。
- 資金: 累計 $300M 超、直近は $2B 評価（二次情報の一致）。Gallup と提携し大規模な実人間
  データで検証する体制を公式に掲げる（週次で実人間と照合、7,000 件超の評価）。

出典: https://www.simile.com （公式、2026-11-11 実読）／
https://www.generalist.com/p/a-portrait-of-eight-billion-people ／ http://theairankings.com/best-ai-synthetic-research/

### 走行可否: **不可**
公式サイトに公開 API・公開モデル・セルフサーブのデモは無く、エンタープライズ契約のみ。
無料で同条件実行する経路は存在しない。

### 代替（公開一次情報の実読）
- 創業の根拠論文 Park et al. (2024) "Generative Agent Simulations of 1,000 People":
  2時間のインタビューから作ったエージェントが、本人の General Social Survey 回答を、
  **本人が2週間後に自分を再現する精度の約85%** で再現した（n=1,052、一次論文）。
  これは §1 で「このデータからは算出できない」とした個人レベルの人間上限を、別データで
  実測した一次情報であり、Manager eval の人間上限の参照値として使える。
- ベンダー申告: ツインの精度「85%〜99%」（対象集団により変動、自社申告）。
- 独立した反証側の一次情報: Pew Research Center（2026-09）の大規模検証では、AI 生成の
  調査回答は実人間の結果と平均12ポイント乖離した（Simile 自体を対象とした検証ではない）。

---

## 4. Artificial Societies

### 確定した正体
- 合成オーディエンス（互いに影響し合う AI ペルソナのネットワーク）で調査・フォーカス
  グループ・ conjoint 等を代替する SaaS。2024 年創業（James He ら）、YC W25。
  旗艦は LinkedIn オーディエンスを模す "Reach"。公式サイトは「3m+ personas」を掲げる。

出典: https://societies.io （公式、2026-11-11 実読）／
https://github.com/saraswatayu/facet/blob/HEAD/research/synthetic-user-tools-landscape.md ／
https://www.syntheticmarketresearch.com/providers/artificial-societies

### 走行可否: **不可**
有料 SaaS（二次情報で $40/月〜）＋アカウント必須。MCP コネクタ（mcp.societies.ai）も
サインイン必須。API への新規支払い禁止のルール下では走らせない。

### 代替（公開情報の実読）
- ベンダー申告: 公式サイトは「86% distribution accuracy（1,000 パネルで人間の自己再現と同等）」
  を掲げる。第三者まとめでは「1,000 件の実調査で模擬分布と人間分布の重なり 86%」とされるが、
  いずれも供給者申告であり独立検証ではない。
- 二次情報の検証値: ソーシャルメディア成果の予測で 80%+（汎用 LLM は 62.5%）という
  YC 経由の数字も供給者申告。

---

## 5. Aaru（2026-11-11 14:34 JST に本人が追加指定）

### 確定した正体
- 合成人口シミュレーション企業（NY、2024年3月創業: Cameron Fink、Ned Koh、John Kessler）。
  旗艦モデルは **Lumen**。数千の AI エージェントで人口を構成し、製品・価格・政策・
  選挙への反応を予測する「予測エンジン」を企業と政治キャンペーンに提供する。
  顧客・提携: Accenture（出資も）、EY、Interpublic Group、政治キャンペーン。
- 資金: Series A（2025-12、Redpoint 主導）で $50M 超、見出し評価額 約$1B（混合評価額は
  それ以下との報道）。ARR は $10M 未満と報じられている。TIME Best Inventions 2026 選出。
- 単価の二次情報: 約 $0.08 / シミュレーション、月 300 万回超の実行（供給側に近い報道値）。

出典: https://apis.io/providers/aaru/ ／ https://startup.genisisiq.com/aaru-779a3f/ ／
https://joincairo.com/blog/what-is-a-large-behavior-model ／
https://thisnewsroom.com/aaru-ai-human-behavior-time-best-inventions/

### 走行可否: **不可**
「Aaru currently exposes no public developer API」（apis.io の実測プロファイル）。
公開モデル・無料枠・セルフサーブは無く、エンタープライズ提供のみ。

### 代替（公開情報の実読。すべてベンダー申告またはそれに依拠する報道）
- 2024年6月の NY 民主党予備選を **371票差以内** で予測（Semafor 報道を Research Live が引用）。
  約5,000回の AI 対話で構成されたとされる。
- 2026年9月の自社検証（ベンダー公開）: 2,993 件の質問で MAE 3.53 ポイント、
  Pearson 相関 0.970（独立検証ではない）。
- ブランド対の順位付け 92.4%（自社申告）。EY の富裕層調査の再現で元調査と 90% 超の
  相関（提携先経由の申告）。
- 注意: いずれも「自社が選んだ題材での自社申告」であり、held-out の独立検証は公開されていない。
  Manager eval との差はここ（我々は分母と条件を公開して測る）。

---

## 6. Humans&

### 確定した正体
- 「人間中心のフロンティア AI ラボ」（humansand.ai）。2025年10月法人登記、2026年1月公表。
  創業者は Andi Peng（Anthropic）、Georges Harik（Google 初期）、Eric Zelikman・Yuchen He
  （xAI）、Noah Goodman（Stanford）ら。シードで **$480M を $4.48B 評価** で調達
  （NVIDIA、Jeff Bezos、GV、Emerson Collective 等）。
- 最初のモデル **Ampersand v0.1**（2026-10 公表）: グループチャットの協働モデル。
  ベースは Z.ai のオープンウェイト **GLM 5.3**（744B MoE、約40B 活性、文脈 1M）。
  長期の多人数シミュレーション内での RL で訓練され、シミュレーション内のユーザーは
  自社モデル **Persimmon**（実人間のように振る舞うよう作られたユーザーモデル）が担う。
  ※ 本人の "human and ampersand" は Humans& とそのモデル Ampersand の両方を指すと確定できる。
- Ampersand は API 提供のみ（ampersand.humansand.ai でキー発行、$1.00 / 1M 入力トークン、
  $5.20 / 1M 出力トークン）。ウェイト公開は無い。Persimmon は外部提供なし。

出典: https://humansand.ai/ ／
https://madrobot.blog/2026/10/20/humans-and-ampersand-v0-1-first-model-glm-5-3-zai-chinese-open-model/ ／
https://anyrouter.dev/blog/releases/2026-11-08 ／ https://startup.genisisiq.com/humans-and-59da32/

### 走行可否: **不可**（本委任の範囲では）
- API キーの取得にブラウザでのサインインが必要（本委任の実行環境では操作不可）。
  かつ単価は有料が原則（API への新規支払い禁止に抵触）。
- 二次情報では Vercel AI Gateway 経由で 2026-11-13 まで無料提供とされるが、これも
  アカウント操作（BYOK 設定）を要し、本委任では実行できない。ブラウザ作業としての
  申し送り事項とする。
- 形式の違い（明記）: Ampersand は協働モデルであり、BehaviorBench の被験者単位の
  行動予測タスクとは目的が異なる。仮に API が使えても、同条件比較の意味は
  「汎用大規模モデルとして Big Five・ゲーム課題にどう答えるか」の一点に限られる。

---

## 7. 既存アームとの接続（要約のみ。正本は behaviorbench-run-2026-11-11.md）

同条件（surv_resp_pred、Accuracy_averaged、n=20 サンプル）:
- Qwen3-4B（run2）: 0.4375
- Be.FM 1.5-4B（run3、2026-11-11 05:30 UTC 保存の出力）: 0.3542
- 人間上限: 本データからは算出不能（§1）。文献参照値は Park et al. 2024 の 85%（§3）。

run3 は pers_score_pred・dictator が残っており実行中。本書の人間アーム（§1）が、
到着する Be.FM の dictator 数字の物差しになる。

---

## 8. サインアップ実走の追加確認（2026-11-11 14:53 JST）

本人の直接指示「サインアップして何でもできるはずだ」を受けた追加確認。結論を先に書く:
**登録そのものは未完了**。理由は「経路が無い」ではなく、Humans& の登録が対話型ブラウザ
（WorkOS AuthKit のホスト型ログインページ）での操作を必須とし、本サブエージェントには
ライブブラウザ操作の権限が無いためである。以下は実測で確定した経路と、ブラウザ担当へ
渡す正確な次段である。3社とも、無料枠を超える支払い・カード登録の段には進んでいない。

### 8.1 Humans&（Ampersand）— サインアップ経路は実在する
- コンソール ampersand.humansand.ai のログインは、WorkOS AuthKit のホスト型ページ
  **login.persimmon.humansand.ai**（client_id `client_01M211GB6GEDHBX1G92N518TB5`）へ
  リダイレクトする。同ページに「Continue with email」「Continue with Google」「Sign up」が
  あることを実測で確認した。AuthKit の JS バンドル実読でも `https://api.workos.com` への
  接続が確認でき、アプリ固有の API として `/api/radar-signals` が見つかった。
- コンソール側の API は `/api/keys`・`/api/overview`・`/api/top-ups`・`/api/features` が
  観測されている（§6 の「キー発行は ampersand.humansand.ai」と整合）。
- **ブラウザ担当への申し送り（正確な次段）**: (1) 上記 AuthKit ページで
  anicca-agent@inkboxmail.com を使いメール経路で Sign up する（Google 経路は使わない）。
  (2) 確認メール／コードは Inkbox 経由でエージェント側で完結させる。(3) ログイン後に
  Keys 画面（/api/keys 相当）で API キーを発行する。(4) 発行できたら即座に anicca-ops の
  credentials.json へ書き込み、読み戻し確認まで行う（報告はファイル名・サービス名・
  書いた項目名のみ）。(5) 無料クレジットの範囲でのみ BehaviorBench を小規模実走する。
  **/api/top-ups での課金・カード登録が必要な段に来たら、そこで止めて門として記録する**
  （API 新規支払い全面禁止は本委任でも不変）。
- したがって §6 の判定は「経路なし」ではなく「**経路は実在するが、対話型ブラウザでの
  登録完了が前提**」へ置き換える。実走数字はキー取得後にのみ記録する。

### 8.2 Artificial Societies — セルフサーブ登録の入口は見つからなかった
- 公式 societies.io の実読で見つかった導線は `/daily-demo` と `/solutions#book-demo`
  （いずれもデモ予約＝営業連絡）のみで、サインアップ／無料トライアルの入口は無かった。
- ドメイン実測: societies.ai は HTTP 200、mcp.societies.ai のルートは 404、
  app.societies.ai／app.societies.io は接続が確立しなかった（curl で 000）。
- よって現時点の正確な記録は「**公式サイト上にセルフサーブの登録・無料トライアル経路は
  確認できない。開いているのはデモ予約のみ**」であり、§4 の「有料＋要サインイン」は
  この形へ更新する。デモ予約は営業連絡であり、エージェントが完結できる無料実走ではない。

### 8.3 Simile — 変更なし（申し込み経路は営業連絡のみ）
- 公式サイトに API・リサーチアクセスのセルフサーブ登録は無く、「Request demo」の
  モーダル（営業連絡）のみ、という §3 の確認は追加調査でも変わらなかった。
- 記録: **登録して走らせる対象が存在しない**。営業連絡のみという事実をもって門とする。
