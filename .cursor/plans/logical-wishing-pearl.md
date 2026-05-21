# mobileapp-builder スキルリファクタリング計画

## Context

mobileapp-builder の reference MD が「THICK」（レシピ全文インライン、170-715行）になっており、skill-creator BP に違反している。修正方針: **thin reference MD → スキルをロード → レシピはスキル内に集約**。これにより単一ソース・オブ・トゥルース、オープンソース向けチェリーピック可、ファクトリー進化時にスキル単体で改善可能になる。

---

## Phase 1: Reference MD Thin 化（T1-T8）

### Thin テンプレート（us-006/us-007 から抽出）

```markdown
# US-XXX: タイトル

## 1. Read First
Load: `skill-name` SKILL.md

## 2. Factory Variables
| Variable | Value |
|----------|-------|
| APP_DIR | ... |

## 3. Quality Gate
| Gate | Command |
|------|---------|
| ... | ... |

## 4. Execution Order
1. ...

## 5. Prohibited
- ...

## 6. Gate Checks
- ...
```

---

### T1: us-001-trend.md thin 化
- **現状**: 378行。トレンド収集・フィルタリングレシピがインライン
- **対象**: `references/us-001-trend.md`
- **移動先**: `idea-generator` スキル（373行、references/ なし）
- **thin 後**: ~40行。「Load: idea-generator」+ 重複チェック + rank1 auto-select + 出力パス
- **Factory 固有で残す**: 重複アプリチェック、AppStore カテゴリフィルタ、spec/01-trend.md 出力

### T2: us-002-planning.md thin 化
- **現状**: 245行。4エージェント構成・I/Oマッピングがインライン
- **対象**: `references/us-002-planning.md`
- **移動先**: `prd-generator` スキル（693行 ⚠️ → T9 で references/ 分割）
- **thin 後**: ~30行。「Load: prd-generator」+ 入力パス + 出力パス + ゲート

### T3: us-003-research.md thin 化
- **現状**: 291行。3ステップ競合分析がインライン
- **対象**: `references/us-003-research.md`
- **移動先**: `competitive-analysis` スキル（392行、references/ なし）
- **thin 後**: ~30行。「Load: competitive-analysis」+ 出力パス + ゲート

### T4: us-004-specs.md thin 化 + 4スキル問題修正
- **現状**: 570行。PRD/ARCH/UX/DS/IMPL/TEST/RELEASE テンプレ全部インライン。4スキル参照（implementation-spec, ios-ux-design, prd-generator, architecture-spec）
- **対象**: `references/us-004-specs.md`
- **修正**:
  - 「迷ったら prd-generator/architecture-spec も読め」を削除
  - テンプレ内容を `implementation-spec` の references/ に移動（→ T9）
  - 必須ロードは 2 スキルのみ: `implementation-spec` + `ios-ux-design`
- **thin 後**: ~60行。「Load: implementation-spec, ios-ux-design」+ 3フェーズゲート + 出力パス

### T5: us-005a-infra.md thin 化
- **現状**: 171行。Privacy Policy URL、PrivacyInfo、ASC app 作成手順がインライン
- **対象**: `references/us-005a-infra.md`
- **移動先**: `asc-signing-setup`（44行）に追記
- **thin 後**: ~40行。「Load: asc-signing-setup」+ iris session check + ゲート

### T6: us-005b-monetization.md thin 化
- **現状**: 402行。IAP作成・RC setup・uiPreviewMode パターンがインライン
- **対象**: `references/us-005b-monetization.md`
- **移動先**: `asc-ppp-pricing` スキル（141行 → T11 で強化）
- **thin 後**: ~40行。「Load: asc-ppp-pricing」+ RC Public Key 取得 + ゲート

### T7: us-008-release.md 分割 + thin 化
- **現状**: 715行。5つのサブUS（008a-e）が1ファイルに
- **対象**: `references/us-008-release.md`
- **分割**:

| サブUS | 内容 | 変更点 |
|--------|------|--------|
| 008a | スクショ撮影 | thin 化のみ |
| 008b | スクショフレーミング | thin 化のみ |
| 008c | メタデータ | thin 化のみ |
| 008d | コンプライアンス | **App Privacy を US-009 から移動** |
| 008e | レビュー | **release-review のみ（TestFlight 分離）** |
| 008f | **TestFlight（新設）** | 008e から分離。ビルド添付→グループ→招待→テストノート |

- **各サブUS**: ~30-50行の thin reference に
- **正しいフロー**: review(008e) → testflight(008f) → submission(009)

### T8: us-009-submit.md thin 化
- **現状**: 132行。App Privacy + submit コマンド
- **対象**: `references/us-009-submit.md`
- **修正**:
  - App Privacy → US-008d に移動（T7 で実施）
  - `asc-submission-health` を「参考のみ」→「ロード必須」に変更
  - `apple-appstore-reviewer` もロード
- **thin 後**: ~40行。「Load: asc-submission-health, apple-appstore-reviewer」+ 依存チェック + submit コマンド

---

## Phase 2: スキル強化（T9-T12）

### T9: implementation-spec スキル強化
- **現状**: 1,123行 ⚠️（500行上限の2倍超）、references/ なし
- **対象**: `.claude/skills/implementation-spec/SKILL.md`
- **修正**:
  1. `references/` ディレクトリ作成
  2. us-004-specs.md から以下を移植:
     - `references/templates.md` — PRD/ARCH/IMPL/TEST/RELEASE テンプレート
     - `references/cross-reference.md` — Cross-Reference Matrix
     - `references/gate-checklist.md` — 3フェーズゲートチェック
  3. SKILL.md 本体を 500行以下に削減（コア手順のみ残す）
- **prd-generator も同様**（693行 → references/ 分割、ただし T2 の移植先なので T2 後に実施）

### T10: release-review + asc-submission-health に修正ループ追加
- **方針**: 2つのスキルは**別々のまま**（ユーザー決定）
- **release-review** (`231行`):
  - 現状: レポート出力のみ
  - 追加: Critical/High 発見 → 修正指示 → 再実行 → 全パスまでループ
  ```
  Report → Critical/High? → YES → Fix → Re-run checklist → Loop
                           → NO  → PASS
  ```
- **asc-submission-health** (`157行`):
  - 現状: 7項目チェック + submit コマンド
  - 追加: FAIL 項目 → 修正 → 再チェック → 全パスまでループ
  ```
  Check 7 items → Any FAIL? → YES → Fix → Re-check → Loop
                             → NO  → Submit
  ```

### T11: asc-ppp-pricing スキル強化
- **現状**: 141行、references/ なし
- **対象**: `.claude/skills/asc-ppp-pricing/SKILL.md`
- **移植元**: us-005b-monetization.md のレシピ
  - IAP 作成手順（availability → pricing 順序ルール）
  - RC プロジェクトセットアップ
  - uiPreviewMode パターン
- **references/ に配置**: 詳細レシピは `references/` に

### T12: idea-generator スキル強化
- **現状**: 373行、references/ なし
- **対象**: `.claude/skills/idea-generator/SKILL.md`
- **移植元**: us-001-trend.md のレシピ
  - トレンド収集（TikTok/Reddit/AppStore）
  - フィルタリング・スコアリング
- **references/ に配置**: 詳細レシピは `references/` に

---

## Phase 3: Polish（T13-T17）

### T13: SKILL.md テーブル更新
- **対象**: `.claude/skills/mobileapp-builder/SKILL.md` L28-49
- **修正**:
  - US-008f（TestFlight）行を追加
  - Skills 列を正確に（「(inline)」表記削除、正しいスキル名に）
  - US-008e の Skills 列 = `release-review` のみ
  - US-009 の Skills 列 = `asc-submission-health, apple-appstore-reviewer`

### T14: Description pushy 化
- **対象**: `.claude/skills/mobileapp-builder/SKILL.md` frontmatter
- **修正**: トリガーキーワード追加（「アプリ作って」「iOS開発」「モバイルアプリ」等）
- **BP**: skill-creator L67 「Claude undertriggers skills; descriptions need explicit trigger keywords」

### T15: WHY なしルールに理由追記
- **対象**: `.claude/skills/mobileapp-builder/SKILL.md` CRITICAL RULES
- **対象ルール**: Rule 3, 12, 14, 16, 17, 18, 38
- **BP**: skill-creator L139 「Explain why things are important in lieu of heavy-handed musty MUSTs」

### T16: scripts/ ディレクトリ作成
- **対象**: `.claude/skills/mobileapp-builder/scripts/`
- **作成ファイル**:
  - `setup-env.sh` — PATH + keychain unlock + .env source
  - `slack-report.sh` — US 完了報告テンプレート
  - `gate-check.sh` — Greenlight + validate.sh 実行ラッパー

### T17: 全15ミニスキル BP チェック
- **チェック項目**:

| チェック | 基準 |
|---------|------|
| 行数 | 500行以下 |
| Description | pushy（トリガーキーワードあり） |
| references/ | 500行超のスキルは references/ で分割済み |

- **既知の違反**:
  - `implementation-spec`: 1,123行 → T9 で修正済みのはず
  - `prd-generator`: 693行 → references/ 分割必要
  - 他13スキル: 500行以下 ✅

---

## 実行順序

```
Phase 1（構造変更）:
  T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8

Phase 2（スキル強化）:
  T9 → T10 → T11 → T12

Phase 3（Polish）:
  T13 → T14 → T15 → T16 → T17
```

**依存関係**:
- T4 → T9（us-004 のコンテンツを implementation-spec に移すので）
- T1 → T12（us-001 のコンテンツを idea-generator に移すので）
- T6 → T11（us-005b のコンテンツを asc-ppp-pricing に移すので）
- T7 → T13（US-008f 新設後にテーブル更新）

---

## 検証方法

| # | 検証 | コマンド/方法 |
|---|------|-------------|
| 1 | 全 reference MD が 60行以下 | `wc -l references/us-*.md` |
| 2 | 全 SKILL.md が 500行以下 | `wc -l` 各スキル |
| 3 | reference MD が正しいスキルをロード | 各ファイルの「Load:」行を確認 |
| 4 | SKILL.md テーブルに US-008f がある | 目視 |
| 5 | release-review に修正ループがある | SKILL.md 内に Loop セクション確認 |
| 6 | asc-submission-health に修正ループがある | 同上 |
| 7 | App Privacy が US-008d にある（US-009 にない） | 両ファイル確認 |
| 8 | US-004 が 2 スキルのみロード | 「迷ったら」削除確認 |

---

## 対象ファイル一覧

### 編集するファイル

| ファイル | タスク |
|---------|--------|
| `references/us-001-trend.md` | T1 |
| `references/us-002-planning.md` | T2 |
| `references/us-003-research.md` | T3 |
| `references/us-004-specs.md` | T4 |
| `references/us-005a-infra.md` | T5 |
| `references/us-005b-monetization.md` | T6 |
| `references/us-008-release.md` | T7（分割） |
| `references/us-009-submit.md` | T8 |
| `.claude/skills/implementation-spec/SKILL.md` | T9 |
| `.claude/skills/release-review/SKILL.md` | T10 |
| `.claude/skills/asc-submission-health/SKILL.md` | T10 |
| `.claude/skills/asc-ppp-pricing/SKILL.md` | T11 |
| `.claude/skills/idea-generator/SKILL.md` | T12 |
| `.claude/skills/mobileapp-builder/SKILL.md` | T13, T14, T15 |
| `.claude/skills/prd-generator/SKILL.md` | T17（500行超修正） |

### 新規作成するファイル

| ファイル | タスク |
|---------|--------|
| `references/us-008d-compliance.md` | T7 |
| `references/us-008e-review.md` | T7 |
| `references/us-008f-testflight.md` | T7 |
| `.claude/skills/implementation-spec/references/templates.md` | T9 |
| `.claude/skills/implementation-spec/references/cross-reference.md` | T9 |
| `.claude/skills/implementation-spec/references/gate-checklist.md` | T9 |
| `.claude/skills/asc-ppp-pricing/references/iap-recipe.md` | T11 |
| `.claude/skills/idea-generator/references/trend-recipe.md` | T12 |
| `scripts/setup-env.sh` | T16 |
| `scripts/slack-report.sh` | T16 |
| `scripts/gate-check.sh` | T16 |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| `ralph.sh` | 外部品質ゲート |
| `validate.sh` | 外部品質ゲート |
| `CLAUDE.md` | テンプレート |
| `prd.json`（テンプレート版） | テンプレート |
