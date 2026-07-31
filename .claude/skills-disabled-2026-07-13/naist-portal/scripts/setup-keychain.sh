#!/bin/bash
# naist-portal-skill: setup-keychain.sh
# Stores credentials in macOS Keychain instead of .env
# Run once during setup. After this, delete PORTAL_PASSWORD and PORTAL_TOTP_SECRET from .env.

set -e

echo "NAISTポータル認証情報を macOS Keychain に保存します"
echo ""

read -p "NAISTユーザーネーム (例: t12345dz): " USERNAME
read -s -p "NAISTポータルのパスワード: " PASSWORD
echo ""
read -s -p "TOTPシークレット (zbarimg の出力値から secret= 以降): " TOTP_SECRET
echo ""

# Save to Keychain
security add-generic-password -U -a "naist-portal" -s "PORTAL_USERNAME" -w "$USERNAME"
security add-generic-password -U -a "naist-portal" -s "PORTAL_PASSWORD" -w "$PASSWORD"
security add-generic-password -U -a "naist-portal" -s "PORTAL_TOTP_SECRET" -w "$TOTP_SECRET"

echo ""
echo "Keychain に保存しました"
echo ""
echo "以下を /Users/anicca/.openclaw/.env に追加してください:"
echo "PORTAL_USERNAME=$USERNAME"
