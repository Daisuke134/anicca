# Composio実装バックアップ（復元可能）

## 復元方法
以下のファイルを作成して、環境変数を設定すれば即座に復元可能

## 1. ファイル: anicca-proxy-slack/src/api/composio/calendar-mcp.js

```javascript
import { Composio } from '@composio/core';
import { OpenAIResponsesProvider } from '@composio/openai';

export default async function handler(req, res) {
  try {
    const { userId } = req.body;
    if (!userId) return res.status(400).json({ error: 'userId is required' });

    const composio = new Composio({
      apiKey: process.env.COMPOSIO_API_KEY,
      provider: new OpenAIResponsesProvider(),
    });

    const serverName = `gcal-${userId}`;

    const allowed = [
      'GOOGLECALENDAR_LIST_CALENDARS',
      'GOOGLECALENDAR_EVENTS_LIST',
      'GOOGLECALENDAR_CREATE_EVENT',
      'GOOGLECALENDAR_UPDATE_EVENT',
      'GOOGLECALENDAR_DELETE_EVENT',
      'GOOGLECALENDAR_FIND_EVENT',
    ];

    // 1) Auth Config を厳密に選択（toolkit.slug === 'GOOGLECALENDAR'）
    const authConfigsResponse = await composio.authConfigs.list();
    const googleCalendarAuthConfig =
      authConfigsResponse.items.find((cfg) => {
        const slug = (cfg.toolkit?.slug || '').toUpperCase().replace(/[-_]/g, '');
        return slug === 'GOOGLECALENDAR';
      }) ||
      (process.env.COMPOSIO_AUTH_CONFIG_ID_GOOGLECALENDAR
        ? authConfigsResponse.items.find((cfg) => cfg.id === process.env.COMPOSIO_AUTH_CONFIG_ID_GOOGLECALENDAR)
        : null);

    if (!googleCalendarAuthConfig) {
      throw new Error('No Google Calendar auth config found. Please create one first.');
    }

    // 2) まずは常に create（既存なら既存を返す糖衣）
    const serverResp = await composio.mcp.create(
      serverName,
      [{ authConfigId: googleCalendarAuthConfig.id, allowedTools: allowed }],
      { isChatAuth: true }
    );

    // 3) 接続状態チェック
    const status = await composio.mcp.getUserConnectionStatus(userId, serverResp.id);
    console.log('Connection status:', JSON.stringify(status, null, 2));

    const toolkits = status.connectedToolkits || {};
    const googleToolkit = Object.values(toolkits).find((tk) => {
      const t = (tk.toolkit || '').toUpperCase().replace(/[-_]/g, '');
      return t === 'GOOGLECALENDAR';
    });
    const isConnected = !!googleToolkit && googleToolkit.connected === true;

    if (!isConnected) {
      // 4) 未接続 → toolkitレベルのauthorize（サーバretrieveに依存しない）
      const connReq = await composio.toolkits.authorize(userId, 'google-calendar');
      return res.json({
        connected: false,
        authUrl: connReq.redirectUrl,
        message: 'Google Calendar authentication required',
      });
    }

    // 5) 接続済 → server_url を払い出し（create戻りの糖衣 getServer を活用）
    const resp = await serverResp.getServer({ userId });

    // プロバイダにより配列/単一の場合があるためフォールバック
    const mcpUrl =
      resp?.[0]?.server_url ||
      resp?.mcpUrl || resp?.mcp_url ||
      resp?.url || resp?.[0]?.url;

    if (!mcpUrl) {
      console.error('Invalid server URLs:', resp);
      throw new Error('Failed to get MCP server URL');
    }

    return res.json({ connected: true, mcpUrl, serverId: serverResp.id, message: 'Google Calendar connected successfully' });
  } catch (error) {
    console.error('Calendar MCP error:', error);
    return res.status(500).json({ error: 'Internal server error', message: error.message });
  }
}
```

## 2. Desktop側: src/agents/remoteMcp.ts

```typescript
export async function resolveGoogleCalendarMcp(userId: string): Promise<McpServerConfig | null> {
  const url = `${PROXY_URL}/api/composio/calendar-mcp`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId })
  });

  const data = await res.json();
  if (data.connected && data.mcpUrl) {
    return { 
      serverLabel: 'google_calendar', 
      serverUrl: data.mcpUrl 
    };
  }
  return null;
}
```

## 3. 必要な環境変数（Railway）

```env
COMPOSIO_API_KEY=your-composio-api-key
COMPOSIO_AUTH_CONFIG_ID_GOOGLECALENDAR=your-auth-config-id
```

## 4. server.js設定

```javascript
// Composio calendar-mcp endpointの追加
app.all('/api/composio/calendar-mcp', composioCalendarMcpHandler);
```