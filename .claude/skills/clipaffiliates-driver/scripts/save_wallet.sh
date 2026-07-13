#!/usr/bin/env bash
# Swap ClipAffiliates payout wallet via the discovered API endpoint.
# Drives the CloakBrowser daily-driver tab so the cookie + CSRF are in-session.
# Usage: save_wallet.sh <TAB_ID> <NEW_PUBKEY> [currency=usdcsol]
set -euo pipefail
TID="${1:?tab-id required (CDP target id of an authed ClipAffiliates tab)}"
PUBKEY="${2:?new wallet pubkey (Base58 Solana address)}"
CURRENCY="${3:-usdcsol}"

CDP=/Users/anicca/.claude/skills/ig-account-create/scripts/cdp.py
/opt/homebrew/bin/python3 "$CDP" eval "$TID" - <<JS
(() => {
  const PK = "$PUBKEY";
  const CUR = "$CURRENCY";
  return new Promise(async (resolve) => {
    const csrf = document.cookie.split(';').map(s=>s.trim()).find(s=>s.startsWith('csrftoken='))?.split('=')[1];
    const headers = {'Content-Type':'application/json','X-CSRFToken':csrf,'Accept':'application/json'};
    const body = JSON.stringify({wallet_address: PK, wallet_currency: CUR});
    const save = await fetch('https://api.clipaffiliates.com/api/payments/crypto/save_wallet/', {
      method:'POST', credentials:'include', headers, body
    });
    const save_body = await save.text();
    const verify = await fetch('https://api.clipaffiliates.com/api/payments/crypto/account_status/', {credentials:'include'});
    const verify_body = await verify.text();
    resolve({save_status: save.status, save_body, verify_status: verify.status, verify_body});
  });
})()
JS
