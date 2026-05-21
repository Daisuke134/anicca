# US-007 Testing — 改善トラッキング

**対象アプリ:** DeskStretch (stretch-flow)
**レシピ:** `.claude/skills/mobileapp-builder/references/us-007-testing.md`
**TEST_SPEC:** `mobile-apps/stretch-flow/docs/TEST_SPEC.md`
**開始日:** 2026-03-05

---

## 発見した問題・改善点

### 🔴 CRITICAL（レシピ修正必須）

| # | カテゴリ | 問題 | 修正案 | ステータス |
|---|---------|------|--------|-----------|
| 1 | **xcodebuild 直接禁止** | レシピが `xcodebuild -scheme <AppName> build` を直接使用（Quality Gate, Step 2, Step 5）。プロジェクトルール: Fastlane 以外禁止 | `xcodegen generate && fastlane test` に変更。DeskStretch 用 Fastfile の作成手順を追加 | ❌ 未修正 |
| 2 | **Maestro CLI 直接禁止** | レシピ Step 5 が `maestro test flows/` を直接使用。プロジェクトルール: Maestro MCP 必須（CLI は CI/CD のみ） | `mcp__maestro__run_flow_files` に変更。エージェント作業時は MCP 経由を明記 | ❌ 未修正 |
| 3 | **Rule 21 違反** | TEST_SPEC Edge Case #7: 「Foundation Models timeout → Fall back to static routine」。Rule 21 で AI API / Foundation Models は**完全禁止** | Edge Case #7 を削除。Performance §「AI generation < 3s」も削除。静的コンテンツのみ | ❌ 未修正 |
| 4 | **依存関係チェックなし** | レシピが US-006（実装）完了を前提とするが、明示的な依存チェックがない。現状 US-006 未完了でソースコード 0 ファイル | Quality Gate 冒頭に `ls DeskStretch/App/*.swift || exit 1` 的な存在チェック追加 | ❌ 未修正 |
| 5 | **xcodegen 対応なし** | レシピが `.xcodeproj` 前提。DeskStretch は xcodegen (`project.yml`) 使用。ビルド前に `xcodegen generate` が必須 | Quality Gate に `xcodegen generate` ステップ追加 | ❌ 未修正 |

### ⚠️ HIGH（品質に影響）

| # | カテゴリ | 問題 | 修正案 | ステータス |
|---|---------|------|--------|-----------|
| 6 | **UDID ハードコード** | レシピが `$UDID` を未定義のまま使用。動的検出の手順なし | `xcrun simctl list devices available \| grep "iPhone.*Booted" \| head -1` で動的検出 | ❌ 未修正 |
| 7 | **Fastfile 未作成** | DeskStretch に Fastlane が存在するが Fastfile が空/未確認。レシピに Fastfile セットアップ手順なし | レシピに「Fastfile テンプレート」セクション追加（test/build/build_for_simulator lane） | ❌ 未修正 |
| 8 | **flows/ ディレクトリ名** | レシピ Step 4-5 が `flows/` を参照。TEST_SPEC は `maestro/` を参照。DeskStretchios 配下に `maestro/` ディレクトリあり | `flows/` → `maestro/` に統一 | ❌ 未修正 |
| 9 | **StoreKit 設定手順不足** | Step 3 が「`Products.storekit` を作成」のみで具体的な製品ID・価格定義なし | PRD.md の $3.99/mo + $29.99/yr を引用し、product_id / subscription_group_id を明記 | ❌ 未修正 |
| 10 | **テストターゲット Info.plist** | xcodegen で TestTarget を定義する際 `GENERATE_INFOPLIST_FILE: YES` が必須。レシピに言及なし | project.yml TestTarget テンプレートに `GENERATE_INFOPLIST_FILE: YES` 追加 | ❌ 未修正 |

### 📌 MEDIUM（改善推奨）

| # | カテゴリ | 問題 | 修正案 | ステータス |
|---|---------|------|--------|-----------|
| 11 | **スキル参照の整合性** | レシピが `tdd-feature`, `integration-test-scaffold`, `test-data-factory`, `maestro-e2e` の4スキルを参照するが、mobileapp-builder 用に最適化されていない | 各スキルの核心ルールをレシピ内にインライン化（外部依存減らす） | ❌ 未修正 |
| 12 | **TEST_SPEC: Fastlane パス** | TEST_SPEC §9 が `cd DeskStretchios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane test` を使用。正しいが `FASTLANE_OPT_OUT_CRASH_REPORTING=1` が欠落 | 環境変数を追加 | ❌ 未修正 |
| 13 | **TEST_SPEC: Maestro CLI** | TEST_SPEC §9 が `maestro test maestro/` CLI を直接使用。エージェント作業時は MCP 必須 | 「エージェント: MCP / CI: CLI」の使い分けを明記 | ❌ 未修正 |
| 14 | **Mock チェック範囲** | Quality Gate の `grep -r 'Mock' --include='*.swift' . \| grep -v Tests/` が `Mock` 文字列全般をキャッチ。正規表現が雑（MockURLProtocol 等の正当な利用もキャッチ） | `grep -rw 'Mock' --include='*.swift' DeskStretch/ \| grep -v 'Protocol'` に改善 | ❌ 未修正 |
| 15 | **Acceptance Criteria 不足** | レシピ AC が5項目のみ。カバレッジ80%+、Edge Case テスト、Accessibility テストの合格基準なし | TEST_SPEC の全セクションに対応する AC を追加 | ❌ 未修正 |
| 16 | **TEST_SPEC: AIStretchService テスト名** | テスト名 `testFallbackReturnsCorrectCount` — 「Fallback」は Foundation Models 前提の命名。Rule 21 適用後は通常ロジック | `testGenerateReturnsCorrectCount` に改名。全テスト名から「Fallback」を削除 | ❌ 未修正 |
| 17 | **TEST_SPEC: Performance §** | 「AI generation < 3s」— Rule 21 で AI 禁止なので無意味。「Cold start < 2s」は妥当 | 「AI generation」行を「Routine generation < 500ms」（静的フィルタリングなので高速）に変更 | ❌ 未修正 |
| 18 | **Scheme 名の明示** | レシピが `<AppName>` プレースホルダーを使用。実際のスキーム名 `DeskStretch` を明記すべき | テンプレートに `$APP_SCHEME` 変数定義を追加、またはレシピ冒頭に変数セクション | ❌ 未修正 |

### 💡 LOW（Nice-to-have → MUST として実装）

| # | カテゴリ | 問題 | 修正案 | ステータス |
|---|---------|------|--------|-----------|
| 19 | **Swift Testing 推奨** | TEST_SPEC が Swift Testing (`#expect`) を推奨するが、レシピ本文に言及なし | レシピ Step 2 に「Swift Testing framework を使用（`@Test`, `#expect`）」を追加 | ❌ 未修正 |
| 20 | **テスト実行順序** | レシピが Unit → Integration → E2E の順序を明記していない。TEST_SPEC はピラミッド図のみ | Step 2 を「Step 2a: Unit Tests」「Step 2b: Integration Tests」に分割 | ❌ 未修正 |
| 21 | **エラーハンドリングテスト** | TEST_SPEC Edge Cases は表で列挙するが、どのテストファイルでカバーするか未マッピング | Edge Case → Unit Test マッピングテーブル追加 | ❌ 未修正 |
| 22 | **TEST_SPEC: Accessibility** | Accessibility Testing が「Manual」のみ。自動化可能なテスト（Dynamic Type サイズ変更後のレイアウト等）の言及なし | Maestro の `setDeviceSettings` で一部自動化可能な旨を追記 | ❌ 未修正 |
| 23 | **Quality Gate: プロジェクト生成** | xcodegen プロジェクトの場合、テスト前に `xcodegen generate` → `.xcodeproj` 生成が必須。レシピに手順なし | Quality Gate の最初のステップに追加 | ❌ 未修正 |

---

## サマリー

| 重要度 | 件数 |
|--------|------|
| 🔴 CRITICAL | 5 |
| ⚠️ HIGH | 5 |
| 📌 MEDIUM | 8 |
| 💡 LOW (→ MUST) | 5 |
| **合計** | **23** |

---

## 参照ソース

| ソース | URL | 核心の引用 |
|--------|-----|-----------|
| Apple Testing Best Practices | https://developer.apple.com/documentation/xcode/testing-your-apps-in-xcode | "Use the test navigator to create, run, and review tests" |
| Maestro Docs | https://maestro.dev/docs | "Write YAML test scripts for mobile apps" |
| Swift Testing | https://developer.apple.com/documentation/testing | "Use @Test macro and #expect for modern testing" |
| プロジェクト CLAUDE.md | ローカル | "xcodebuild 直接実行禁止。Fastlane 以外は使うな" |
| プロジェクト tool-usage.md | ローカル | "エージェントは Maestro CLI を直接叩くな。必ず MCP を使え" |
| mobileapp-builder CLAUDE.md Rule 23 | ローカル | "AI API / 外部 API コスト禁止" |
