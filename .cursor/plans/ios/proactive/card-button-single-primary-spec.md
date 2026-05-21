# Spec: Nudge Card ボタンを「主ボタン1つ」に単純化（EN/JA）

## 概要

| 項目 | 内容 |
|---|---|
| 目的 | Nudge Card 上の **2択ボタンを廃止**し、**主ボタン（ポジティブ）1つだけ**を表示して中央に配置する |
| 背景 | 「選択肢があること自体が苦しみ」になり得るため、介入UIは迷いを最小化する |
| 対象画面 | 通知タップ後の 1枚カード: `NudgeCardView` |
| 対象言語 | EN / JA（文言は既存の `positiveButtonText` を流用し、新規翻訳は原則不要） |

## 受け入れ条件（Acceptance Criteria）

| # | 受け入れ条件 | 期待結果 |
|---|---|---|
| 1 | 2択だった ProblemType でもボタンは **1つのみ**表示 | 右側のゴースト（ネガティブ）ボタンが UI から消える |
| 2 | 1つだけ残るボタンは **中央配置** | ボタンが左右のどちらかに寄らず、中央に見える |
| 3 | タップ時の挙動は従来の「ポジティブ」動作に統一 | `onPositiveAction()` が呼ばれ、`onNegativeAction` は UI 起点で呼ばれない |
| 4 | EN / JA で表示が崩れない | 文言の折返し/はみ出し/レイアウト崩れがない |
| 5 | 全 ProblemType でボタンの見た目が統一されている | 旧「1択デザイン」（フル幅/フォント18/padding16）に揃う |

## As-Is（現状）

| 項目 | 内容 |
|---|---|
| 条件分岐 | `content.problemType.hasSingleButton` により 1択/2択を切替 |
| 2択UI | `twoButtonView` で **左=ポジティブ / 右=ネガティブ（ゴースト）** の2ボタン |
| 文言 | `ProblemType` の `positiveButtonText` / `negativeButtonText`（`Localizable.strings` の `problem_*_(positive|negative)_button`） |
| 例（rumination/反芻） | JA: `problem_rumination_positive_button` = 「今に戻る 🧘」 / `problem_rumination_negative_button` = 「考え続ける」 |

## To-Be（変更後の設計）

### UI/UX 方針

| 項目 | 決定 | 理由 |
|---|---|---|
| ボタン数 | **常に1つ（ポジティブのみ）** | 迷い/自己責めを増やす「選択」を作らない |
| 配置 | **中央（フル幅のため視覚的に中央）** | 2択→1択で左寄りに見える違和感を無くす |
| 文言 | 既存の `positiveButtonText` をそのまま使用 | 翻訳追加なしでEN/JA一貫を保つ |
| ネガティブ側 | **UIから削除**（表示しない/押せない） | 選択肢を作らない目的に一致 |
| 見た目 | **全ケースで旧1択デザインに統一** | 1ボタンになった以上、デザイン差分が迷いを生むため |

### 実装方針（案）

| 項目 | 変更内容（案） |
|---|---|
| `NudgeCardView` | `hasSingleButton` 分岐を廃止し、常に「主ボタン1つ」View を表示 |
| `onNegativeAction` | `NudgeCardView` の public API は **当面維持**（呼び出し側互換のため）。ただし UI 起点では呼ばれない |
| レイアウト | 2択時の横並びをやめ、1つのボタンを中央寄せ。見た目のサイズは「旧 2択の片側に近い幅」を目標（実装時に確認） |
| アクセシビリティ | 主ボタンに `accessibilityIdentifier` を付与（例: `nudge-primary-action`） |

> 注: `ProblemType.negativeButtonText` や `Localizable.strings` の `*_negative_button` キーは **今回の目的（UIから選択肢を消す）に必須ではないため削除しない**。削除は後続の整理タスクで安全に行う（互換性/影響範囲の確認が必要）。

## To-Be チェックリスト

| # | To-Be | 完了 |
|---|---|---|
| 1 | `NudgeCardView` から 2択UI を排除し、主ボタン1つに統一 | [ ] |
| 2 | 主ボタンを中央寄せにする | [ ] |
| 3 | 主ボタンのタップで `onPositiveAction()` のみ呼ばれる | [ ] |
| 4 | EN/JA（少なくとも rumination/obsessive 等）でレイアウト崩れなし | [ ] |
| 5 | 主ボタンに `accessibilityIdentifier` 付与 | [ ] |

## 重複実装の防止（調査結果）

| 観点 | 結果 |
|---|---|
| 類似UI | `NudgeCardView.swift` 内に 1択/2択の両実装が既に存在 |
| 文言キー | `Localizable.strings` の `problem_*_(positive|negative)_button` が既存 |
| 新規コンポーネント要否 | 不要（既存Viewの分岐整理で実現可能） |

## テストマトリックス

| # | To-Be | テスト種別 | テスト名（案） | 対象 | カバー |
|---|---|---|---|---|---|
| 1 | 2択UI排除 | E2E(Maestro) | `nudge_card_single_primary_button.yaml` | `NudgeCardView` | ✅ |
| 2 | 中央寄せ | E2E(Maestro) | 同上（スクショ比較 or 位置の期待を簡易確認） | `NudgeCardView` | ✅ |
| 3 | ポジティブのみ発火 | Unit/XCTest(案) | `NudgeCardViewActionTests`（DIでクロージャ呼び出し回数を検証） | `NudgeCardView` | ✅ |

> 注: 位置の厳密比較は fragile になりやすいので、E2E では「ボタンが1つだけ表示される」＋「識別子が存在」＋「押下で次の状態（例: dismiss/ログ）に遷移」など、安定指標を優先する。

## E2E シナリオ（Maestro）

| Flow | 目的 | 検証 |
|---|---|---|
| `maestro/phase6/04-nudge-single-primary-button.yaml`（新規） | 2択だったケースでボタンが1つのみであること | `nudge-primary-action` が表示され、ネガティブ相当が存在しない |

## Skills / Sub-agents

| ステージ | 使用するもの | 用途 |
|---|---|---|
| Spec作成 | `/plan` | 仕様の明文化 |
| 実装後レビュー | `/codex-review` | Review Gate（blocking が無いこと） |
| UIレビュー | `ui-skills` | 1択の中央配置がUXとして自然か確認 |

## 境界（Boundaries）

### 触るファイル（予定）

| 種別 | パス | 内容 |
|---|---|---|
| iOS | `aniccaios/aniccaios/Views/NudgeCardView.swift` | 2択UIの撤去、主ボタン1つへ統一、中央寄せ、a11y id |
| E2E | `maestro/phase6/04-nudge-single-primary-button.yaml`（新規） | 表示要素の確認（ボタン1つ） |
| Test | `aniccaios/aniccaiosTests/...`（必要なら新規） | 主ボタン動作のみの検証 |

### 触らないファイル

| 種別 | パス | 理由 |
|---|---|---|
| i18n | `Resources/*/Localizable.strings` | 今回は既存 `positiveButtonText` を流用し、文言追加/変更を行わない |
| モデル | `Models/ProblemType.swift` | `negativeButtonText` の削除は影響範囲が広く、別タスクで安全に実施 |

## ローカライズ

| 言語 | 変更 | 理由 |
|---|---|---|
| JA | 変更なし | 表示は既存 `problem_*_positive_button` を使用 |
| EN | 変更なし | 同上 |

## ユーザー作業（実装前/中/後）

### 実装前

| # | タスク | 手順 | 取得するもの |
|---|---|---|---|
| 1 | 変更の最終合意 | 本Specをレビューして「OK」を出す | 合意 |

### 実装中

| # | タイミング | タスク | 理由 |
|---|---|---|---|
| 1 | Maestro 追加後 | 画面のスクショ確認 | 自動テストだけだと見た目の違和感が残り得る |

### 実装後

| # | タスク | 確認項目 |
|---|---|---|
| 1 | 実機/シミュレータ確認 | rumination（反芻）等でボタンが1つ・中央・押下でポジティブ動作になる |

## 実行手順（実装フェーズで使用）

| 種別 | コマンド |
|---|---|
| Unit/Integration | `cd aniccaios && fastlane test` |
| E2E | `maestro test maestro/ --include-tags=nudge`（または該当flow単体） |

## レビューチェックリスト（Reviewer向け）

| # | 観点 | チェック |
|---|---|---|
| 1 | 2択ボタンがUIから消えている | [ ] |
| 2 | 主ボタンが中央で、EN/JAどちらも崩れない | [ ] |
| 3 | `onNegativeAction` がUI起点で呼ばれない | [ ] |
| 4 | a11y id が付与され、Maestroで安定に参照できる | [ ] |
| 5 | 余計なUI/UX変更（色・フォント・余白）が入っていない | [ ] |

