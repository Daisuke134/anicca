# iPhoneからClaude Code / Codexをリモート操作する

## 結論

ClaudeとCodexは接続方式が異なる。

| 製品 | iPhoneの入口 | リモート端末側 | 初回ペアリング | VPS |
|---|---|---|---|---|
| Claude Code | Claude iOSの`Code` | `claude remote-control` | QRは任意 | VPSへ直接常駐できる |
| Codex | ChatGPT iOSの`Remote` | ChatGPT/Codex Desktop | Desktopに表示されるQRが必要 | DesktopからSSHホストとして接続する |

端末の電源が切れている間は、どちらも接続できない。停電復旧後の自動再接続には、端末の自動電源復旧、OSログイン、Remoteプロセスの自動起動、有効な認証、ネット接続がすべて必要になる。

## Codex: 推奨構成

### Mac / WindowsをiPhoneへ接続する

Codexの公式モバイルRemoteはChatGPT/Codex Desktopをホストにする。

1. ホスト端末とiPhoneで同じChatGPTアカウント、ワークスペースへログインする。
2. ホスト端末でChatGPT/Codex Desktopを開く。
3. サイドバーの`Set up Remote`を開く。
4. Desktopに表示されたQRコードをiPhoneで読み取る。
5. iPhoneのChatGPTアプリでペアリングを完了する。
6. 以後はChatGPT iOSの`Remote → ホスト → 新規チャット`から新規Codexセッションを作る。QRを毎回読む必要はない。
7. Desktopの`Settings → Connections`でRemote、スリープ防止、接続済み端末を管理する。

ホストがスリープする、ネットを失う、Desktopアプリを終了する、ChatGPTからログアウトする、のいずれかでRemoteは停止する。ログアウト後もペアリング情報は残るが、Remoteを再び有効にする必要がある。

### 停電・再起動後に復旧させる

Mac / Windowsホストは次を満たすようにする。

| 設定 | 目的 |
|---|---|
| 停電後の自動電源復旧 | 電源が戻ったら端末を起動する |
| スリープ無効 | Remoteホストをオンラインに保つ |
| ChatGPT/Codex Desktopをログイン項目へ追加 | OSログイン後にアプリを自動起動する |
| ユーザーセッションへログイン | Desktop、資格情報、Computer Useを利用可能にする |
| UPS | 短い停電で端末を落とさない |

Desktopアプリはユーザーセッション上で動くため、再起動後にログイン画面で止まるとRemoteは復旧しない。無人復旧を優先して自動ログインを使う場合は、物理アクセスとディスク暗号化のリスクを別途評価する。

### Codex Desktopを監視して再起動する

このMacでは`~/Library/LaunchAgents/com.anicca.codex-remote-watchdog.plist`を使う。`RunAtLoad=true`、`StartInterval=60`とし、次の判定を60秒ごとに実行する。

```bash
/usr/bin/pgrep -f '/Applications/Codex.app/Contents/MacOS/ChatGPT' \
  >/dev/null || /usr/bin/open -a Codex
```

LaunchAgentを読み込む。

```bash
launchctl bootstrap \
  "gui/$(id -u)" \
  "$HOME/Library/LaunchAgents/com.anicca.codex-remote-watchdog.plist"

launchctl kickstart \
  "gui/$(id -u)/com.anicca.codex-remote-watchdog"
```

状態を確認する。

```bash
launchctl print \
  "gui/$(id -u)/com.anicca.codex-remote-watchdog"
```

watchdogはCodex Desktopが停止している場合だけアプリを開く。Codex DesktopのRemoteホストとCLI daemonを重複起動しない。

### Codex CLIのRemote Control daemon

Codex CLIには実験的なRemote Control daemonがある。

```bash
codex remote-control start
codex remote-control pair
codex remote-control stop
```

- `start`: Remote Controlを有効にしたapp-server daemonを起動する。
- `pair`: 短時間だけ有効な手動ペアリングコードを発行する。
- `stop`: daemonを停止する。

daemonにはCodex公式standaloneインストールが必要になる。

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex remote-control start
```

これは実験的な管理・SSHワークフロー用であり、iPhoneの標準セットアップはDesktopの`Set up Remote`から開始する。同じ登録済みホストでDesktop RemoteとCLI daemonを同時起動しない。OpenAI側は2本目を`409 Remote app server already online`として拒否する。

`codex remote-control start`はバックグラウンドdaemonを起動するが、停電・OS再起動後の自動起動まで保証しない。Desktopを使う構成では、Desktopアプリのログイン時自動起動を正本にする。

手動ペアリングコード、QR内容、認証トークンはログ、Git、チャットへ保存しない。

## Codex: VPS上のプロジェクトを使う

公式の推奨経路は、iPhoneからVPSへ直接接続するのではなく、Desktopホストを経由する構成。

```text
ChatGPT iOS
    ↓ Remote
ChatGPT/Codex Desktop（Mac / Windows）
    ↓ SSH
VPS上のCodex app-server、リポジトリ、ツール
```

1. Desktopホストの`~/.ssh/config`へ具体的なVPSエイリアスを登録する。

   ```sshconfig
   Host devbox
     HostName example.com
     User you
     IdentityFile ~/.ssh/id_ed25519
   ```

2. Desktopホストから接続を確認する。

   ```bash
   ssh devbox
   ```

3. VPSへCodexをインストールし、VPS上のユーザーとして認証する。
4. Desktopの`Settings → Connections`でSSHホストを追加する。
5. VPS上のプロジェクトフォルダを選ぶ。
6. iPhoneはDesktopホストへRemote接続し、実行場所としてVPSプロジェクトを使用する。

app-serverのWebSocketやUnix socketをインターネットへ直接公開しない。SSH、VPN、メッシュVPNを使用する。

## Claude Code: VPSへ直接接続する

Claude CodeはVPS自身をRemote Controlサーバーにできる。

```bash
claude auth login
cd /path/to/project
claude remote-control \
  --name "My Remote Device" \
  --spawn worktree \
  --capacity 10
```

同じClaudeアカウントのClaude iOSで`Code → My Remote Device → 新規セッション`を開く。QRはセッションを素早く開くための任意手段で、毎回のペアリングには不要。

24時間運用では、上のプロセスをLinux/VPSなら`systemd`、Macなら`launchd`で管理する。プロセスだけを手動起動した状態、`tmux`、`nohup`はOS再起動後の復旧を保証しない。

## 障害時の挙動

| 障害 | Claude | Codex |
|---|---|---|
| 端末停止中 | 接続不可 | 接続不可 |
| ネット切断 | 一時切断。長時間切断ではプロセス終了の可能性 | Remote停止 |
| OS再起動 | systemd/launchd設定済みなら起動後に復旧 | ログイン後、Desktop自動起動で復旧 |
| 認証失効 | `claude auth login`が必要 | ChatGPT再ログイン、Remote再有効化が必要 |
| 短い停電 | UPSがあれば維持可能 | UPSがあれば維持可能 |

## このMac miniの実測状態

| 対象 | 状態 |
|---|---|
| Claude | `com.anicca.claude-remote-control`が`launchd`で稼働。`RunAtLoad=true`、`KeepAlive=true`、接続済み |
| Mac電源 | AC接続時スリープ無効、停電復旧後の自動起動有効 |
| macOSログイン | FileVault無効、自動ログインユーザー`anicca`設定済み |
| Codex | ChatGPT/Codex DesktopがRemoteホストとしてすでにオンライン。macOSログイン項目へ登録済み |
| Codex watchdog | `com.anicca.codex-remote-watchdog`が60秒間隔でDesktopを監視し、停止時に再起動 |
| Codex CLI daemon | Desktopと重複して`409 Remote app server already online`になるため停止 |
| Codex standalone CLI | `~/.codex/packages/standalone/current/codex`へ導入済み |

このMacでは、Codex DesktopをRemoteの正本にし、CLI daemonを重複起動しない。

## 検証

### Claude

1. Claude iOSの`Code`でホストに緑のオンライン表示がある。
2. `新規セッション`から固有のメッセージを送る。
3. リモート端末上でセッションが生成され、応答が返る。

### Codex

1. ChatGPT iOSの`Remote`にホストがオンライン表示される。
2. ホスト上の保存済みプロジェクトで新規チャットを作る。
3. リモート端末のファイル、シェル、ツールを使った応答が返る。
4. Desktopの`Settings → Connections`にiPhoneが表示される。

## 公式資料

- OpenAI, [Remote connections](https://learn.chatgpt.com/docs/remote-connections.md)
- OpenAI, [Codex CLI command reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli#cli-codex-remote-control)
- Anthropic, [Continue local sessions from any device with Remote Control](https://code.claude.com/docs/en/remote-control)
