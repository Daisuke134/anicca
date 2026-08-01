# Remote Control 堅牢化 (phone → Mac mini が切れ続ける問題)

作成: 2026-08-01 / branch: `fix/cleanup-control-runtime-restore`
対象: `com.anicca.claude-remote-control` (LaunchAgent) + `claude remote-control --name "Mac mini"`

---

## 1. Goal (done 条件)

```
done = 以下がすべて真
  A. remote-control.log の合計サイズに物理上限がある (回転が効いている実測)
  B. 401 発生時に 90秒ループが起きない (サーキットブレーカが 2回目で停止)
  C. 401 で停止したことが Dais に通知として届く (無音で2時間放置されない)
  D. plist が launchd BP 準拠 (zsh -l 廃止 / PATH 明示 / ProcessType / ExitTimeOut)
  E. 上記変更後も remote-control が Connected を維持している
```

---

## 2. なぜ壊れていたか (実測済み、2026-08-01)

| 事実 | 実測値 | 取得方法 |
|---|---|---|
| 切断の正体 | `com.anicca.claude-remote-control` が **14:23:27〜16:28:48 に83回** 再起動 (90.5秒周期) | `/usr/bin/log show --predicate 'process == "launchd" AND eventMessage CONTAINS "claude-remote-control"'` |
| 引き金 | `[14:23:25] Error: Failed to stop work cse_...: StopWork: Authentication failed (401): Invalid authentication credentials. Remote Control is only available with claude.ai subscriptions. Please use /login` | `~/.claude/logs/remote-control.log:503073` |
| launchctl 最終終了 | `-15` (SIGTERM) | `launchctl list \| grep claude-remote-control` |
| 過去の別死因 | `zsh:1: command not found: claude` (PATH 未解決) | `~/.claude/logs/remote-control.err.20260731-090457` |
| 過去の別死因 | ロック済み `ci-signing.keychain-db` が検索リストに居て `security` 全読取りがハング | memory `feedback_locked_keychain_in_search_list_hangs_all_reads` (2026-07-31) |
| ログ肥大 | `remote-control.log` 38MB + 旧 148MB (TUI の ANSI 再描画が丸ごと落ちる) | `ls -la ~/.claude/logs/` |
| ディスク | `/System/Volumes/Data` 97% (残り 7.3GB)、`~/.openclaw` 14G | `df -h` / `du -sh` |

**恒久障害ではないことの実測 (2026-08-01 16:50 時点)**:

```
PID 44122 の env: 21変数、ANTHROPIC_* / CLAUDE_CODE_* / DISABLE_* ゼロ  (ps eww)
claude auth status: loggedIn=true, authMethod=claude.ai, apiProvider=firstParty, subscriptionType=max
claude doctor: Remote Control セクションに失敗チェック無し
```

→ **設定は壊れていない。401 はサーバー側セッション状態。プロセス再起動では直らない。**

---

## 3. 裏取り (best practice / 車輪の再発明チェック)

| # | 論点 | 結論 | 出典 |
|---|---|---|---|
| 3.1 | launchd で常駐させるのは公式サポート? | **No。** docs はサーバーモードを "stays running in your terminal" としか書かない。headless/daemon 化は open FR **#30447**、launchd 起動で「Not logged in」になるバグ open **#77213**、ユーザー idle 中に worker が凍る open **#80827** | https://docs.claude.com/en/docs/claude-code/remote-control.md |
| 3.2 | `ANTHROPIC_BASE_URL` が proxy を指すと? | **v2.1.196 以降 Remote Control 無効化。** 「Remote Control is only available when using Claude via api.anthropic.com」。この環境は CLIProxyAPI `:8317` を使うため最大の容疑者だった → **実測でシロ (§2)** | 同上 |
| 3.3 | 他に RC を殺す env | `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` (setup-token 系はフルスコープでないため不可) / `DISABLE_TELEMETRY` / `DO_NOT_TRACK` / `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` / `DISABLE_GROWTHBOOK` | 同上 |
| 3.4 | 401 の既知原因 | (a) トークン期限切れ → **#36482 で maintainer ashwin-ant「v2.1.88 で bridge が事前リフレッシュ + 401 で再接続するよう修正済」** (b) サーバー側セッション消失 → open #53635 / #30102 / #80311 (c) **Trusted Devices: サインインから18時間超で失効、人間の `/login` + 生体認証が必須** | gh issues + remote-control.md |
| 3.5 | 401 に再起動は効くか | **効かない。** #53635 / #30102 はトークンが独立に有効なまま401。自前の83回リトライと一致 | 同上 |
| 3.6 | launchd に指数バックオフはあるか | **無い。** Apple の launchd ソース `src/core.c` に失敗カウンタも諦め処理も存在しない。`ThrottleInterval` は既定10秒の**固定**、しかも「ジョブ起動時刻から」計測するため長時間動いた後の再起動は遅延ゼロ | `man 5 launchd.plist` / apple-oss-distributions/launchd |
| 3.7 | `KeepAlive` の形 | dict のサブキーは OR される。`NetworkState` は「no longer implemented as it never acted how most users expected」。`RunAtLoad` は KeepAlive が含意するので省略 | `man 5 launchd.plist` |
| 3.8 | ログ回転に newsyslog は使えるか | **使えない。** launchd は spawn 時に `StandardOutPath` を1回 open して fd を保持 → rename 回転すると書き手は古い inode に書き続け、新ファイルは永久に0バイト。newsyslog に `copytruncate` 相当は無い (flags = BCDGJNUZ- 全確認) | `man 5 launchd.plist` / `man 5 newsyslog.conf` / サブエージェント実機再現 |
| 3.9 | 正しいログ回転 | **`/usr/sbin/rotatelogs` (macOS 同梱、Apache httpd)** にパイプ。回転するのが rotatelogs 自身なので fd 問題が原理的に起きない。実運用例: `rkitover/wemohue` の launchd plist | https://github.com/rkitover/wemohue/blob/master/launchctl/com.magneto.wemoswitchdaemon.plist |
| 3.10 | ANSI 除去 | `sed 's/\x1b\[[0-9;]*[A-Za-z]//g'` は **不完全** (private-mode `ESC[?25l` が残る)。`perl -pe 'BEGIN{$\|=1} s/\e\[[0-9;?]*[ -\/]*[@-~]//g'` は完全除去。macOS 同梱 perl のみ、追加依存ゼロ。`ansi2txt` は Homebrew に無い | サブエージェント実機検証 |
| 3.11 | 非対話の認証ヘルスチェック | **`claude auth status`** (JSON 既定、exit 0) と **`claude doctor`** ("Remote Control" 適格性セクションを出す)。トークン更新コマンドは存在しない | `claude auth --help` 実行 |
| 3.12 | `auth status` は401 検知に十分か | **不十分。** `/bridge`・code-session エンドポイントを叩かないため、401 中でも green を返す (#78453「他の認証接続は正常、401 は code-session/bridge だけで単独発生」)。→ **検知はログパターンで行う** | gh #78453 |
| 3.13 | 既存 OSS supervisor | `Silversteelsolutions/claude-remote-control-supervisor` の1件のみ (★0、Linux/systemd + tmux 専用)。**macOS/launchd 版は存在しない** → ラッパーは自作せざるを得ない。ただし回転と ANSI 除去は既存品 (rotatelogs / perl) を使い、自作は最小限に留める | gh search repos |
| 3.14 | Wi-Fi ch100 DFS が主因か | **主因ではない (自説を撤回)。** ch100 が JP W56 の DFS なのは正 (`wireless-regdb`: `country JP: (5490-5730 @ 160), DFS`)。ただしコストは ETSI EN 301 893 Table D.1 で Channel Move Time 10s + CAC 60s = **最大90秒程度**。10分CAC は 5600–5650MHz 帯のみで ch100@80MHz (5490–5570) は**非該当**。2時間の切断は説明できない | ETSI EN 301 893 V2.1.1 §4.2.6.2.5 + Table D.1 |
| 3.15 | 有線化の根拠 | Apple Platform Deployment「**For best results, deploy content caching on a Mac that has a single wired Ethernet connection as its only connection to the network.**」。DFS が主因でなくても、DFS・ローミング・5GHz PHY 変動を一手で除去できて費用ゼロ | https://support.apple.com/guide/deployment/content-caching-in-macos-depde72e125f/web |
| 3.16 | pmset は関係するか | **無関係。** `SleepDisabled 1` / `sleep 0` = このマシンは眠らない。powernap / womp / tcpkeepalive はすべて睡眠中のみ作用 | `pmset -g` 実測 |

---

## 4. TODO (順序が正本。番号順に着手、飛ばさない)

| # | タスク | 状態 |
|---|---|---|
| 1 | ログ回転: plist を `perl` ANSI除去 + `rotatelogs -n 5 10M` パイプに (上限50MB) | **done 2026-08-01 17:22** (§4.1) |
| 2 | plist 衛生: `zsh -l` 廃止 / `EnvironmentVariables.PATH` 明示 / `ProcessType` / `ExitTimeOut=30` / `ThrottleInterval=60` / `RunAtLoad` 削除 | **done 2026-08-01 17:35** (§4.2) |
| 3 | 401 サーキットブレーカ: ログに `Authentication failed (401)` 検知 → 20秒後に1回だけリトライ → まだ401なら `launchctl bootout` + sentinel 書いて停止 | **done 2026-08-01 17:48** (§4.3) |
| 4 | 通知: sentinel が立ったら Dais へ「`claude auth login` が必要」を送る (18時間ルールは人間しか解けない = 正当な human-loop) | **done 2026-08-01 17:52** (§4.4) |
| 5 | 有線化: Mac mini 背面 Ethernet にLANケーブル → ルーター。**Dais の物理作業**。優先度最下位 | pending (Dais) |
| 6 | 掃除: 重複 tailscale LaunchAgent (exit 1) 削除 / orphaned npm `@anthropic-ai/claude-code` 削除 / `~/.openclaw` 14G 回収 | **done 2026-08-01 18:02** (§4.6) |
| 7 | **回帰修正**: `health-check.sh` がラッパー PID を見て毎分 `kickstart -k` を撃っていた (#1 が引き起こした) | **done 2026-08-01 17:49** (§4.7) |
| 8 | ディスク出血の追跡 (colima VM / codex sqlite)。**本 spec の範囲外**、別タスク | pending (§4.8) |

---

### 4.1 実測ログ — #1 ログ回転 (2026-08-01 17:22 完了)

やったこと: `~/.claude/scripts/remote-control-supervise.sh` を新設し、plist の `ProgramArguments` をそれ1本に置換。`StandardOutPath` は**削除**（残すと launchd と rotatelogs が二重に書く）。`StandardErrorPath` は `remote-control.boot.err` に退避（exec 前のエラー専用）。

途中で見つけた不具合と修正:

| 事象 | 対処 |
|---|---|
| `perl` の CSI 除去だけでは ESC が4行残った | この TUI は **OSC 8 ハイパーリンク** (`ESC]8;;URL BEL text ESC]8;; BEL`) も吐く。OSC を別ルールで剥がし、URI は診断用に本文として残す形に変更 |
| `launchctl bootstrap` が `5: Input/output error` で失敗 | bootout 直後は domain が落ち着いていない。数秒空けて再実行で `rc=0`。**plist は `plutil -lint` で OK、原因は plist ではない** |

実測 (自分の目で確認):

```
# 稼働プロセス3本
8669 /bin/zsh /Users/anicca/.claude/scripts/remote-control-supervise.sh
8681 /Users/anicca/.local/bin/claude remote-control --name Mac mini
8683 /usr/sbin/rotatelogs -n 3 -f /Users/anicca/.claude/logs/remote-control.log 10M

# ANSI 残存
grep -ac $'\e' ~/.claude/logs/remote-control.log  →  0

# サービス状態
launchctl list | grep claude-remote-control  →  14737  0  com.anicca.claude-remote-control
ログ本文                                      →  ·✔︎· Connected / ·✔︎· Ready

# 回転上限の独立検証 (scratchpad, -n 3 / 100K)
6000行 (~294KB) 投入 → rt.log 4,628B + rt.log.1 102,440B + rt.log.2 102,440B = 216K で頭打ち
→ 本番の -n 5 / 10M = 合計 50MB 上限
```

副次効果: 肥大した旧ログを削除して `~/.claude/logs` が **186M → 4K**、ディスク空きが **7.1GB → 8.6GB**。401 の証拠行だけ `remote-control.401-evidence.txt` に退避済み。

**注意 (ソースの二重化)**: 実体は `~/.claude/scripts/remote-control-supervise.sh`（ブランチに依存させないため）。`scripts/runtime/remote-control-supervise.sh` はリポジトリ側のミラー。触ったら必ず `diff` で一致を確認すること。

---

### 4.2 実測ログ — #2 plist 衛生 (2026-08-01 17:35 完了)

`man 5 launchd.plist` を実物で読んでから決めた。verbatim 引用:

| キー | man の記述 | 採用値 |
|---|---|---|
| `RunAtLoad` | "The default is false. **This key should be avoided**, as speculative job launches have an adverse effect on system-boot and user-login scenarios." / KeepAlive 側: "**The use of this key implicitly implies RunAtLoad**" | **削除** |
| `ThrottleInterval` | "jobs will not be spawned more than once every **10 seconds**" (既定) | `60` |
| `ProcessType` | "**If left unspecified, the system will apply light resource limits to the job, throttling its CPU usage and I/O bandwidth.**" / Interactive: "run with the same resource limitations as apps, that is to say, none… should only be used if an app's ability to be responsive depends on it" | **`Interactive`** — Background だと disk I/O が絞られる。これは Dais が電話から叩く対話経路であり、配下で Claude Code がビルド/テストを回すため |
| `ExitTimeOut` | SIGTERM→SIGKILL の猶予。`0` は無限を意味する | `30` |

**途中で見つけた実害 (#1 の副作用)**: `zsh -lc` をやめた結果、`~/.zshenv` しか読まれなくなり **PATH が痩せた**。

```
before (旧 plist, PID 44122): 21 vars / PATH に ~/.local/bin, solana, homebrew/sbin, Cryptexes, TeX, quarto あり
after  (#1 直後,  PID 19358): 16 vars / PATH = ~/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:...
                               ← ★ ~/.local/bin が消滅 = claude 自身が PATH から引けない ★
```

スクリプトは絶対パスで claude を起動するので起動自体は成功していたが、**セッション内から `claude` や `gh` を呼ぶ経路が壊れる**ところだった。`EnvironmentVariables.PATH` に旧 PATH を明示して復旧。

実測 (リロード後):

```
launchctl list           →  24158  -15  com.anicca.claude-remote-control   (-15 は bootout の SIGTERM、正常)
プロセス3本               →  supervise.sh 24158 / claude remote-control 24182 / rotatelogs 24184
PATH                     →  /opt/homebrew/bin:...:/Users/anicca/.local/bin:... ★復帰★
ログ本文                  →  ·✔︎· Connected / ·✔︎· Ready
grep -ac $'\e' log       →  0
boot.err                 →  0 bytes
```

**運用上の注意**: `ThrottleInterval=60` を入れたので、`bootout` 直後の `bootstrap` では最大60秒プロセスが上がらない。この間 `launchctl list` は PID 欄が `-` になる。**壊れたと誤認しないこと。**

---

### 4.3 実測ログ — #3 401 サーキットブレーカ (2026-08-01 17:48 完了)

設置先は supervisor スクリプト本体（別プロセスの watchdog にしない — パイプの終了を直接見られる方が確実で、監視対象と監視者がずれない）。

判定ロジック:

```
claude 終了
  ├ 直近400行に 401 パターン無し
  │    └ 600秒以上動いていたら計数と sentinel をリセット → 通常終了 (launchd が再起動)
  └ 401 あり
       ├ 窓(600秒)内 1回目 → 20秒待ってから終了。launchd が1回だけ再試行
       └ 窓内 2回目      → sentinel 書く → 通知呼ぶ → launchctl bootout で自分を降ろす
```

設計上の要点:

| 判断 | 理由 |
|---|---|
| 検知は**ログパターン**、`claude auth status` ではない | `auth status` は `/bridge`・code-session を叩かないので **401 中でも green を返す**（gh #78453「他の認証接続は正常、401 は code-session/bridge だけで単独発生」）。実際 401 の最中に `loggedIn=true, subscriptionType=max` が返っていた |
| 1回目は**即再起動せず20秒待つ** | gh #78453 の報告者「CLI 起動直後の自動接続は失敗するが、数秒後の手動リトライは 3/3 で成功」 |
| 2回目で**自分を bootout** | `KeepAlive=true` はどんな終了コードでも再起動する。止める手段は自分を降ろすことだけ |
| 諦める閾値は 2 | 83回リトライして一度も直らなかった実績。2回で十分 |

sandbox 検証（$HOME ごと隔離、偽 claude が 401 を吐く、`launchctl bootout` はスタブに置換して本番を巻き込まない）:

```
--- run 1 ---  rc=1
  [supervise] 401 detected (hit 1/2 in 600s window) after 0s: ...
  [supervise] backing off 20s, then letting launchd respawn once
--- run 2 ---  rc=1
  STUB-BOOTOUT  gui/501/com.anicca.claude-remote-control      ← bootout が呼ばれた
  [supervise] CIRCUIT BREAKER OPEN — booting out the job
  sentinel: hits=2 in 600s / last_error=...(401 の実文言)... / fix=claude auth login

--- 誤爆しないことの確認 (401 を含まず exit 7 する偽 claude) ---
  rc=7 (終了コードが透過している)
  sentinel: 無し
  [supervise] exit rc=7 after 0s, no 401 in log — letting launchd restart
```

本番反映後の実測:

```
launchctl list  →  32091  0  com.anicca.claude-remote-control
プロセス3本      →  supervise.sh 32091 / claude remote-control 32106 / rotatelogs 32108
ログ            →  ·✔︎· Connected
~/.claude/state →  401 関連ファイル無し (誤爆していない)
supervise.log   →  空 (インシデント無し)
```

新しく増えたファイル: `~/.claude/logs/remote-control.supervise.log`（監視側の判断ログ。TUI 出力とは別系統。**回転対象外なので行数は極小に保つこと**）、`~/.claude/state/remote-control-401.{count,sentinel}`。

---

### 4.4 実測ログ — #4 通知 (2026-08-01 17:52 完了)

**通知経路は新設していない。** 停電通知 `~/recovery-setup/boot-notify.sh` が既に使っている Telegram bot をそのまま再利用する（`~/.openclaw/.env` の `TELEGRAM_BOT_TOKEN` / `TELEGRAM_ALERT_CHAT_ID`、送信前にネット復帰を待つ形も踏襲）。Dais が見る場所を増やさないため。

`~/.claude/scripts/remote-control-notify.sh` — sentinel の中身をそのまま本文に載せ、直し方（`claude auth login` → `launchctl bootstrap`）を添えて送る。

実配信で検証（Dais 自身のアラート channel に、テストと明記した1通）:

```
notify: telegram http=200
rc=0
```

supervisor からの呼び出し配線も sandbox で確認（実送信を重ねないようスタブに差し替え）:

```
[supervise] CIRCUIT BREAKER OPEN — booting out the job. see .../remote-control-401.sentinel
STUB-NOTIFY called with: .../remote-control-401.sentinel      ← bootout の前に発火している
```

**なぜここだけ人を呼ぶのか**: 401 の解除は対話セッションでの `claude auth login`（Trusted Devices 下では生体認証つき）が要る。機械では解けない。黙って諦めるのは「2時間気づかない」の再現なので、必ず届ける。

---

### 4.6 実測ログ — #6 掃除 (2026-08-01 18:02 完了)

| 対象 | 判断根拠 (自分で確認したこと) | 結果 |
|---|---|---|
| orphaned npm `@anthropic-ai/claude-code` (28M) | 稼働中の claude は `~/.local/bin/claude → ~/.local/share/claude/versions/2.1.210` (native installer)。`/opt/homebrew/bin/claude` は**存在しない** = この node_modules を指す経路が無い | 削除。削除後 `claude --version` → `2.1.210 (Claude Code)` |
| 重複 tailscale LaunchAgent | system 側 `/Library/LaunchDaemons/homebrew.mxcl.tailscale.plist` が `state = running` (PID 313 = tailscaled 本体)。user 側 `gui/501` は `state = spawn scheduled` で **2本目の tailscaled を spawn し続けて失敗** (exit 1) | bootout + plist 削除。削除後も PID 313 健在、`tailscale status` 正常 |
| `~/.openclaw/logs/article-daily.log` 204M + `article-resume.log` 132M | remote-control と**同じ病気** (launchd の無制限 stdout)。書き手が fd を握っているので `rm` せず **in-place で末尾200KBに切り詰め** | 336M → 390K |
| `~/.openclaw/tmp` の7日超ファイル 6264個 | playwright の `.crdownload` 残骸、node コンパイルキャッシュ等、全て再生成可能 | 56M → 4K |

`~/.claude/logs` は 186M → 36K。ディスク空きは **セッション開始時 7.1GB → 9.6GB**。

`~/.openclaw/.git` が 3.3G あるが、稼働中リポジトリの `gc` は別件として残す（本 spec の範囲外）。

### 4.7 回帰 — #7 health-check がラッパーを殺していた

**#1 で自分が壊した。** 全部直したはずなのに PID が入れ替わり続けたので追った。

```
17:35:30 pid=56846 etime=00:53
17:35:51 pid=56846 etime=01:14
17:36:01 pid=61377 etime=00:03     ← 交代
17:37:11 pid=61377 etime=01:13
17:37:21 pid=63436 etime=00:02     ← 交代 (約78秒周期)
```

`supervise.log` が空 = スクリプトの終了処理に到達していない = 外から SIGTERM されている。犯人は `~/recovery-setup/health-check.sh:75`:

```sh
cpid=$(launchctl list | awk '/com.anicca.claude-remote-control/{print $1}')
conns=$(lsof -nP -p "$cpid" | grep -c ESTABLISHED)
[ "$conns" -ge 1 ] || launchctl kickstart -k gui/501/com.anicca.claude-remote-control
```

`launchctl list` が返すのは**ジョブの PID**。#1 より前はそれが `claude` 自身だった（旧 plist が `exec` していたため）。今はラッパー zsh なので、ソケットは子が持つ:

```
wrapper=54828 → ESTABLISHED 0
child=61391   → ESTABLISHED 1
```

→ 毎回 `no_conn` と判定 → `kickstart -k` (= SIGTERM) → `StartInterval=60` + `ThrottleInterval=60` で約78秒周期。**元の 90 秒ループを別の原因で再現していた。**

修正 (`health-check.sh`):

| 変更 | 理由 |
|---|---|
| 子 `claude remote-control` の PID も lsof 対象に加える | ソケットの所在に判定を合わせる |
| PID が `-` = `restarting` として扱い bootstrap を撃たない | ThrottleInterval の待ち中を DOWN と誤認して正常な再起動と競合するのを防ぐ |
| sentinel があるときは復帰させず `DOWN_401_needs_login` と表示するだけ | **これが無いと health-check が毎分 bootstrap し直し、#3 のサーキットブレーカが完全に無効化される** |

**一般法則**: 常駐プロセスにラッパーを噛ませたら、**そのジョブの PID を見ている監視側を必ず洗う**。「ジョブの PID = 実体の PID」を暗黙に仮定した監視は、ラッパー導入の瞬間に全部壊れる。

修正後の実測 (10秒間隔サンプリング):

```
17:37:41 pid=63436 etime=00:22
...                              ← 同一 PID が途切れない
17:41:23 pid=63436 etime=04:04
17:48:49 pid=63436 etime=11:30   ← 修正前は 78 秒で必ず死んでいた

health.log (毎分):
2026-08-01 17:47:08 net=ok ts=ok codex2=connected claude=ok
2026-08-01 17:48:22 net=ok ts=ok codex2=connected claude=ok
```

### 4.8 範囲外の発見 — ディスクが別口で出血している

作業中に空きが **9.6GB → 5.4GB へ約10分で減少**。remote-control ではない（`~/.claude/logs` は 76K）。継続的に書かれている大物:

| 対象 | 状態 |
|---|---|
| `~/.colima/_lima/colima/disk` / `_disks/colima/datadisk` | colima VM が**稼働中で成長し続けている**。停止は稼働中ワークロードへの介入なので本 spec では触らない |
| `~/.codex/logs_2.sqlite` (464M) | 継続的に書き込みあり |
| Chromium `code_sign_clone` 13個 | `du` は 4.5G と表示するが **APFS の共有ブロックで実容量はほぼゼロ**。稼働中 Chromium が1つも参照していないことを2手法で確認して削除したが、**空きは 6GB → 6GB で変化なし**。`du` の数字を実容量と読んだのは誤り |

→ タスク #8 として分離。**「ストレージが原因では?」という当初の問いへの答えは変わらず No** — 電話が切れていた原因は 401 と kickstart ループであり、ディスクではない。ただしディスク自体は別途手当てが要る。

---

## 5. 残存リスク / 自分が間違うとしたら最有力の筋

401 の真因が 18時間ルールでもサーバー側でもなく、**このMacで同時に走る複数の `claude` プロセスが同じ OAuth 資格情報でリフレッシュトークンを取り合っている**線。gh #53635 のコメントに「1つの `.credentials.json` を共有する5デーモンが朝までに全滅」という状況証拠がある。**UNVERIFIED。** #1〜#4 を入れた上で、401 の発生時刻と他 claude ジョブの起動時刻を突き合わせれば切り分けられる。

---

## 6. 関連ファイル

| path | 役割 |
|---|---|
| `~/Library/LaunchAgents/com.anicca.claude-remote-control.plist` | 対象の LaunchAgent |
| `~/.claude/logs/remote-control.log` / `.err` | 捕捉ログ (回転対象) |
| `~/.claude/scripts/` | サーキットブレーカ設置先 |
| memory `feedback_locked_keychain_in_search_list_hangs_all_reads` | 過去の死因 (keychain 検索経路) |
| `docs/superpowers/specs/2026-08-01-blackout-autorecovery-design.md` | 別トピック (停電)。混同しないこと |
