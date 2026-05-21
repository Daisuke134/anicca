# Mac Mini セットアップ完了スペック
日付: 2026-02-28
ステータス: 進行中

## 背景
Mac MiniにOpenClaw Gatewayを移行済み。初期セットアップの残タスクを整理・実行する。

## 完了済み ✅

### 1. WiFi + Tailscale 自動化
- `/Users/anicca/scripts/auto-connect.sh` 作成
- LaunchDaemon `com.anicca.autoconnect` 登録
- 再起動時に WiFi(`xg100n-16fdcd-3`) + `tailscale up` 自動実行

### 2. Xcode確認
- Xcode 26.2 インストール済み

### 3. フォルダ整理
- 全サブアプリを `daily-apps/` に集約
  - breatheai, calmcortisol, daily-dhamma-app, dailydhamma, rork-thankful-gratitude-app
- GitHubプッシュ済み

### 4. mobileapp-builder SKILL.md 復元
- 793行のオリジナルをgit historyから復元
- references (iap-bible.md, spec-template.md) も復元
- GitHubプッシュ済み

### 5. Full Keyboard Access 有効化
- `defaults write NSGlobalDomain AppleKeyboardUIMode -int 3`

### 6. パスワード修正
- Apple ID: `Chatgpt12345`（!なし）
- TOOLS.md + .env 修正済み

### 7. スキル健全性チェック
- .cursor/skills/ 96個中、SKILL.mdなし: 2個（skills/, x-research/） → 元々ない
- .openclaw/skills/ 88個中、SKILL.mdなし: 1個（usdc-testnet-tx-checker/） → 元々ない
- 壊れたスキル: なし

### 8. メモリ更新
- MEMORY.mdに正確なパス情報追加
- Mac Miniセットアップ残タスク追加

## 今すぐやるTODO（マウス不要）

### 9. 自動sync設置
ベストプラクティス: cron + git pull
ソース: https://portent.com/blog/design-dev/github-auto-deploy-setup-guide.htm
引用: 「Using cron as our auto-deployment method... run the git fetch and git checkout commands」

実装:
```bash
# Mac Mini側: 5分毎にgit pull
*/5 * * * * cd /Users/anicca/anicca-project && git fetch --all && git checkout --force "origin/dev" 2>&1 >> /Users/anicca/scripts/git-sync.log
```

### 10. シンボリックリンク修正
現状: `.claude/skills/` → `.cursor/skills/`（実体）
修正: `.claude/skills/` を実体に、`.cursor/skills/` をシンボリックリンクに
理由: Claude Codeは `.claude/skills/` を読む。OSSでの公開時にも混乱しない。

### 11. mobileapp-builder独立リポ同期
現状: `Daisuke134/mobileapp-builder`（最新、RULE 38）と `anicca-products/.cursor/skills/mobileapp-builder/`（古い、v3）が乖離
修正: 独立リポの最新版をanicca-projectに同期

### 12. mobileapp-factoryスキルに定期報告追加
現状: 起動報告と完了報告のみ
修正: 各フェーズ完了ごとにSlack #metrics報告を追加

### 13. Netlify CLI設定
- `npm install -g netlify-cli`
- トークン取得
- NETLIFY_AUTH_TOKEN と NETLIFY_SITE_ID を .env に追加

## 10pm以降TODO（マウス必要）

### 14. USB-A to C変換器でマウス接続
購入場所: ダイソー京王モールアネックス店（110円、土日祝10:00-21:00）

### 15. Allowボタンクリック（Bluetooth許可）

### 16. System Settings > Privacy & Security > Accessibility > Terminal ON

### 17. System Settings > General > Sharing > Screen Sharing ON

### 18. Xcode > Settings > Accounts > Apple ID追加
- keiodaisuke@gmail.com / Chatgpt12345

### 19. macos-desktop-controlスキルインストール
- `clawhub install macos-desktop-control --dir ~/.openclaw/skills`

### 20. CalmCortisol PHASE 3.5 + 4 再開

## 継続タスク

### 21. 全daily-appsにscreenshot-ab実験設定
### 22. 全daily-appsにpaywall-ab実験設定
### 23. 新規アプリは日付コードネーム方式（例: 2026-03-01-app/）

## ソース
- Portent (2024): https://portent.com/blog/design-dev/github-auto-deploy-setup-guide.htm
- Stack Overflow: https://stackoverflow.com/questions/4414140/git-auto-pull-using-cronjob
- Jake McCrary: https://jakemccrary.com/blog/2020/02/25/auto-syncing-a-git-repository/
- Apple Support: https://support.apple.com/guide/mac-help/allow-accessibility-apps-to-access-your-mac-mh43185/mac
- ClawHub macos-desktop-control: https://clawhub.com/skills/macos-desktop-control
