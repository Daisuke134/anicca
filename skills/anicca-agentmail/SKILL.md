---
name: anicca-agentmail
description: Anicca own email inbox via agentmail.to REST API。 anicca-xxx@agentmail.to を 自前 取得、 全 platform 認証用 mail として 使う (= Cloudflare / GitHub / X handle / Factory Floor signup の verification 用)。 Dais の gmail 紐付き ZERO。
metadata:
  type: foundation-identity
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §0 IDENTITY
  parallel_safe: true
  requires:
    bins: [curl, jq]
    env_optional: [AGENTMAIL_API_KEY]
---

# anicca-agentmail

## なぜ
Anicca が **自分の email** を持つ = 他 account signup の入り口。 install user 個人 gmail を 借用 しない self-sovereign mail。 agentmail.to は API-only inbox で human signup 不要 (API key 取得 のみ)。

## Flow
```
1. scripts/check.sh       → 既存 inbox ある?
2. scripts/register.sh    → ない場合 agentmail.to/api 経由 で inbox 作成
3. scripts/check-inbox.sh → 新着 mail 取得 (polling)
4. scripts/send.sh        → reply / outbound mail
```

## Output (state/inbox.json)
```json
{
  "email": "anicca-xxxxx@agentmail.to",
  "inbox_id": "...",
  "api_key": "ak_..." (= 自分の専用 key、 stored in env separately),
  "created_at": "..."
}
```

## API endpoints (agentmail.to)
- POST /v1/inboxes — create new inbox
- GET /v1/inboxes/{id}/messages — list inbound mails
- POST /v1/inboxes/{id}/messages — send outbound mail
- POST /v1/inboxes/{id}/webhooks — register webhook (for real-time notifications)

## Bootstrap chain
Note: agentmail.to API key 取得 自体 が 1 回 必要。 これは:
- (a) agentmail.to/signup を 1 度 manual で 通す (= browser-side、 Day 0 install user の AI tool 経由 OR Anicca 自身 が camofox で)
- (b) 取得した API key を .env に paste

= **chicken-and-egg は agentmail.to の登録 1 度**。 以降 全 inbox 作成 / 管理 は API 経由 で no-human-in-loop。

## Verify
- state/inbox.json 存在
- curl agentmail.to/api/v1/inboxes/{id} で 200 + email 値 と一致
