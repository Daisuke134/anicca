#!/bin/zsh
# claude remote-control supervisor
#
# spec: ~/anicca-project/docs/superpowers/specs/2026-08-01-remote-control-robustness-design.md
#
# なぜラッパーが要るか:
#   - launchd は StandardOutPath を spawn 時に1回 open して fd を保持するため、
#     rename ベースの回転 (newsyslog) が効かない。回転する側が自分で書く必要がある。
#   - remote-control は TUI なので ANSI 再描画が丸ごとログに落ちる (1日で185MB)。

set -o pipefail
zmodload zsh/datetime   # $EPOCHSECONDS

LOG_DIR="$HOME/.claude/logs"
LOG="$LOG_DIR/remote-control.log"
mkdir -p "$LOG_DIR"

# 認証情報は ci-signing.keychain-db 側にある。ロックされたままだと security の
# 全読取りがヘッドレスで無限ハングする。
# memory: feedback_locked_keychain_in_search_list_hangs_all_reads
KP="$(set -a; . "$HOME/.openclaw/.env" 2>/dev/null 1>/dev/null; printf %s "$KEYCHAIN_PASSWORD")"
/usr/bin/security unlock-keychain -p "$KP" "$HOME/ci-signing.keychain-db" 2>/dev/null
/usr/bin/security set-keychain-settings "$HOME/ci-signing.keychain-db" 2>/dev/null
unset KP

# Remote Control は api.anthropic.com 直でしか動かない (v2.1.196+)。CLIProxyAPI 等を
# 指す env が残ると恒久的に 401 になる。setup-token 系トークンもフルスコープでないため不可。
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL CLAUDE_CODE_OAUTH_TOKEN

# ANSI 除去。CSI だけでは足りない — この TUI は OSC 8 ハイパーリンク
# (ESC]8;;URL BEL text ESC]8;; BEL) も吐く。URL は診断に使うので本文として残す。
STRIP_ANSI='BEGIN{$|=1}
  s/\e\]8;;([^\a\e]*)(?:\a|\e\\)/$1 /g;   # OSC 8: 枠だけ外して URI は残す
  s/\e\][^\a\e]*(?:\a|\e\\)//g;           # その他の OSC
  s/\e\[[0-9;?]*[ -\/]*[@-~]//g;          # CSI (色・カーソル移動・画面消去)
  s/\e[@-Z\\-_]//g;                       # 2文字エスケープ'

STATE_DIR="$HOME/.claude/state"
COUNT_FILE="$STATE_DIR/remote-control-401.count"
SENTINEL="$STATE_DIR/remote-control-401.sentinel"
WINDOW=600   # 401 を数える窓 (秒)
TRIP_AT=2    # この回数に達したら諦める
mkdir -p "$STATE_DIR"

log_note() { print -r -- "[supervise $(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_DIR/remote-control.supervise.log" }

# 前回の停止が残っていても起動自体は妨げない。Dais が /login を直して
# 手で bootstrap し直したケースがこれ。記録だけ残す。
[[ -f "$SENTINEL" ]] && log_note "previous 401 sentinel present, starting anyway: $(cat "$SENTINEL")"

STARTED_AT=$EPOCHSECONDS

# -n 5 = remote-control.log{,.1,.2,.3,.4} の循環、10M で回転 → 合計上限 50MB
# -f   = 起動時に即 open (最初の1行が出るまで待たない)
"$HOME/.local/bin/claude" remote-control --name "Mac mini" 2>&1 \
  | perl -pe "$STRIP_ANSI" \
  | /usr/sbin/rotatelogs -n 5 -f "$LOG" 10M
RC=$?
RAN_FOR=$(( EPOCHSECONDS - STARTED_AT ))

# ---- 401 サーキットブレーカ ----
#
# なぜ要るか: 2026-08-01 に 401 を引き金として launchd の KeepAlive が
# 90 秒周期で 83 回リトライした。401 はサーバ側のセッション/権限状態なので
# プロセスを作り直しても直らない (gh #53635 / #30102 で報告済)。
# launchd 自体に指数バックオフも諦める仕組みも無い (man 5 launchd.plist)。
# よってここで数えて止める。

NOW=$EPOCHSECONDS

LAST_401="$(tail -n 400 "$LOG" 2>/dev/null \
  | grep -aE 'Authentication failed \(401\)|Invalid authentication credentials' \
  | tail -n 1)"

if [[ -z "$LAST_401" ]]; then
  # 健全に終了した。窓が意味を失うので計数をリセットして launchd に再起動させる。
  [[ $RAN_FOR -ge $WINDOW ]] && rm -f "$COUNT_FILE" "$SENTINEL"
  log_note "exit rc=$RC after ${RAN_FOR}s, no 401 in log — letting launchd restart"
  exit $RC
fi

# 窓の外の記録を捨ててから今回を足す
if [[ -f "$COUNT_FILE" ]]; then
  awk -v now="$NOW" -v w="$WINDOW" '$1 > now - w' "$COUNT_FILE" > "$COUNT_FILE.tmp" 2>/dev/null
  mv -f "$COUNT_FILE.tmp" "$COUNT_FILE"
fi
print -r -- "$NOW" >> "$COUNT_FILE"
HITS=$(wc -l < "$COUNT_FILE" | tr -d ' ')

log_note "401 detected (hit $HITS/$TRIP_AT in ${WINDOW}s window) after ${RAN_FOR}s: $LAST_401"

if (( HITS < TRIP_AT )); then
  # 1回目は即時再接続でなく少し置いてから 1 回だけやり直す。
  # gh #78453 の報告者いわく、CLI 起動直後の自動接続は失敗するが
  # 数秒後の手動リトライは 3/3 で成功している。
  log_note "backing off 20s, then letting launchd respawn once"
  sleep 20
  exit $RC
fi

# 2回目 = 諦める。ここで止めないと 83 回ループが再現する。
{
  print -r -- "tripped_at=$(date '+%Y-%m-%d %H:%M:%S')"
  print -r -- "hits=$HITS in ${WINDOW}s"
  print -r -- "last_error=$LAST_401"
  print -r -- "action=circuit breaker opened; launchd job booted out"
  print -r -- "fix=Dais が対話セッションで 'claude auth login' を実行し、"
  print -r -- "    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.anicca.claude-remote-control.plist"
  print -r -- "why=401 はサーバ側セッション状態。Trusted Devices はサインインから18時間で失効し、"
  print -r -- "    人間の /login + 生体認証でしか解けない。再起動では直らない。"
} > "$SENTINEL"

log_note "CIRCUIT BREAKER OPEN — booting out the job. see $SENTINEL"

# 通知 (#4 で配線)
[[ -x "$HOME/.claude/scripts/remote-control-notify.sh" ]] && \
  "$HOME/.claude/scripts/remote-control-notify.sh" "$SENTINEL" >> "$LOG_DIR/remote-control.supervise.log" 2>&1

# KeepAlive=true なのでどんな終了コードでも再起動される。止めるには自分を降ろすしかない。
/bin/launchctl bootout "gui/$(id -u)/com.anicca.claude-remote-control"
exit $RC
