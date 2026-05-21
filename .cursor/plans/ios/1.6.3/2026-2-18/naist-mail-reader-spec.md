# naist-mail-reader スキル仕様書

最終更新: 2026-02-21

---

## 概要

NAISTメールの受信箱を AI が自動で読み、最新10件を Slack に通知するスキル。
SAML + Google Authenticator (TOTP) の2段階認証を自動突破する。
Mac Mini (OpenClaw) で毎朝 9:00 JST に自動実行する。
v2 でメール返信機能を追加する。

---

## できること / できないこと

| 機能 | 状態 |
|------|------|
| 受信箱の最新 N 件を読む | ✅ v1 実装済み |
| 未読のみフィルタ | ✅ v1 実装済み |
| Slack に自動通知 | ✅ v1 実装済み |
| OpenClaw cron で毎朝自動実行 | ✅ v1 実装済み |
| 指定メールに返信する | 🔜 v2 |
| セッション自動削除（セキュリティ） | 🔜 v2 |
| macOS Keychain 統合 | 🔜 v2 |

---

## 技術仕様

| 項目 | 値 |
|------|-----|
| リポジトリ | https://github.com/Daisuke134/roundcube-webmail-skill |
| ランタイム | Node.js + Playwright + otplib |
| 認証方式 | SAML SSO (TOTP Step1) + Roundcube native login (Step2) |
| メール URL | https://mailbox.naist.jp/roundcube/（固定） |
| セッション保存 | `.session.json` に保存して再利用 |
| Mac Mini スキルパス | `/Users/anicca/.openclaw/skills/roundcube-webmail-skill/` |
| Slack通知チャンネル | C091G3PKHL2 (cron自動通知先) |

---

## ログイン2ステップの仕組み

```
https://mailbox.naist.jp/roundcube/
  → SAML リダイレクト
    → idp.naist.jp/pub/otplogin.cgi
      → Step1: #username_input / #password_input に TOTP コード入力
        → SAML アサーション → Roundcube に戻る
          → Step2: #rcmloginuser / #rcmloginpwd に username / password 入力
            → ログイン完了 (task=mail)
```

---

## v2: 返信機能 仕様

### 返信フロー

```
inbox から対象メール（uid）を指定
  → tr[id^="rcmrow"][data-uid="<uid>"] をクリックして開く
    → [command="reply"] をクリック
      → waitForSelector('#composebody', timeout: 15000)
        → TinyMCE が有効か確認
          → 有効: page.evaluate(() => tinymce.get('composebody').setContent(text))
          → 無効: page.fill('#composebody', text)
            → [command="send"] または .btn.btn-primary.send をクリック
              → waitForSelector('tr[id^="rcmrow"]', timeout: 15000) で送信完了を確認
```

### 返信に使うセレクタ

| UI要素 | セレクタ | 備考 |
|--------|---------|------|
| メール行 | `tr[id^="rcmrow"]` | data-uid 属性でメール特定 |
| 返信ボタン | `[command="reply"]` | elastic skin |
| 全員に返信 | `[command="reply-all"]` | |
| 本文入力欄 | `#composebody` | plain text モード |
| 本文（TinyMCE） | `tinymce.get('composebody').setContent(text)` | HTML モード時 |
| 送信ボタン | `[command="send"]` または `.btn.btn-primary.send` | |

### TinyMCE 判定ロジック

```javascript
const isTinyMCE = await page.evaluate(() => typeof tinymce !== 'undefined' && tinymce.get('composebody'));
if (isTinyMCE) {
  await page.evaluate((text) => tinymce.get('composebody').setContent(text), replyText);
} else {
  await page.fill('#composebody', replyText);
}
```

### reply-mail.js の入力インターフェース

| 環境変数 | 意味 | 例 |
|---------|------|-----|
| `WEBMAIL_REPLY_UID` | 返信対象メールのUID | `12345` |
| `WEBMAIL_REPLY_TEXT` | 返信本文 | `ご連絡ありがとうございます。` |
| `WEBMAIL_REPLY_ALL` | 全員に返信するか | `false` |

---

## v2: セキュリティ改善 仕様

### 現状のリスク（対応必須）

| 順位 | リスク | 深刻度 |
|-----|--------|--------|
| 1 | `.env` にパスワード・TOTPシークレットが平文 | CRITICAL |
| 2 | base32 TOTPシークレットが平文 = 2FA無効化と同じ | HIGH |
| 3 | `.session.json` が使用後も平文でディスクに残る | MEDIUM |
| 4 | 誤って `.env` を git にコミットするリスク | CRITICAL |

### v2 で対応する改善

| # | 改善内容 | 効果 |
|---|---------|------|
| 1 | **`.session.json` を実行後に自動削除** | セッション漏洩防止 |
| 2 | **macOS Keychain 統合**（`security` コマンド経由） | TOTPシークレット・パスワードを平文ファイルから排除 |
| 3 | **README に警告セクション追加**（`.env` を絶対 git に上げるな） | 公開スキルのユーザー保護 |

### macOS Keychain 統合方針

```bash
# 保存（セットアップ時に1回）
security add-generic-password -a "naist-mail" -s "WEBMAIL_PASSWORD" -w "パスワード"
security add-generic-password -a "naist-mail" -s "WEBMAIL_TOTP_SECRET" -w "base32シークレット"

# 取得（スクリプト実行時）
WEBMAIL_PASSWORD=$(security find-generic-password -a "naist-mail" -s "WEBMAIL_PASSWORD" -w)
WEBMAIL_TOTP_SECRET=$(security find-generic-password -a "naist-mail" -s "WEBMAIL_TOTP_SECRET" -w)
```

`.env` に残すのは `WEBMAIL_URL` と `WEBMAIL_USERNAME`（非機密）のみ。

### セッション自動削除

```javascript
// finally ブロックで必ず実行
} finally {
  await browser.close();
  if (fs.existsSync(SESSION_FILE)) fs.unlinkSync(SESSION_FILE);
}
```

---

## OpenClaw Cron 設定（Mac Mini）

| 項目 | 値 |
|------|-----|
| Cron ID | naist-mail-reader |
| schedule | `0 9 * * *`（毎朝 9:00 JST） |
| Slack 通知先 | C091G3PKHL2 |
| delivery.mode | none |

---

## 実装済みファイル（v1）

| ファイル | 役割 |
|---------|------|
| `scripts/read-mail.js` | メイン実行スクリプト（ログイン + 受信箱読み取り + Slack通知） |
| `scripts/decode_totp_qr.py` | Google Authenticator QR → TOTP Secret 抽出ツール |
| `package.json` | 依存: playwright, otplib |
| `.gitignore` | node_modules, .session.json を除外 |
| `SKILL.md` | Claude Code / OpenClaw 用スキル説明 |

## 追加予定ファイル（v2）

| ファイル | 役割 |
|---------|------|
| `scripts/reply-mail.js` | 返信スクリプト（UID + 本文を受け取って返信） |
| `scripts/setup-keychain.sh` | macOS Keychain にシークレットを登録するセットアップスクリプト |

---

## 受け入れ条件

| # | 条件 | 対象バージョン |
|---|------|--------------|
| 1 | 最新10件をSlackに通知できる | v1 ✅ |
| 2 | 未読フィルタが動作する | v1 ✅ |
| 3 | 指定UIDのメールに返信が送信できる | v2 ⚠️ 未テスト（実機未確認） |
| 4 | 返信後にSlackに「返信しました」と通知される | v2 ⚠️ 未テスト（実機未確認） |
| 5 | 実行後 `.session.json` が自動削除される | v2 |
| 6 | macOS Keychain からシークレットを取得して動作する | v2 |
| 7 | `.env` に機密情報（パスワード・TOTPシークレット）が含まれない | v2 |

---

## テストマトリックス（v2）

| # | テスト名 | カバー |
|---|---------|--------|
| 1 | `test_reply_plain_text_mode` | TinyMCE なしの返信 |
| 2 | `test_reply_tinymce_mode` | TinyMCE ありの返信 |
| 3 | `test_session_deleted_after_run` | 実行後に `.session.json` が存在しない |
| 4 | `test_keychain_secret_fetch` | Keychain からシークレット取得 |
| 5 | `test_reply_confirmation_slack` | 返信後に Slack 通知が届く |

---

## 完了チェックリスト

| # | タスク | 状態 |
|---|--------|------|
| 1 | スクリプト動作確認（最新10件取得） | ✅ 完了 |
| 2 | GitHub push | ✅ 完了 |
| 3 | README 更新 | ✅ 完了 |
| 4 | 仕様書作成（このファイル） | ✅ 完了 |
| 5 | Slack 投稿（C08RZ98SBUL） | ✅ 完了 |
| 6 | Mac Mini cron 設定 | ✅ 完了 |
| 7 | v2: reply-mail.js 実装 | ⚠️ コード実装済み・実機未テスト |
| 8 | v2: setup-keychain.sh 実装 | ✅ 完了 |
| 9 | v2: セッション自動削除 | ✅ 完了 |
| 10 | v2: Keychain必須化・DEBUGガード | ✅ 完了 |
| 11 | v2: .env.example 作成 | ✅ 完了 |
| 12 | v2: README macOS専用明記 | ✅ 完了 |
| 13 | npx skills add でローカルインストール | ✅ 完了 |
