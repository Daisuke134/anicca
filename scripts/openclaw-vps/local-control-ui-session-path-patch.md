# OpenClaw dist パッチ: sessionFile 絶対パス保存の防止

「Session file path must be within sessions directory」の恒久対策として、sessions.json に書き戻す `sessionFile` を常に basename（例: `xxxx.jsonl`）にするパッチ。

## 適用済み（2026-02-13）

- gateway 停止 → 4ファイルにパッチ適用 → local-fix-session-path.js で既存 sessions.json 修正 → gateway 再起動
- 検証: abs_count=0, openclaw gateway health OK

## パッチ対象ファイル

`/opt/homebrew/lib/node_modules/openclaw/dist/` 内の以下4ファイル:

| ファイル | 関数 |
|----------|------|
| pi-embedded-helpers-DP9eeE_7.js | appendAssistantMessageToSessionTranscript |
| pi-embedded-helpers-DVHjAjCj.js | appendAssistantMessageToSessionTranscript |
| sandbox-Bz_i-Ifh.js | appendAssistantMessageToSessionTranscript |
| sandbox-BZDlvSgL.js | appendAssistantMessageToSessionTranscript |

## 変更内容

各ファイルの `appendAssistantMessageToSessionTranscript` 内で:

1. `resolveSessionFilePath` の直後に追加: `const sessionFileForStore = path.basename(sessionFile);`
2. `updateSessionStore` の条件・保存: `sessionFile` → `sessionFileForStore`
3. 戻り値: `sessionFile` → `sessionFile: sessionFileForStore`

※ `emitSessionTranscriptUpdate(sessionFile)` はフルパスのまま（ファイル操作用）

## 再発時（npm install -g openclaw 後など）

1. gateway 停止
2. 上記4ファイルに同パッチを再適用
3. `node scripts/openclaw-vps/local-fix-session-path.js`
4. gateway 再起動
5. 検証（下記）

## 検証コマンド

```bash
# abs_count が 0 であること
python3 - <<'PY'
import json, os
p=os.path.expanduser('~/.openclaw/agents/anicca/sessions/sessions.json')
data=json.load(open(p))
bad=[(k,v.get('sessionFile')) for k,v in data.items() if isinstance(v.get('sessionFile'),str) and v.get('sessionFile').startswith('/')]
print("abs_count", len(bad))
PY

openclaw gateway health
tail -n 100 ~/.openclaw/logs/gateway.err.log | grep "Session file path" || echo "OK"
```
