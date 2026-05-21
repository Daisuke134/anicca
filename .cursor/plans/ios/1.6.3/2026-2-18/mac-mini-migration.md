# Mac Mini Migration — VPS → Mac Mini

## ベストプラクティス

Source: `/docs/install/migrating.md`
> "Copy the **state directory** (~/.openclaw/) and your **workspace** (~/.openclaw/workspace/)"
> "Run openclaw doctor on the new machine"

## 前提条件
- workspace-cleanup完了済み（ゴミを移行しない）
- git-versioning完了済み（バックアップがある）

## メリット（AS-IS → TO-BE）

| AS-IS（VPS + Mac SSH） | TO-BE（Mac Mini） |
|---|---|
| gog CLIにSSH必要 → スリープで失敗 | ローカル実行 → スリープ問題なし |
| Codex/Claude CodeにSSH必要 → 認証切れ | ローカル実行 → 認証管理が楽 |
| plansとmemoryが別マシン → 同期問題 | 同じファイルシステム → 同期不要 |
| lunch-music: SSH + caffeinate | `open` コマンドだけ |
| VPS 4GB RAM | Mac Mini 16GB+ |
| ファイルをIDEで見れない | 直接IDEで開ける |

## 移行手順

Source: `/docs/install/migrating.md`

### Step 0: バックアップ（VPS）
```bash
# VPSで
openclaw gateway stop
cd ~
tar -czf openclaw-state.tgz .openclaw
```

### Step 1: Mac MiniにOpenClawインストール
```bash
# Mac Miniで
npm install -g openclaw
```

### Step 2: state dir + workspace転送
```bash
# VPSからMac Miniへ
scp openclaw-state.tgz user@mac-mini:~/
# Mac Miniで
cd ~
tar -xzf openclaw-state.tgz
```

### Step 3: Doctor + Restart
```bash
# Mac Miniで
openclaw doctor
openclaw gateway restart
openclaw status
```

### Step 4: 検証
Source: `/docs/install/migrating.md`
> "Confirm:
> - openclaw status shows the gateway running
> - Your channels are still connected
> - The dashboard opens and shows existing sessions
> - Your workspace files are present"

### Step 5: VPS対応
- VPSのgatewayは停止したまま
- フォールバック用に残す（削除しない）
- 必要ならVPS → Mac Mini間でTailscale接続を維持

## 注意事項

Source: `/docs/install/migrating.md`
> "Footgun: permissions / ownership — ensure the state dir + workspace are owned by the user running the gateway"
> "Footgun: secrets in backups — treat backups like production secrets"

## config変更が必要な項目
- SSH関連のスキル（gmail-digest, gcal-digest, lunch-music） → SSH不要に書き換え
- TOOLS.mdのMac SSH情報 → ローカルパスに更新
- openclaw.jsonのworkspaceパス確認

## 実行タイミング
- workspace-cleanup + git-versioning 完了後
- Daisが今日か明日やりたい意向

---

*作成: 2026-02-18 06:39 UTC*
*Source: `/docs/install/migrating.md`*
