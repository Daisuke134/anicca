# roundcube-webmail-skill

> **macOS 専用**

NAISTメールを AI エージェントから自動で読むスキル。
SAML + Google Authenticator 認証を自動突破して、受信箱の最新件数を Slack に通知します。

## できること

| 機能 | スクリプト |
|------|-----------|
| 受信箱の最新 N 件を読む | `read-mail.js` |
| 未読のみフィルタ | `read-mail.js` |
| Slack に自動通知 | `read-mail.js` |
| OpenClaw cron で毎朝自動実行 | cron 設定参照 |

---

## セットアップ

### Step 1: 手元で用意する（あなたがやること）

**① 認証コードのスクリーンショット**

1. iPhone で Google Authenticator を開く
2. 左上の ☰ をタップ →「アカウントのエクスポート」をタップ
3. NAISTメールのアカウントにチェック →「次へ」をタップ
4. QRコードが表示されたらスクリーンショットを撮る（電源 + 音量↑ 同時押し）
5. 写真アプリでスクリーンショットを長押し → 共有 → AirDrop → このMac
6. `~/Downloads/` に PNG が届いたことを確認してファイル名を控える

**② NAISTメールに入る際のユーザーネームとパスワード**

---

### Step 2: 以下を Claude Code または Cursor に貼り付ける

`[ ]` の中を自分の情報に書き換えてからペーストしてください。

```
roundcube-webmail-skill をセットアップしてください。

以下を用意しました:
- QRコードのPNG: ~/Downloads/[ファイル名].PNG
- ユーザーネーム: [例: daisuke-na]
- パスワード: [NAISTメールのパスワード]

以下を順番に実行してください:
1. npx skills add Daisuke134/roundcube-webmail-skill
2. brew install zbar（未インストールの場合）
3. zbarimg --raw ~/Downloads/[ファイル名].PNG でQRを読み取る
4. python3 scripts/decode_totp_qr.py で認証シークレットを抽出する
5. bash scripts/setup-keychain.sh を実行してパスワードと認証シークレットを Keychain に保存する
6. .env に WEBMAIL_USERNAME と WEBMAIL_URL のみ設定する
7. node scripts/read-mail.js を実行して最新5件をこのチャットに表示する

最後に最新5件が表示されれば完了です。
```

---

## セキュリティ

パスワードと認証シークレットは macOS Keychain に保存されます。テキストファイルには一切残りません。

ログイン後のセッション情報は毎回の実行後に自動で削除されます。

`DEBUG=pw:*` が設定されている場合は認証情報が出力されるため、スクリプトが起動を拒否します。

---

## 環境変数一覧

| 変数名 | 保存場所 | 説明 |
|--------|---------|------|
| `WEBMAIL_USERNAME` | `.env` | NAISTユーザーネーム |
| `WEBMAIL_PASSWORD` | Keychain | NAISTメールのパスワード |
| `WEBMAIL_TOTP_SECRET` | Keychain | Google Authenticator の TOTP シークレット |
| `WEBMAIL_URL` | `.env` | デフォルト: `https://mailbox.naist.jp/roundcube/` |
| `WEBMAIL_MAX_EMAILS` | `.env` | 取得件数（デフォルト: 10） |
| `WEBMAIL_UNREAD_ONLY` | `.env` | `true` で未読のみ取得 |
| `SLACK_WEBHOOK_URL` | `.env` | Slack 通知先 Webhook URL |

---

## OpenClaw cron（毎朝自動実行）

```json
{
  "id": "naist-mail-reader",
  "schedule": "0 9 * * *",
  "kind": "agentTurn",
  "message": "exec コマンドで node scripts/read-mail.js を実行して、最新10件のメールを Slack C091G3PKHL2 に投稿してください。",
  "delivery": { "mode": "none" }
}
```
