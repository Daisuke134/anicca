---
description: Automates browser interactions for web testing, form filling, screenshots, and data extraction
allowed-tools: Bash
---

# playwright-cli

Browser automation CLI tool. This project has it at repo root: run with `npx playwright-cli` from project root.

## Quick Start

```bash
npx playwright-cli open https://example.com/
npx playwright-cli snapshot
npx playwright-cli click e3
```

## Core Workflow

1. `open` to navigate to a page
2. `snapshot` to get element refs
3. `click`, `fill`, `type` to interact

## Commands

### Core
```bash
npx playwright-cli open <url>              # open url
npx playwright-cli close                   # close the page
npx playwright-cli click <ref>            # perform click
npx playwright-cli fill <ref> <text>      # fill text
npx playwright-cli type <text>             # type text
npx playwright-cli snapshot                # capture page snapshot
npx playwright-cli screenshot [ref]        # take screenshot
```

### Sessions
```bash
npx playwright-cli -s=<name> open <url>   # open with named session (e.g. -s=test)
npx playwright-cli close-all              # stop all sessions (or kill-all)
```

### DevTools
```bash
npx playwright-cli tracing-start          # start trace recording
npx playwright-cli tracing-stop           # stop trace recording
npx playwright-cli console [min-level]     # list console messages
```

## 実際のワークフロー

### Step 1: Skillsでフローを確認する

例: 「カテゴリ選択 → サブカテゴリへの遷移」を確認する場合。

1. セッション付きでブラウザを開く: `npx playwright-cli -s=test --headed open http://localhost:3000`
2. `npx playwright-cli -s=test snapshot` で要素の ref を取得（YAML でボタン・リンクの ref が得られる）
3. モーダルを閉じる・ボタンクリック・リンククリックなどを `click <ref>` で実行
4. 必要に応じて `snapshot` で状態を確認し、`screenshot` で結果を保存

### Step 2: テストコードを実装する

Step 1 で確認したフローを元に `@playwright/test` でテストを実装。`playwright.config.ts` の baseURL は `http://localhost:3000`（または Tailscale URL）に合わせる。

### Step 3: テスト実行

```bash
npx playwright test --headed
```

動画は `test-results/` に出力（config で `video: "on"` の場合）。

## playwright-cli の作業ファイル

- `.playwright-cli/*.yml` — snapshot の結果（アクセシビリティツリー）。ref 確認用。
- `.playwright-cli/*.png` — screenshot の結果。

テスト完了後に削除してよい: `rm -rf .playwright-cli/`。セッションを止める: `npx playwright-cli close-all`。

## まとめ

| ツール | 役割 | タイミング |
|--------|------|------------|
| Playwright CLI + Skills | ブラウザとの対話的なフロー確認 | テスト設計時 |
| @playwright/test | テストコードの実装・実行 | テスト実装・CI |
| Playwright MCP | 複雑なインタラクティブデバッグ | 必要に応じて |
