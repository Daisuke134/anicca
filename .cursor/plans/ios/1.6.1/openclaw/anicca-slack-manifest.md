# Anicca Slack App Manifest (OpenClaw用)

## 問題点

現在の manifest に **Event Subscriptions がない** → Bot がメッセージを受信できない

## 修正済み Manifest

以下を https://api.slack.com/apps → Anicca → App Manifest にコピペ:

```json
{
  "display_information": {
    "name": "Anicca",
    "description": "Proactive Agent For Your Self Care",
    "background_color": "#000003"
  },
  "features": {
    "bot_user": {
      "display_name": "Anicca",
      "always_online": true
    },
    "app_home": {
      "messages_tab_enabled": true,
      "messages_tab_read_only_enabled": false
    }
  },
  "oauth_config": {
    "redirect_urls": [
      "https://localhost:3000/callback",
      "https://anicca-proxy-ten.vercel.app/api/slack-oauth/callback",
      "https://anicca-proxy-staging.up.railway.app/api/slack/oauth-callback",
      "https://anicca-proxy-production.up.railway.app/api/slack/oauth-callback"
    ],
    "scopes": {
      "user": [
        "channels:history",
        "channels:read",
        "chat:write",
        "im:history",
        "mpim:history",
        "reactions:read",
        "reactions:write",
        "users:read",
        "users:read.email",
        "search:read"
      ],
      "bot": [
        "app_mentions:read",
        "assistant:write",
        "channels:history",
        "channels:read",
        "chat:write",
        "groups:history",
        "groups:read",
        "im:history",
        "im:read",
        "im:write",
        "incoming-webhook",
        "mpim:history",
        "mpim:read",
        "mpim:write",
        "reactions:read",
        "reactions:write",
        "users:read",
        "users:read.email",
        "pins:read",
        "pins:write",
        "files:read",
        "files:write",
        "emoji:read"
      ]
    }
  },
  "settings": {
    "event_subscriptions": {
      "bot_events": [
        "app_mention",
        "message.channels",
        "message.groups",
        "message.im",
        "message.mpim",
        "reaction_added",
        "reaction_removed",
        "member_joined_channel",
        "member_left_channel",
        "channel_rename",
        "pin_added",
        "pin_removed"
      ]
    },
    "interactivity": {
      "is_enabled": true
    },
    "org_deploy_enabled": false,
    "socket_mode_enabled": true,
    "token_rotation_enabled": false
  }
}
```

## 変更点

| 項目 | 旧 | 新 |
|------|-----|-----|
| `event_subscriptions` | なし | 12イベント追加 |
| `app_mentions:read` | なし | 追加 |
| `groups:*` スコープ | なし | 追加 |
| `im:read/write` | なし | 追加 |
| `mpim:read/write` | なし | 追加 |
| `reactions:read` | なし | 追加 |
| `pins:*` | なし | 追加 |
| `files:*` | なし | 追加 |
| `app_home` | なし | 追加 |

## 適用手順

1. https://api.slack.com/apps → Anicca 選択
2. **App Manifest** タブをクリック
3. 上記 JSON をコピペして **Save Changes**
4. **OAuth & Permissions** → **Reinstall to Workspace** をクリック
5. ターミナルで: `openclaw gateway restart`
6. Slack で `@Anicca test` を送信してテスト
