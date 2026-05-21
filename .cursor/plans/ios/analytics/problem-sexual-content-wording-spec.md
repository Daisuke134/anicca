## iOS v1.4.0 Spec: 「porn_addiction」表記の心理安全性改善（削除せず、言い換え）

> 作成日: 2026-01-26  
> ステータス: Draft  
> 対象ブランチ: `cursor/porn-addiction-wording-c766`  

---

## 概要

オンボーディング等の「悩み（ProblemType）」一覧に含まれる `porn_addiction` は、機能価値が高い一方で、**露骨な語（porn/ポルノ）**が初見ユーザー（特に女性・宗教観が異なる層）に「怖い/治安が悪い/自分向けではない」という印象を与え、離脱要因になり得る。

本Specでは `porn_addiction` を **削除しない**（後方互換・機能価値を維持）一方、UIや通知文面上の表現を **中立語**に寄せ、心理安全性を上げる。

---

## 受け入れ条件

| # | 条件 | 期待結果 |
|---|------|----------|
| 1 | オンボーディングの悩み一覧 | `porn_addiction` が一覧に残り、表示名が露骨でない（porn/ポルノという語が表示されない） |
| 2 | Profile の「Current Struggles（今の悩み）」等の表示 | 同様に露骨語が表示されない |
| 3 | Nudge（通知/カード） | `porn_addiction` 関連のテキストで porn/ポルノ を原則使用しない（中立語へ置換） |
| 4 | 後方互換性 | `ProblemType.pornAddiction.rawValue == "porn_addiction"` を維持（保存済みユーザーの `problems` が壊れない） |
| 5 | UI/UX | レイアウト・色・フォント・間隔は変更しない（文言のみ変更） |

---

## As-Is（現状）

| 項目 | 現状 |
|---|---|
| データキー | `ProblemType.pornAddiction = "porn_addiction"`（保存/同期のキー） |
| 表示名 | `Localizable.strings` の `problem_porn_addiction = "Porn addiction" / "ポルノ依存"` |
| オンボーディング | `StrugglesStepView` の options 配列に `"porn_addiction"` があり、`Text(NSLocalizedString("problem_\(key)", ...))` で表示 |
| 文面 | `nudge_porn_addiction_*` / `deepdive_porn_addiction_*` 等で porn/ポルノ が多用される |

---

## To-Be（変更後）

### 1) 表示名（Problemラベル）を中立化（キーは維持）

| 言語 | キー | 変更前 | 変更後（推奨） |
|---|---|---|---|
| en | `problem_porn_addiction` | Porn addiction | **Compulsive sexual content** |
| ja | `problem_porn_addiction` | ポルノ依存 | **性的コンテンツの過剰視聴** |

> 意図: 「porn/ポルノ」を避けつつ、対象が伝わる中立表現にする。  
> 注意: `rawValue` やキー名（`problem_porn_addiction`）は後方互換のため変更しない。

### 2) 付随テキスト（DeepDive / Nudge）も同じ語彙に揃える

「一覧は中立なのに、次の画面で突然 porn/ポルノ が出る」状態を避けるため、`porn_addiction` に紐づく文字列は中立語へ置換する。

#### 英語（方針）

| 種別 | 置換方針 |
|---|---|
| 質問文 | “watch porn” → “view sexual content” / “consume sexual content” のように言い換える（自然な英語に調整） |
| 解説文 | “Porn is …” → “Sexual content can become …” のように一般化し、説教/烙印感を下げる |
| タイトル | “Beat the Urge” は維持可（露骨語がないため） |

#### 日本語（方針）

| 種別 | 置換方針 |
|---|---|
| 質問文 | 「ポルノを見る」→「性的コンテンツを見てしまう」等（非難語を避ける） |
| 解説文 | 「ポルノは〜」→「性的コンテンツは〜」または「性的コンテンツに逃げるのは〜」 |

---

## To-Be チェックリスト

| # | 変更内容 | ファイル/対象 | 完了 |
|---|---|---|---|
| 1 | `problem_porn_addiction` の表示名変更（en/ja） | `aniccaios/aniccaios/Resources/*/Localizable.strings` | [ ] |
| 2 | `deepdive_porn_addiction_*` の文言中立化（en/ja） | 同上 | [ ] |
| 3 | `nudge_porn_addiction_*` の文言中立化（en/ja） | 同上 | [ ] |
| 4 | 露骨語（porn/ポルノ）が UI に残っていないか確認 | オンボーディング/プロフィール/カード | [ ] |

---

## テストマトリックス（実装時）

| # | To-Be | テスト名/方法 | 期待結果 |
|---|---|---|---|
| 1 | 表示名が中立化される | 手動: Onboarding `StrugglesStepView` を確認 | “porn/ポルノ” が表示されない |
| 2 | DeepDive 質問が中立化される | 手動: `porn_addiction` の DeepDive を表示 | “porn/ポルノ” が表示されない |
| 3 | Nudge文面が中立化される | 手動: `porn_addiction` のカード/通知文を確認 | “porn/ポルノ” が表示されない |
| 4 | 後方互換が維持される | Unit（推奨）: `ProblemType.pornAddiction.rawValue` を検証 | `"porn_addiction"` のまま |

---

## E2E シナリオ（Maestro）

新規E2Eは不要（UI導線/レイアウト変更なし）。既存フローで確認する。

| # | フロー | 追加/変更 | 検証項目 |
|---|---|---|---|
| 1 | `maestro/01-onboarding.yaml`（または同等） | 変更なし | 悩み一覧に該当チップが表示され、文言が中立化されている |

---

## Skills / Sub-agents

| ステージ | 使用するもの | 用途 |
|---|---|---|
| Spec作成 | `/plan` | 実装計画の整理 |
| 実装 | （通常フロー） | ローカライズの更新（UIは触らない） |
| テスト | `/tdd-workflow` | 文字列/後方互換の最小ユニットテスト追加（任意） |
| コードレビュー | `/code-review` | 文言の一貫性・影響範囲レビュー |
| ゲート | `/codex-review` | コミット前の自動レビュー |

---

## 境界（Boundaries）

### 触るファイル（予定）

| 種別 | パス |
|---|---|
| iOS ローカライズ | `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings` |
| iOS ローカライズ | `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings` |

### 触らない（今回スコープ外）

| 種別 | 理由 |
|---|---|
| `ProblemType` の rawValue 変更 | 後方互換を壊すため（保存済み `problems` が壊れる） |
| UIレイアウト変更 | ルール上禁止（文言のみ） |
| Backend（`apps/api`）の文言/生成 | 今回は iOS アプリ内の表記改善に限定（必要なら別Spec） |

---

## ローカライズ（変更リスト）

### 変更対象キー（最低限）

| カテゴリ | キー（prefix） | 備考 |
|---|---|---|
| ラベル | `problem_porn_addiction` | 表示名 |
| ボタン | `problem_porn_addiction_*_button` | 露骨語が入る場合のみ調整 |
| 通知タイトル | `problem_porn_addiction_notification_title` | 露骨語がなければ維持可 |
| Nudge | `nudge_porn_addiction_*` | 置換対象 |
| DeepDive | `deepdive_porn_addiction_*` | 置換対象 |

### 置換ルール（ガイド）

| 言語 | NG | OK（推奨） |
|---|---|---|
| en | porn | sexual content / adult content（文脈により） |
| ja | ポルノ | 性的コンテンツ |

---

## ユーザー作業（実装前/中/後）

### 実装前

| # | タスク | 手順 | 取得するもの |
|---|---|---|---|
| 1 | なし | - | - |

### 実装中

| # | タイミング | タスク | 理由 |
|---|---|---|---|
| 1 | 文言変更後 | 目視確認 | 自動テストではニュアンス確認が難しい |

### 実装後

| # | タスク | 確認項目 |
|---|---|---|
| 1 | 目視確認 | Onboarding/プロフィール/カードで露骨語が残っていない |

---

## 実行手順（実装時）

| # | コマンド | 目的 |
|---|---|---|
| 1 | `cd aniccaios && fastlane test` | 変更箇所に関連するテスト実行（推奨） |
| 2 | `maestro test maestro/01-onboarding.yaml` | Onboardingの表示確認（任意） |

---

## レビューチェックリスト

| # | 観点 | チェック |
|---|---|---|
| 1 | 後方互換 | `rawValue` と保存キーが維持されている |
| 2 | 露骨語の残存 | UI/通知/DeepDiveに porn/ポルノ が残っていない |
| 3 | 自然な言い回し | “sexual content” が不自然な直訳になっていない |
| 4 | 範囲 | `porn_addiction` 以外の問題タイプに影響していない |
| 5 | UI変更なし | レイアウト変更が入っていない（文言のみ） |

---

最終更新: 2026-01-26

