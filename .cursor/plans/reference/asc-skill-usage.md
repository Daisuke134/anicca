# App Store Connect は asc スキル＋asc CLI で行う

MCP の App Store Connect ツールではなく、**app-store-connect-cli-skills** と **asc** コマンドを使う。

## 前提

- スキル: `npx skills add rudrankriyam/app-store-connect-cli-skills` で導入済み（[GitHub](https://github.com/rudrankriyam/app-store-connect-cli-skills)）
- CLI: `asc` は [rudrankriyam/App-Store-Connect-CLI](https://github.com/rudrankriyam/App-Store-Connect-CLI) のものを使う
  - 導入: `brew tap rudrankriyam/tap && brew install rudrankriyam/tap/asc`
- **スクリプト**: keychain 未設定時は `./scripts/asc.sh` で .env を自動読込して asc を実行

## 認証（初回のみ）

**asc-cli-usage** に従う。

| 方法 | コマンド・設定 |
|------|----------------|
| **keychain 永続化（推奨）** | `./scripts/asc-auth-login.sh`（.env の ASC_* を使って keychain に登録。一度実行すれば以降は asc を直接叩ける） |
| **.env のみ** | `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_PRIVATE_KEY_PATH` または `ASC_PRIVATE_KEY` を .env に設定し、`./scripts/asc.sh` で asc を実行 |
| **手動 login** | `asc auth login --name "Anicca" --key-id "XXX" --issuer-id "YYY" --private-key /path/to/AuthKey.p8`（非対話。全フラグ必須） |
| **確認** | `asc auth doctor` |

## 審査状況の確認（asc-submission-health Monitor）

**asc-id-resolver** で ID を解決してから **asc-submission-health** の Monitor を実行する。

```bash
# App ID（bundle ID で解決）
asc apps list --bundle-id "ai.anicca.app.ios"

# 1.6.3 の提出状況（Version ID は versions list で取得済みならそれを使う）
asc submit status --version-id "f114930c-bab6-4a60-9181-b2d7361cde77" --output table

# 提出一覧
asc review submissions-list --app "6755129214" --output table
```

## 参照するスキル

| やりたいこと | スキル |
|-------------|--------|
| コマンド・フラグ・認証 | asc-cli-usage |
| App / Build / Version ID 解決 | asc-id-resolver |
| 提出前チェック・提出・審査モニター | asc-submission-health |
| アップロード〜提出フロー | asc-release-flow |
| ビルド・アーカイブ・アップロード | asc-xcode-build |

## Anicca の ID（asc-id-resolver 用）

| 種類 | 値 |
|------|-----|
| App ID | 6755129214 |
| Bundle ID | ai.anicca.app.ios |
| 1.6.3 Version ID | f114930c-bab6-4a60-9181-b2d7361cde77 |
