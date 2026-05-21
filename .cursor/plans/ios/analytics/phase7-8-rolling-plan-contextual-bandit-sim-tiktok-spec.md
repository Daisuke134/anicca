# Phase 7/8 Spec: Rolling Plan + Contextual Bandit + Simulation Calibration + TikTok Bridge

> 最終更新: 2026-01-26  
> 対象リリース: 1.4.0  
> 目的: Phase 6（LLM生成）完了後に、Phase 7/8 を「迷いなく実装」できるレベルまで設計を固定する。  
> 注意: **実装コードは書かない（Specのみ）**。UI/UX変更はこのSpecが明示したものだけ。

---

## 概要

| 項目 | 内容 |
|---|---|
| Phase 7（判断） | LLMが「今日/今」の介入を**計画し、実行し、結果で再計画**する（固定スケジュールではない）。 |
| Phase 8（察する） | 選んだ ProblemType の内側で「根本原因仮説」を立て、角度を変えた介入で事後更新する。 |
| コールドスタート対策 | オンボーディング追加質問は増やさず、**探索 + 事前分布 + 合成シミュの候補ふるい**で立ち上げる。 |
| 学習アルゴリズム | **Contextual Bandit（文脈付きバンディット）**を中心に、非定常（人が変わる）へ追随する。 |
| Simulation の役割 | 本番の最終意思決定には使わず、**候補生成/危険排除/探索空間圧縮**に限定する。 |
| TikTok Bridge | TikTokの「3秒維持/完視聴/保存/コメント質」を、アプリの「tap/👍」に近い“表現品質”シグナルとして活用する（ポリシー直移植はしない）。 |

---

## 受け入れ条件（Acceptance Criteria）

| # | 受け入れ条件 | 測定/検証 |
|---:|---|---|
| 1 | **Rolling Plan**（朝の仮プラン + イベント駆動リプラン）の設計が、データモデルとAPI境界まで確定している | Specに To-Be データモデル/フロー/境界がある |
| 2 | Hook（通知）と Content（カード）を分離して学習できる（tap と 👍/👎 を別報酬として扱う） | 既存 `NudgeStatsManager` / `ProblemNotificationScheduler` の userInfo とイベントに整合する設計 |
| 3 | Contextual Bandit の「Context/Arms/Reward」「非定常対応（忘却/窓）」が明確 | Specの表と擬似コードで明文化 |
| 4 | シミュレーションは **校正（ログ再現）** を通過したものだけを候補ふるいに使う | Specに校正プロトコル（Offline replay評価）がある |
| 5 | TikTok側は **既存 `sns-poster`（Blotato+Fal）** を前提に、最小ループ（投稿→計測→Hook候補更新）の境界が明確 | Specに “TikTokはまず表現学習、ポリシー学習は別” の方針がある |
| 6 | 並列worktreeで進める場合の担当範囲・依存関係が明確 | Specに Worktree Plan と「触る/触らないファイル」テーブルがある |

---

## As-Is（現状把握）

| 項目 | 現状（コード確認済み） | 参照 |
|---|---|---|
| 通知スケジュール | `ProblemNotificationScheduler` が ProblemType の schedule に基づき、衝突回避・シフト・有効時間チェックを行い、`NudgeContentSelector` で variant を選びUNNotificationを登録 | `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift` |
| 選択ロジック | `NudgeContentSelector` は Phase6 として **LLMキャッシュとルールベースを交互**で切替。ルールベース側は Thompson Sampling（Beta）で variant を選ぶ | `aniccaios/aniccaios/Services/NudgeContentSelector.swift` |
| 統計/報酬 | `NudgeStatsManager` が scheduled/tapped/ignored/👍/👎 をローカル永続化し、ignored はアプリ起動時に閾値分で判定 | `aniccaios/aniccaios/Services/NudgeStatsManager.swift` |
| LLM Nudge | `/api/mobile/nudge/today` を `LLMNudgeService` が取得し `LLMNudgeCache` に保持 | `LLMNudgeService.swift`, `LLMNudgeCache.swift` |
| TikTok投稿 | リポジトリ内に Blotato+Fal ベースの投稿自動化（TikTok含む）実装とSpecがある | `.cursor/plans/ios/marketing/sns-automation-spec.md`, `.cursor/plans/ios/sns-poster/` |

---

## To-Be（設計）

### 1) “1日のゲームプラン” を固定計画にしない（Rolling / Receding Horizon）

| 要点 | 方針 |
|---|---|
| 朝の計画 | 「その日の仮説としての計画」を作る（出す/出さない、トーン配分、危険時間帯の重点）。 |
| 実行 | 実行は短いホライズン（次の1手〜数手）で行う。 |
| リプラン | **イベント（tap/ignored/👍/👎/時間経過）で即時更新**する。 |
| “今のあなた”優先 | 古い履歴は事前分布、直近イベントが上書きする（非定常）。 |

#### 1.1 データモデル（iOS側に保持する「計画のスナップショット」）

| エンティティ | 役割 | 備考 |
|---|---|---|
| `DailyPlan` | その日（ローカル日付）の「仮計画」 | 例: 3回の介入枠（朝/昼/夜）を持つが、実行は可変 |
| `PlanStep` | 次に試す介入候補（Hook+Content+タイミングウィンドウ） | “実行時刻”ではなく“実行可能ウィンドウ”を持つ |
| `PlanReasoning` | なぜその候補を選ぶか（LLM explanation） | 解析・デバッグ用途。ユーザー表示しない |

※ 実装時は `NudgeStatsManager` の永続化方針と合わせ、UserDefaultsに保存する（Phase 4/5と同じ思想）。

#### 1.2 リプラン条件（擬似コード）

```text
on day_start (e.g., 05:00 local):
  plan = build_initial_plan(context_summary)

on event (nudge_tapped | nudge_ignored | thumbs_up | thumbs_down | time_tick):
  belief = update_belief(event, recent_history)
  plan = replan(plan, belief)

execute next step only within its time window and "notification fatigue" budget.
```

---

### 2) Contextual Bandit（基本からAniccaへの落とし込み）

#### 2.1 定義（Anicca）

| 要素 | 定義 | 例 |
|---|---|---|
| Context（文脈） | その瞬間の特徴量 | 曜日/時間帯/直近nudge結果/ProblemType集合/（将来）推定ムード |
| Arms（選択肢） | 送れる候補の集合 | Hook候補A,B,C… / 送信ウィンドウ候補 / トーン候補 |
| Reward（報酬） | 観測できる成功指標 | Hook: tapped(1)/ignored(0) / Content: 👍(1)/👎(0) |

#### 2.2 目的関数（最適化目標）

| 目標 | 重み | 理由 |
|---|---:|---|
| **Hookのtap率** | 高 | 通知の“届き”がなければ介入が始まらない |
| **Contentの👍率** | 中 | 介入品質（刺さり） |
| **通知疲れ（過多）ペナルティ** | 中 | “苦しみを減らす”の反対（ノイズ・ストレス） |

#### 2.3 非定常対応（“過去のあなた”に縛られない）

| 方針 | 具体 | 理由 |
|---|---|---|
| Forgetting（忘却） | 直近N日/直近Kサンプルを重視（スライディング窓） | 生活は変わる |
| 状態遷移 | “落ち込み/可用性”を潜在状態として推定し、プランを切り替える | 今日は特別にしんどい、が起こる |

#### 2.4 Bandit選択（擬似コード）

```text
given: context x, candidate arms A = {a1..ak}
for each arm ai:
  estimate reward distribution using recent-window stats (with prior)
pick arm using Thompson Sampling (or contextual TS / linear bandit later)
observe reward r (tap or thumbs)
update stats in recent window (forget old)
```

---

### 3) LLM（判断）と Bandit（学習）の統合方針

| コンポーネント | 役割 | 決定 |
|---|---|---|
| LLM | 候補生成・仮説・説明（why） | Phase7の中心。最終選択の“提案者” |
| Bandit | 候補の最終選択（what/when）を現実反応で最適化 | LLMの提案を「候補集合」にして選択 |
| ルールベース | 安全網（害の回避・障害時フォールバック） | 当面は残す（極小核） |

---

### 4) Phase 8: “察する” を ProblemType の内側でやる

| 制約 | 理由 |
|---|---|
| 選んでないProblemTypeにジャンプしない | roadmap準拠。「当たらない」より「安全に深掘り」 |
| 1回で断定しない | 根本原因は隠れ状態。反応で事後更新する |

#### 4.1 根本原因仮説（例：self_loathing）

| 仮説ID | 仮説 | 介入の角度（例） | 観測 |
|---|---|---|---|
| SL-H1 | 完璧主義 | “60点で十分” | tap/👍が上がるか |
| SL-H2 | 比較 | “比較をやめる一手” | 同上 |
| SL-H3 | 過去失敗の反芻 | “出来事と自己を分ける” | 同上 |

---

### 5) Synthetic User Simulation（校正必須・役割限定）

#### 5.1 役割（限定）

| 役割 | OK | NG |
|---|---|---|
| 候補生成/多様化 | ✅ |  |
| 危険表現の除外（安全テスト） | ✅ |  |
| 探索空間の圧縮（上位N候補に絞る） | ✅ |  |
| 本番の最終意思決定（配信） |  | ❌ |

#### 5.2 校正（ログ再現評価 / Offline replay）

| ステップ | 内容 | 合格条件 |
|---:|---|---|
| 1 | 過去ログ（context, arm, reward）を固定し、シミュが reward をどれだけ再現するか測る | 最低ラインを満たすまで本番利用しない |
| 2 | セグメント（ProblemType集合）ごとに誤差を可視化 | 特定セグメントだけズレる場合は分離 |
| 3 | 校正後、候補ふるいにのみ利用 |  |

---

### 6) TikTok Bridge（“表現学習”としてのみ接続）

#### 6.1 指標対応（近似）

| TikTok指標 | 近いAnicca指標 | 用途 |
|---|---|---|
| 3秒維持 / 冒頭視聴維持 | 通知tap率（Hook） | Hook候補の優先順位づけ |
| 完視聴 / 視聴維持 | カード👍（Content） | Content候補の“型”発見 |
| 保存/共有 | “苦しみ減”の代理シグナル | “ビュー最大化”より優先 |
| コメント質 | 安全・慈悲に反してないか | ガードレール改善 |

#### 6.2 実装上の前提

| 項目 | 決定 |
|---|---|
| 投稿 | 既存 `sns-poster`（Blotato+Fal）を前提にする |
| 自動スクロール/自動いいね等 | しない（規約/リスク/不要） |
| まずの最小ループ | “Hookライブラリ更新 → 画像/スライド生成 → 投稿 → 指標集計 → Hook候補更新” |

---

## ローカライズ（JP/EN）

| 項目 | 方針 |
|---|---|
| Spec自体の言語 | 日本語で記述（既存ルール準拠） |
| 実装で追加される文字列 | **原則なし**（計画/学習/ログ中心）。もしユーザーに新しいUI文言を出す場合は `Localizable.strings`（ja/en）を同時追加する |
| TikTok投稿文言 | まず英語中心（既存 `sns-automation-spec` の運用に従う）。日本語は後追いでOK |

---

## 後方互換性（Backward Compatibility）

| 項目 | 方針 |
|---|---|
| 通知userInfo形式 | 既存形式を壊さない（`notificationTextKey`/`detailTextKey` と LLM直書きの両方を維持） |
| Stats保存形式 | `NudgeStatsManager` の永続化キーを変更する場合は移行期間を設ける（2〜3バージョン） |
| 既存のルールベース/TS | 安全網として維持（段階的に比率を下げるのは可） |

---

## エッジケース / 安全性

| # | ケース | 方針 |
|---:|---|---|
| 1 | 通知が多すぎてストレス | “通知疲れペナルティ”を設け、送信上限（Budget）を設計に含める |
| 2 | LLMが危険/攻撃的な文言を生成 | ルールベースのガードレールでブロックし、フォールバックへ |
| 3 | 非定常（生活が変わる） | 忘却（直近窓）で追随。過去の最適を固定しない |
| 4 | TikTokで伸びる表現が「煽り」に寄る | KPIを保存/共有/コメント質へ寄せ、煽り・罪悪感煽りは禁じる |

---

## ユーザー作業（実装前/中/後）

### 実装前

| # | タスク | 手順 | 取得するもの |
|---:|---|---|---|
| 1 | SNS自動投稿の現状確認 | `.cursor/plans/ios/marketing/sns-automation-spec.md` を参照し、Blotato側のTikTokアカウント接続が生きているか確認 | Blotatoの最新Account ID/権限状態 |

### 実装中

| # | タイミング | タスク | 理由 |
|---:|---|---|---|
| 1 | TikTok指標連携を入れた直後 | “取得可能な指標”の確定 | APIで取れない指標に依存すると設計破綻するため |

### 実装後

| # | タスク | 確認項目 |
|---:|---|---|
| 1 | ログ確認 | context/arm/reward が欠損なく記録されているか |
| 2 | シミュ校正 | replay評価が閾値を満たすか（満たさない場合は本番利用しない） |

---

## To-Be チェックリスト（漏れ防止）

| # | To-Be | 完了条件 |
|---:|---|---|
| 1 | Rolling Plan（仮計画 + リプラン） | データモデル/イベント/リプラン条件がSpecで確定 |
| 2 | Contextual Bandit 定義 | context/arms/reward/非定常がSpecで確定 |
| 3 | LLM×Bandit 統合方針 | 役割分担とフォールバックが確定 |
| 4 | Phase 8 根本原因仮説ループ | 仮説→介入→更新のフローが確定 |
| 5 | Simulation 校正 | Offline replay評価の手順と合格条件が確定 |
| 6 | TikTok Bridge | 指標対応/KPI/禁止事項/最小ループが確定 |
| 7 | Worktree並列計画 | 担当範囲/依存/触るファイルが確定 |

---

## テストマトリクス（実装時に作るテストの地図）

| # | To-Be | テスト名（案） | 種別 | 対象 |
|---:|---|---|---|---|
| 1 | Rolling Planのリプラン条件 | `test_replan_onTap_updatesNextStep()` | Unit | Plan engine |
| 2 | 非定常（忘却） | `test_bandit_forgetting_prefersRecent()` | Unit | Bandit stats |
| 3 | Context→Arm→Reward記録 | `test_log_schema_records_context_arm_reward()` | Unit/Integration | Stats/Analytics |
| 4 | Simulation校正（ログ再現） | `test_simulator_replay_accuracy_threshold()` | Integration | API/Sim |
| 5 | TikTok指標→Hook候補更新 | `test_hook_library_updates_from_tiktok_metrics()` | Integration | sns-poster pipeline |

---

## E2E シナリオ（Maestro）

| # | フロー | 目的 | 対応 |
|---:|---|---|---|
| 1 | （N/A） | 本フェーズは主にロジック/計測のため、UI変更が発生しない限りMaestroは追加しない | UI変更が入る場合のみ追加 |

---

## Skills / Sub-agents（使いどころ）

| ステージ | 使用するもの | 用途 |
|---|---|---|
| Spec作成/整合 | `/plan` + `/codex-review` | Specの抜け漏れ防止、レビューゲート |
| Bandit設計/検証 | `architect` | データモデル/非定常/評価設計の決め切り |
| iOS実装（計測/イベント） | `coding-standards` + `tdd-workflow` | 変更範囲のテストから実装 |
| API/Simulation | `tech-spec-researcher` | 校正（replay）評価の設計と実装案 |
| TikTok/投稿 | `content-creator` | Hook/コンテンツ生成の運用設計 |

---

## 境界（Boundaries）

### このSpecでやること（必須）

| 項目 | やる |
|---|---|
| Phase 7/8 の設計固定 | ✅ |
| Worktree分割と依存の明確化 | ✅ |
| 既存コード構造に沿った境界定義 | ✅ |

### このSpecではやらないこと（禁止）

| 項目 | やらない |
|---|---|
| 実装コードの追加/変更 | ❌ |
| UI/UXの勝手な変更 | ❌（Specに明記したもの以外） |
| TikTokの非公式ボット化（自動スクロール等） | ❌ |

### 実装時に“触る可能性があるファイル”（参考）

| ドメイン | ファイル（例） |
|---|---|
| iOS通知/統計 | `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`, `aniccaios/aniccaios/Services/NudgeStatsManager.swift`, `aniccaios/aniccaios/Services/NudgeContentSelector.swift` |
| iOS LLM連携 | `aniccaios/aniccaios/Services/LLMNudgeService.swift`, `LLMNudgeCache.swift` |
| API | `apps/api/src/routes/mobile/*`（追加のみ、後方互換維持） |
| SNS | `.cursor/plans/ios/sns-poster/*`（既存基盤を利用） |

---

## Worktree 並列実装プラン（提案）

> 目的: Phase 7/8 は “設計/計測/バックエンド/シミュ/投稿” が独立しやすいので、Worktreeで安全に並列化する。

| Worktree | 担当（サブエージェント例） | 主タスク | 触るファイル（例） | 依存 |
|---|---|---|---|---|
| wt/spec-phase7-8 | planner + architect | Spec最終化（この文書を更新） | `.cursor/plans/ios/1.4.0/...` | なし |
| wt/ios-logging-bandit | tdd-guide | iOSのログ/イベント/保存スキーマ整備 | `NudgeStatsManager`, `ProblemNotificationScheduler`, Analytics | Spec確定 |
| wt/api-plan-engine | build-error-resolver | 計画/候補APIの追加（追加的変更のみ） | `apps/api/src/routes/mobile/...` | iOSログ設計 |
| wt/sim-calibration | tech-spec-researcher | ログ再現（replay）評価と候補ふるい | `apps/api/...` or `apps/sim/...` | APIログ形式 |
| wt/tiktok-bridge | content-creator | sns-posterでHook実験→指標集計→Hookライブラリ更新 | `scripts/sns-poster/...` | SpecのKPI定義 |

---

## 不確実性（Uncertainty）と決定（Decision）

| 論点 | 不確実性 | 決定 | 理由 |
|---|---|---|---|
| オンボ追加質問 | 追加すると冷スタートが上がるが離脱増の可能性 | **追加しない** | “Proactive”の核。探索+事前分布+推定で勝つ |
| 1日プラン | 固定すると「今」に弱くなる | **Rolling（常時更新）** | “人生はシーケンス、でも今日は揺れる”を両立 |
| TikTok最適化 | ビュー最大化に引っ張られる | **保存/共有/コメント質を重視** | “苦しみ減”の代理シグナルに寄せる |
| ルールベース卒業 | 完全排除は危険 | **安全核として残す** | メンタル領域の害回避が最優先 |

---

## 実行手順（実装開始時）

| # | 手順 | コマンド/作業 |
|---:|---|---|
| 1 | Specレビューゲート | `/codex-review`（blocking 0になるまで） |
| 2 | Worktree作成 | `git worktree add ... -b wt/...` |
| 3 | 変更単位でコミット | 小さくコミット、push |
| 4 | 実装→テスト | 触った範囲だけテスト（CLAUDE.md準拠） |

---

## レビューチェックリスト

| # | 観点 | 確認 |
|---:|---|---|
| 1 | As-Is/To-Beが矛盾していない | [ ] |
| 2 | Hook/Contentの報酬分離がログ設計に落ちている | [ ] |
| 3 | 非定常（忘却）方針が明記されている | [ ] |
| 4 | シミュの役割が「候補ふるい」に限定されている | [ ] |
| 5 | TikTokが“表現学習”であり、ポリシー直移植しないと明記されている | [ ] |
| 6 | 後方互換（userInfo/保存形式）が壊れない | [ ] |

---

## 参考（一次ソース・ロードマップ整合）

| 種別 | リンク | 使いどころ |
|---|---|---|
| Roadmap | `.cursor/plans/ios/proactive/roadmap.md` | Phase 7/8/10/11 の思想 |
| 既存SNS自動化 | `.cursor/plans/ios/marketing/sns-automation-spec.md` | TikTok入口の最小ループ |
| LLMエージェント人工社会 | `https://arxiv.org/abs/2304.03442` | “記憶・反省・計画”の型（ただし本番意思決定には直結させない） |
| MRT/JITAI | `https://pubmed.ncbi.nlm.nih.gov/38887953/` | 反復介入×反応で最適化する科学的土台 |

