# Anicca Net Suffering Reduction Spec

最終更新: 2026-02-12  
対象: Anicca（iOS + API + OpenClaw運用）  
目的: 収益中心ではなく「苦しみ削減」をプロダクトの第一KPIとして定義・計測・運用する。

---

## 1. Purpose（何を達成するか）

Aniccaの最終目的を以下に固定する。

- **Primary Objective**: `Maximize Net Suffering Reduction (NSR)`
- **Hard Constraints**:
  - SAFE-T優先（危機時は通常自動化を中断）
  - No-harm（短期効果のための有害介入を禁止）
  - Sustainability（継続運用可能な事業性は制約として保持）

補足:
- 売上/継続率は重要だが、目的関数ではなく運用継続の制約指標として扱う。

---

## 2. Why SAFE-T First（なぜSAFE-T優先か）

### 2.1 定義
SAFE-Tは「危機兆候または過激化兆候」を検知した際に、通常の自動介入フローを止め、安全導線へ強制ルーティングする仕組み。

### 2.2 理由
- 人命・心理安全の保護（最優先）
- 高刺激/高圧Nudgeへの最適化暴走を防止
- ミッション逸脱（反応率最適化のための有害介入）を防止
- 長期信頼を維持

### 2.3 実装ルール（必須）
- `severityScore >= threshold` または crisis判定で `safe_t_interrupt`
- `safe_t_interrupt` 発火時:
  - 通常Nudge生成/配信を中断
  - 安全導線（支援情報・人間エスカレーション）を優先
  - `agentAuditLog` に必ず記録

---

## 3. Metric Architecture（指標の階層）

## 3.1 L0: North Star
- **NSR (Net Suffering Reduction)**  
  介入がなかった反実仮想と比較した、苦しみ総量の減少。

## 3.2 L1: Individual Index
- **HSI (Human Suffering Index)** per user per day
  - 主観シグナル（気分・絶望感・孤独感・制御感）
  - 行動シグナル（睡眠崩れ、回避、反芻、衝動）
  - 危機シグナル（SAFE-T頻度/強度）
  - 機能シグナル（学業/仕事/対人の遂行）

## 3.3 L2: Intervention Outcome
- Nudge開封/反応/24h行動変化
- 介入後の短期HSI変化

## 3.4 L3: Sustainability Constraints
- 継続率、解約率、LTV/CAC、粗利
- これらは「目的」ではなく「制約監視」

---

## 4. Data Model v0（既存基盤で始める）

既存テーブル/ログを活用し、最小追加で運用開始する。

- 既存利用:
  - `nudge_events`
  - `nudge_outcomes`
  - `agentAuditLog`
- 新規追加（推奨）:
  - `suffering_measurements`（日次HSIスナップショット）
  - `intervention_attribution`（event-action-outcome連結）

### 4.1 suffering_measurements（推奨スキーマ）
- `id`
- `user_id`
- `measured_at`
- `hsi_total`
- `hsi_subjective`
- `hsi_behavioral`
- `hsi_crisis`
- `hsi_functional`
- `source`（app/survey/inferred）
- `trace_id`

### 4.2 intervention_attribution（推奨スキーマ）
- `id`
- `user_id`
- `event_id`
- `action_id`
- `outcome_id`
- `channel`（app/slack/email/etc）
- `delta_hsi_24h`
- `causal_bucket`（treatment/control/holdout）
- `trace_id`

---

## 5. HSI v0 Scoring（初期計算式）

日次で `HSI_user_t` を算出する（値が高いほど苦しみが強い）。

`HSI_user_t = 0.35*Subjective + 0.25*Behavioral + 0.25*Functional + 0.15*Crisis`

初期ルール:
- 各サブスコアは 0-100 に正規化
- crisisはSAFE-Tイベントがある日に強く加点
- 欠損は前日補間ではなく「不確実性フラグ」を立てる

---

## 6. Causal Measurement（因果推定）

単純相関ではなく、最低限以下で因果評価する。

- A/BまたはHoldout群を設定
- DiD（Difference-in-Differences）で差分推定
- 主要評価値:
  - `Avg Treatment Effect on HSI`
  - `Crisis Rate Reduction`
  - `Sustained Improvement (7/28日)`

---

## 7. Operational Policy（運用ポリシー）

### 7.1 高リスク操作
- `send_email`, `reply_dm`, `post_public`, `transfer_value` は承認ゲート必須
- 初期は `draft_only` をデフォルト

### 7.2 監査
- すべてのactionに `who/why/input/output/traceId`
- 監査ログ欠損時は実行失敗扱い

### 7.3 Kill Switch
- 安全異常・暴走兆候・外部攻撃兆候で即時停止

---

## 8. Weekly Dashboard（週次運用）

毎週、最低以下をレビューする。

- NSR推定値（全体/チャネル別）
- HSI分布（改善/悪化/不変）
- SAFE-T発火数、誤検知、見逃し
- 介入あたり改善量（channel別）
- 有害介入疑い件数
- 事業制約（継続率/解約率）

---

## 9. Milestones（導入順）

### M1（1-2週）
- HSI v0計算を日次バッチ化
- SAFE-Tログの完全監査化
- Nudge結果とHSIを `traceId` で連結

### M2（3-4週）
- Holdout導入
- NSR暫定推定開始
- 週次ダッシュボード運用

### M3（5-8週）
- 重症度別最適化
- チャネル横断の介入配分最適化
- 目的関数を `NSR最大化` に正式移行

---

## 10. Definition of Success

- 主要判定は「売上増」ではなく、以下の同時達成:
  - NSRが継続改善
  - SAFE-Tの安全性能が維持/改善
  - 有害介入が統計的に低水準
  - 制約指標（継続率など）を満たす

