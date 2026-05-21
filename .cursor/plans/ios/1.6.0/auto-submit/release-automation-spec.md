# リリース自動化 Spec（v2 - レビュー反映済み）

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-auto-release` |
| **ブランチ** | `feature/auto-release` |
| **ベースブランチ** | `dev` |
| **作業状態** | 実装中 |

## 概要（What & Why）

### What
リリースプロセスを完全自動化する。現状はバージョン更新が手動（12箇所のpbxproj編集）で、App Store提出もXcode GUIでのArchive→Distribute操作が必要。

### Why
- **毎回バージョン更新を忘れる** → Apple Validation エラーで時間を浪費
- **Xcode GUI操作が必要** → エージェントが自律的にリリースできない
- **エラーがGUIにしか出ない** → エージェントがエラーを読んで修正できない

### ゴール
ユーザーが「1.6.0をリリースして」と言ったら、エージェントが以下を全自動で実行:
```
release/1.6.0 ブランチ作成
    ↓
fastlane set_version version:1.6.0（明示的にバージョン更新）
    ↓
fastlane full_release
    ↓ Archive → Upload → 処理待ち → 審査提出
「Waiting for Review になりました」と報告
```

## 設計判断（レビューで確定）

### Git Hook を採用しない理由

| 問題 | 詳細 |
|------|------|
| Worktreeで壊れる | `post-checkout` は新Worktreeのコンテキストで正しく動かない |
| バージョン管理されない | `.git/hooks/` はローカルのみ。クローンで消える |
| dirty working tree | 未コミット変更があるとauto-commitが事故る |
| サイレント失敗 | エラーが見えない |

### 採用: 明示的 `fastlane set_version` 呼び出し

| 比較 | Git Hook | `fastlane set_version` |
|------|----------|----------------------|
| Worktree | ❌ | ✅ |
| バージョン管理 | ❌ | ✅ Fastfileに入る |
| デバッグ | ❌ サイレント | ✅ CLI出力 |
| クローン後 | ❌ 手動セットアップ | ✅ ゼロ |

### `increment_version_number` を使わない理由

`increment_version_number` は内部で `agvtool` を使うが、Xcode 11+ の `MARKETING_VERSION` ビルド設定と互換性の問題がある。`sed` で直接 `project.pbxproj` を書き換える方が確実。

## 受け入れ条件

| # | 条件 | テスト可能な形式 |
|---|------|-----------------|
| 1 | `fastlane set_version version:X.Y.Z` で全ターゲットの MARKETING_VERSION が更新される | 実行後 `grep` で12箇所全て確認 |
| 2 | 不正なバージョン形式を拒否する | `fastlane set_version version:abc` → エラー |
| 3 | `fastlane full_release` でArchive→Upload→審査提出まで完了する | 既存レーン（動作確認済み） |
| 4 | CLAUDE.md のリリースフローが自動化手順に書き換えられている | コマンドがコピペ実行可能 |

## As-Is / To-Be

### As-Is（現状）

| 項目 | 現状 |
|------|------|
| バージョン更新 | 手動で `project.pbxproj` の12箇所を sed で書き換え |
| Archive | Xcode GUI で Product → Archive |
| Upload | Xcode GUI で Distribute App |
| 審査提出 | App Store Connect GUI で Submit for Review |
| エラー確認 | Xcode Organizer のダイアログ → ユーザーがスクショしてコピペ |

### To-Be（実装後）

| 項目 | 実装後 |
|------|--------|
| バージョン更新 | `fastlane set_version version:X.Y.Z`（エージェントがブランチ名から抽出して実行） |
| Archive → 審査提出 | `fastlane full_release`（1コマンド） |
| エラー確認 | Fastlane CLI 出力 → エージェントが読んで修正 |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `aniccaios/fastlane/Fastfile` | `set_version` レーン追加 |
| `CLAUDE.md` | リリースフローセクションを自動化手順に書き換え |

## テストマトリックス

| # | To-Be | テスト方法 | カバー |
|---|-------|-----------|--------|
| 1 | `set_version` が全12箇所更新 | `fastlane set_version version:9.9.9` → `grep -c "9.9.9"` = 12 | ✅ |
| 2 | 不正形式を拒否 | `fastlane set_version version:abc` → エラー終了 | ✅ |
| 3 | バージョン未指定を拒否 | `fastlane set_version` → エラー終了 | ✅ |
| 4 | CLAUDE.md のコマンドが実行可能 | 記載コマンドをそのまま実行して動作する | ✅ |

## 境界

### やること
- Fastlane `set_version` レーン追加（sed方式）
- CLAUDE.md リリースフロー書き換え（エージェント向け完全手順）

### やらないこと
- Git hook 作成（レビューで却下）
- `full_release` レーンの改修（既に動作する）
- ビルド番号自動インクリメント（既存フローで対応済み）
- リリースノート自動化（別タスク）
- metadata/ ディレクトリ整備（別タスク）

### 触らないファイル
- `submit_review` / `full_release` レーン（既存のまま）
- iOS Swift コード

## 実装手順

### 1. Fastlane `set_version` レーン追加

```ruby
desc "Set MARKETING_VERSION across all targets"
lane :set_version do |options|
  version = options[:version]
  UI.user_error!("Usage: fastlane set_version version:X.Y.Z") unless version
  UI.user_error!("Invalid format. Expected X.Y.Z, got: #{version}") unless version.match?(/^\d+\.\d+\.\d+$/)

  pbxproj = "aniccaios.xcodeproj/project.pbxproj"
  UI.user_error!("#{pbxproj} not found") unless File.exist?(pbxproj)

  content = File.read(pbxproj)
  count = content.scan(/MARKETING_VERSION = [0-9]+\.[0-9]+\.[0-9]+;/).length
  updated = content.gsub(/MARKETING_VERSION = [0-9]+\.[0-9]+\.[0-9]+;/, "MARKETING_VERSION = #{version};")
  File.write(pbxproj, updated)

  UI.success("✅ MARKETING_VERSION updated to #{version} (#{count} occurrences)")
end
```

**なぜ sed/gsub 方式か:**
- `increment_version_number` は `agvtool` 依存で `MARKETING_VERSION` ビルド設定と相性が悪い
- 正規表現で全バージョン文字列を一括置換（部分更新の事故を防ぐ）
- 12箇所全て確実に更新

### 2. CLAUDE.md 書き換え

リリース関連セクションを以下に更新:

```markdown
### リリース手順（完全自動化）

ユーザーが「X.Y.Z をリリースして」と言ったら、エージェントが以下を実行:

1. main を最新にして release ブランチ作成
   git checkout main && git pull origin main
   git checkout -b release/X.Y.Z

2. バージョン更新（必須: 忘れると Apple Validation エラー）
   cd aniccaios && fastlane set_version version:X.Y.Z

3. コミット & プッシュ
   git add -A && git commit -m "chore: bump version to X.Y.Z"
   git push -u origin release/X.Y.Z

4. 全自動リリース（Archive → Upload → 処理待ち → 審査提出）
   cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane full_release

5. 結果報告
   「Build #XX (vX.Y.Z) が審査に提出されました。Waiting for Review です。」

6. release → dev にマージ（バージョン更新を同期）
   git checkout dev && git merge release/X.Y.Z && git push origin dev
```

### エラー時のリカバリ手順

| エラー | 原因 | 対処 |
|--------|------|------|
| `Invalid Pre-Release Train` | バージョンが古い | `fastlane set_version version:正しいバージョン` |
| `CFBundleShortVersionString must be higher` | バージョンが前回以下 | バージョン番号を上げる |
| build 失敗 | コンパイルエラー | Fastlane CLI 出力を読んで修正 → `fastlane full_release` 再実行 |
| upload 失敗 | ネットワーク/認証 | `fastlane upload` を再実行 |
| processing タイムアウト | Apple 側の遅延 | ASC で確認 → `fastlane submit_review` を個別実行 |
| submit 失敗 | コンプライアンス問題 | ASC で確認 → `submission_information` 修正 |

### ロールバック手順

リリースブランチを取り消す場合:
```bash
git checkout dev
git branch -D release/X.Y.Z
git push origin --delete release/X.Y.Z
```
