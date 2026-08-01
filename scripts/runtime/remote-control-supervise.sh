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

# -n 5 = remote-control.log{,.1,.2,.3,.4} の循環、10M で回転 → 合計上限 50MB
# -f   = 起動時に即 open (最初の1行が出るまで待たない)
"$HOME/.local/bin/claude" remote-control --name "Mac mini" 2>&1 \
  | perl -pe "$STRIP_ANSI" \
  | /usr/sbin/rotatelogs -n 5 -f "$LOG" 10M
