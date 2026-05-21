#!/bin/bash
# roundcube-webmail-skill: setup-keychain.sh
# Stores credentials in macOS Keychain instead of .env
# Run once during setup. After this, delete WEBMAIL_PASSWORD and WEBMAIL_TOTP_SECRET from .env.

set -e

echo "NAISTメール認証情報を macOS Keychain に保存します"
echo ""

read -p "ユーザーネーム (例: daisuke-na): " USERNAME
read -s -p "NAISTメールのパスワード: " PASSWORD
echo ""
read -s -p "TOTPシークレット (decode_totp_qr.py の出力値): " TOTP_SECRET
echo ""

# Save to Keychain
security add-generic-password -U -a "naist-mail" -s "WEBMAIL_USERNAME" -w "$USERNAME"
security add-generic-password -U -a "naist-mail" -s "WEBMAIL_PASSWORD" -w "$PASSWORD"
security add-generic-password -U -a "naist-mail" -s "WEBMAIL_TOTP_SECRET" -w "$TOTP_SECRET"

echo ""
echo "✅ Keychain に保存しました"
echo ""
echo "以下を .env に設定してください（機密情報は不要）:"
echo "WEBMAIL_URL=https://mailbox.naist.jp/roundcube/"
echo ""
echo "スクリプト実行時は以下のように呼び出してください:"
echo "  WEBMAIL_USERNAME=\$(security find-generic-password -a naist-mail -s WEBMAIL_USERNAME -w) \\"
echo "  WEBMAIL_PASSWORD=\$(security find-generic-password -a naist-mail -s WEBMAIL_PASSWORD -w) \\"
echo "  WEBMAIL_TOTP_SECRET=\$(security find-generic-password -a naist-mail -s WEBMAIL_TOTP_SECRET -w) \\"
echo "  node scripts/read-mail.js"
