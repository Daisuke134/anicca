# OpenClaw デフォルトモデル設定（2026-03-07 更新）

## 現在の設定
- **Mac Mini デフォルトモデル**: `anthropic/claude-sonnet-4-6`
- **設定箇所**: `/Users/anicca/.openclaw/openclaw.json` → `agents.defaults.model.primary`
- **確認コマンド**: `openclaw models status --plain` → `anthropic/claude-sonnet-4-6`

## 変更履歴
| 日付 | モデル | 理由 |
|------|--------|------|
| 2026-03-04 | `openai-codex/gpt-5.3-codex` | 429エラー・コスト削減のためAnthropicから変更 |
| 2026-03-07 | `anthropic/claude-sonnet-4-6` | ダイスの指示でSonnet 4.6に戻す |

## OpenClaw モデルID形式（公式ドキュメント確認済み）
- Source: https://docs.openclaw.ai/providers/anthropic
- 形式: `anthropic/<model-id>`
- Sonnet 4.6: `anthropic/claude-sonnet-4-6`
- Opus 4.6: `anthropic/claude-opus-4-6`

## 変更手順（再変更が必要な場合）
```bash
# Mac Mini で直接実行
python3 -c "
import json
with open('/Users/anicca/.openclaw/openclaw.json', 'r') as f:
    c = json.load(f)
c['agents']['defaults']['model'] = {'primary': 'anthropic/claude-sonnet-4-6'}
with open('/Users/anicca/.openclaw/openclaw.json', 'w') as f:
    json.dump(c, f, indent=4)
"
openclaw gateway restart
openclaw models status --plain  # 確認
```

## Mac Mini デフォルトモデル確認方法（2026-03-07 確定）

**Mac Mini の OpenClaw デフォルトモデル: `anthropic/claude-opus-4-6`**

### 確認コマンド（必ずこれを使う）

```bash
ssh anicca@100.99.82.95 "cat /Users/anicca/.openclaw/openclaw.json | python3 -c \"import json,sys; d=json.load(sys.stdin); m=d.get('agents',{}).get('defaults',{}).get('model',{}); print(json.dumps(m, indent=2))\""
```

### ⚠️ 絶対禁止: MacBook config と混同するな

| 場所 | パス | 用途 |
|------|------|------|
| **Mac Mini（正解）** | `/Users/anicca/.openclaw/openclaw.json` | Anicca エージェントの設定 |
| **MacBook（間違い）** | `/Users/cbns03/.openclaw/openclaw.json` | ローカル TUI クライアント設定（モデルは別） |

MacBook の config には `openai-codex/gpt-5.3-codex` が入っているが、それは TUI クライアント用。Anicca が使うモデルは Mac Mini の config を見ること。
