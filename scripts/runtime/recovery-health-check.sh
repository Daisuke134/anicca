#!/bin/bash
# Post-blackout resilience monitor.
# Runs every minute as a LaunchAgent. Checks the three things that must be true
# for the iPhone to reach this Mac, and repairs only what is actually broken.
#
# Deliberately conservative: a repair that fires on a healthy component is worse
# than no repair at all (a keepalive that killed healthy daemons is exactly what
# took the phone offline on 2026-07-31).
set +e

DIR=/Users/anicca/recovery-setup
LOG="$DIR/health.log"
TS=/opt/homebrew/bin/tailscale
CODEX=/Users/anicca/.local/bin/codex
STATUS_PY=/Users/anicca/.codex-remote-status.py
PY=/usr/bin/python3
TIMEOUT=/opt/homebrew/bin/timeout
[ -x "$TIMEOUT" ] || TIMEOUT=""

mkdir -p "$DIR"
unset OPENAI_API_KEY ANTHROPIC_API_KEY

stamp() { date '+%Y-%m-%d %H:%M:%S'; }
say() { echo "$(stamp) $*" >> "$LOG"; }

problems=0

# 1. Internet reachability -------------------------------------------------
if /sbin/ping -c 1 -t 5 1.1.1.1 >/dev/null 2>&1; then
  net=ok
else
  net=DOWN
  problems=$((problems + 1))
fi

# 2. Tailscale (the path the phone and I use to reach this box) -------------
if [ -x "$TS" ]; then
  if "$TS" status >/dev/null 2>&1; then
    ts=ok
  else
    ts=DOWN
    problems=$((problems + 1))
    "$TS" up >/dev/null 2>&1 && ts=recovered
  fi
else
  ts=absent
fi

# 3. Codex remote-control for both ChatGPT accounts -------------------------
codex_status() {
  home="$1"
  out=$(CODEX_HOME="$home" $TIMEOUT ${TIMEOUT:+90} "$CODEX" remote-control start --json 2>&1)
  st=$(printf '%s' "$out" | "$PY" "$STATUS_PY" 2>/dev/null)
  # Only the "unmanaged app-server" case justifies killing a live daemon.
  if printf '%s' "$out" | grep -q 'not managed by codex app-server daemon'; then
    for p in $(pgrep -f 'app-server'); do
      if ps eww -p "$p" 2>/dev/null | tr ' ' '\n' | grep -q "CODEX_HOME=$home"; then
        kill -9 "$p" 2>/dev/null
      fi
    done
    rm -f "$home/app-server-daemon/app-server.pid" 2>/dev/null
    sleep 3
    out=$(CODEX_HOME="$home" $TIMEOUT ${TIMEOUT:+90} "$CODEX" remote-control start --json 2>&1)
    st=$(printf '%s' "$out" | "$PY" "$STATUS_PY" 2>/dev/null)
  fi
  echo "${st:-empty}"
}

c1=$(codex_status /Users/anicca/.codex)
c2=$(codex_status /Users/anicca/.codex-acct2)
[ "$c1" = "connected" ] || problems=$((problems + 1))
[ "$c2" = "connected" ] || problems=$((problems + 1))

# 4. Claude Remote Control --------------------------------------------------
cpid=$(launchctl list 2>/dev/null | awk '/com.anicca.claude-remote-control/{print $1}')
if [ -n "$cpid" ] && [ "$cpid" != "-" ]; then
  # 2026-08-01: launchd のジョブは supervisor スクリプト (zsh) になった。ソケットを
  # 持つのはその子の `claude remote-control` なので、ジョブ PID だけを lsof すると
  # 常に 0 本と出て毎分 kickstart -k を撃つ (実測: wrapper 0 / child 1)。子も数える。
  rcpid=$(pgrep -f 'claude remote-control' 2>/dev/null | head -1)
  conns=$(lsof -nP -p "${cpid}${rcpid:+,$rcpid}" 2>/dev/null | grep -c ESTABLISHED)
  if [ "$conns" -ge 1 ]; then
    claude=ok
  else
    claude=no_conn
    problems=$((problems + 1))
    launchctl kickstart -k gui/501/com.anicca.claude-remote-control >/dev/null 2>&1
  fi
elif [ -n "$cpid" ]; then
  # ラベルは読み込まれているが PID が "-" = ThrottleInterval(60秒) の待ち中。
  # 起動途中を DOWN と呼んで bootstrap を撃つと、正常な再起動と競合する。
  claude=restarting
else
  claude=DOWN
  problems=$((problems + 1))
  # 401 サーキットブレーカが自分を bootout した場合もここに来る。その時は
  # 人間が `claude auth login` するまで直らないので、復帰させるだけ無駄撃ちになる。
  # sentinel があるなら手を出さない (通知は supervisor 側が既に送っている)。
  if [ -f "$HOME/.claude/state/remote-control-401.sentinel" ]; then
    claude=DOWN_401_needs_login
  else
    launchctl bootstrap gui/501 \
      /Users/anicca/Library/LaunchAgents/com.anicca.claude-remote-control.plist >/dev/null 2>&1
  fi
fi

# 5. Free disk ------------------------------------------------------------
# A full disk stops every loop just as dead as a blackout does, and it is the
# more likely of the two: on 2026-08-01 this machine was found at 3GB free.
free_gb=$(df -g / 2>/dev/null | awk 'NR==2{print $4}')
disk="${free_gb}GB"
if [ -n "$free_gb" ] && [ "$free_gb" -lt 5 ]; then
  disk="${free_gb}GB LOW"
  problems=$((problems + 1))
  # Reclaim only regenerable bytes; never touch state, profiles or repos.
  rm -rf /Users/anicca/Library/Caches/* 2>/dev/null
  rm -rf /Users/anicca/.cache/* 2>/dev/null
  rm -rf /Users/anicca/Library/Logs/* 2>/dev/null
  after_gb=$(df -g / 2>/dev/null | awk 'NR==2{print $4}')
  disk="${free_gb}GB->${after_gb}GB LOW"
  # Below 2GB the machine is close to unusable -- tell Dais, this needs a human decision.
  if [ -n "$after_gb" ] && [ "$after_gb" -lt 2 ]; then
    tg=$(grep -m1 '^export TELEGRAM_BOT_TOKEN=' /Users/anicca/.openclaw/.env 2>/dev/null | cut -d= -f2- | tr -d '"')
    [ -n "$tg" ] && curl -s -X POST "https://api.telegram.org/bot${tg}/sendMessage" \
      -d chat_id=8547730585 \
      --data-urlencode "text=⚠️ Mac mini のディスク残量が ${after_gb}GB です。自動回収では足りません。" \
      >/dev/null 2>&1
  fi
fi

say "net=$net ts=$ts codex1=$c1 codex2=$c2 claude=$claude disk=$disk problems=$problems"

# Rotate: keep the log bounded so a wedged loop cannot fill the disk.
if [ "$(wc -l < "$LOG" 2>/dev/null || echo 0)" -gt 5000 ]; then
  tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
