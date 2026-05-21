# Daily Dharma - 別エージェント向け指示書

## 概要
Daily DharmaのApp Store提出を完了させるための指示書。

---

## 1. App Store Connect MCP セットアップ

### MCP設定（claude_desktop_config.jsonに追加）
```json
{
  "mcpServers": {
    "app-store-connect": {
      "command": "npx",
      "args": ["-y", "appstore-connect-mcp-server"],
      "env": {
        "APP_STORE_CONNECT_KEY_ID": "D637C7RGFN",
        "APP_STORE_CONNECT_ISSUER_ID": "f53272d9-c12d-4d9d-811c-4eb658284e74",
        "APP_STORE_CONNECT_P8_PATH": "/Users/cbns03/Downloads/AuthKey_D637C7RGFN.p8"
      }
    }
  }
}
```

### MCPで実行するタスク
1. App Store Connectにアクセス
2. Daily Dharma (Apple ID: 6757726663) を選択
3. 以下のメタデータを更新:
   - Promotional Text
   - Description
   - Keywords
   - What's New
   - Privacy Policy URL: `https://aniccaai.com/dailydharma/privacy`
   - Support URL: `https://aniccaai.com/support`

### メタデータ内容
`/Users/cbns03/Downloads/daily-dhamma-app/app-store-metadata.md` を参照

---

## 2. Sleekスクショプロンプト

### 基本設定
- **アプリ名**: Daily Dharma
- **サイズ**: 6.7インチ (1290x2796), 6.5インチ (1242x2688), 5.5インチ (1242x2208)
- **スタイル**: Minimal, zen-inspired, warm earth tones
- **背景色**: Soft beige/cream (#F5F0E8) or dark mode (#1A1A1A)

### スクショ1: メイン画面
```
Create an App Store screenshot for "Daily Dharma" meditation app.

Device: iPhone 15 Pro Max (6.7 inch)
Background: Soft beige gradient (#F5F0E8 to #EDE5D8)

Content:
- App screenshot showing a verse: "Hatreds never cease through hatred in this world; through love alone they cease."
- Source citation: "Dhammapada, Chapter 1, Verse 5"
- Minimal UI with bookmark icon

Text overlay:
- Headline: "Ancient wisdom, every day"
- Subheadline: "Authentic Dhammapada verses"

Style: Clean, minimal, zen-inspired. No cluttered elements.
```

### スクショ2: スワイプ機能
```
Create an App Store screenshot showing the swipe feature.

Device: iPhone 15 Pro Max (6.7 inch)
Background: Soft beige gradient

Content:
- Multiple verse cards stacked, showing swipe animation
- Visual indication of swiping up

Text overlay:
- Headline: "Swipe through 400+ verses"
- Subheadline: "Discover timeless Buddhist teachings"

Style: Dynamic but minimal
```

### スクショ3: 通知機能
```
Create an App Store screenshot showing Stay Present notifications.

Device: iPhone 15 Pro Max (6.7 inch)
Background: Soft beige or show iPhone lock screen

Content:
- Notification banner: "Daily Dharma: Are you present right now?"
- Or: Settings screen showing notification frequency options (5x, 7x, 10x)

Text overlay:
- Headline: "Stay present throughout your day"
- Subheadline: "Gentle mindfulness reminders"

Style: Peaceful, calming
```

### スクショ4: ダークモード
```
Create an App Store screenshot showing dark mode.

Device: iPhone 15 Pro Max (6.7 inch)
Background: Dark gradient (#1A1A1A to #2D2D2D)

Content:
- Same verse display but in dark mode
- Gold accent colors for decorative elements

Text overlay:
- Headline: "Beautiful in any light"
- Subheadline: "Easy on the eyes, day or night"

Style: Elegant dark theme
```

### スクショ5: 設定画面
```
Create an App Store screenshot showing settings.

Device: iPhone 15 Pro Max (6.7 inch)
Background: Soft beige gradient

Content:
- Settings screen with:
  - Dark Mode toggle
  - Stay Present Reminders (5x, 7x, 10x)
  - Morning Verse notification time
  - Premium banner

Text overlay:
- Headline: "Customize your practice"
- Subheadline: "Set your reminder frequency"

Style: Clean settings UI
```

---

## 3. 君がやる作業チェックリスト

### スクショ作成（Sleek）
- [ ] スクショ1: メイン画面 (6.7/6.5/5.5インチ)
- [ ] スクショ2: スワイプ機能 (6.7/6.5/5.5インチ)
- [ ] スクショ3: 通知機能 (6.7/6.5/5.5インチ)
- [ ] スクショ4: ダークモード (6.7/6.5/5.5インチ)
- [ ] スクショ5: 設定画面 (6.7/6.5/5.5インチ)

### App Store Connectアップロード
- [ ] スクショ15枚アップロード（5画面 × 3サイズ）
- [ ] Promotional Text入力
- [ ] Description入力
- [ ] Keywords入力
- [ ] What's New入力
- [ ] Privacy Policy URL入力
- [ ] Support URL入力

### Landingページデプロイ
- [ ] `cd /Users/cbns03/Downloads/anicca-project/apps/landing`
- [ ] `npm run build`
- [ ] Netlifyにデプロイ（または git push してCI/CDでデプロイ）

### 最終確認
- [ ] ビルド完了確認
- [ ] App Store Connectで審査提出ボタン押す

---

## 4. 重要な情報まとめ

### アプリ情報
| 項目 | 値 |
|------|-----|
| App Name | Daily Dharma |
| Bundle ID | com.dailydhamma.app |
| Apple ID | 6757726663 |
| SKU | dailydhamma |
| Team ID | S5U8UH3JLJ |

### API Keys
| サービス | Key |
|---------|-----|
| RevenueCat iOS | appl_fHvAqxkeyCBSFIslMvNRuCDjndy |
| RevenueCat Test | test_xsrRSGvJpoCewrQyLxZUAOFpXXi |

### URLs
| 用途 | URL |
|------|-----|
| Privacy Policy | https://aniccaai.com/dailydharma/privacy |
| Support | https://aniccaai.com/support |
| Terms | https://www.apple.com/legal/internet-services/itunes/dev/stdeula/ |

---

## 5. EAS Build コマンド（参考）

```bash
# プロジェクトディレクトリに移動
cd /Users/cbns03/Downloads/daily-dhamma-app

# 依存関係インストール
npm install

# EAS CLIインストール（グローバル）
npm install -g eas-cli

# Expoにログイン
eas login

# ビルド設定
eas build:configure

# iOSビルド実行
eas build --platform ios

# App Storeに提出
eas submit --platform ios
```

---

以上。
