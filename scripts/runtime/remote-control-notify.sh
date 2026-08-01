#!/bin/zsh
# 401 サーキットブレーカが開いたことを Dais に知らせる。
#
# spec: ~/anicca-project/docs/superpowers/specs/2026-08-01-remote-control-robustness-design.md
# 呼び出し元: ~/.claude/scripts/remote-control-supervise.sh
#
# 通知経路は新設しない。停電通知 (~/recovery-setup/boot-notify.sh) と同じ
# Telegram bot を使う。Dais が見る場所を増やさないため。
#
# ここだけは human-in-the-loop が正当: 401 の解除には対話セッションでの
# `claude auth login` (Trusted Devices 下では生体認証つき) が要る。
# 機械では解けないので、黙って諦めるのではなく必ず人に届ける。

SENTINEL="${1:-$HOME/.claude/state/remote-control-401.sentinel}"

set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
TG="$TELEGRAM_BOT_TOKEN"
CHAT="${TELEGRAM_ALERT_CHAT_ID:-8547730585}"
[[ -z "$TG" ]] && { print -r -- "notify: TELEGRAM_BOT_TOKEN 未設定、送信を諦める"; exit 0 }

# ネット復帰待ち。通知が届かないくらいなら遅れて届いた方がまし。
for _ in $(seq 1 12); do
  /sbin/ping -c 1 -t 3 1.1.1.1 >/dev/null 2>&1 && break
  sleep 5
done

MSG="🔴 Mac mini の Remote Control が止まりました

電話から Mac mini につながらなくなります。
認証(401)が2回続いたので、無限リトライを避けて自分で停止しました。

$(cat "$SENTINEL" 2>/dev/null)

直し方: Mac mini の対話セッションで
  claude auth login
その後
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.anicca.claude-remote-control.plist"

HTTP=$(curl -s -o /dev/null -w '%{http_code}' -X POST "https://api.telegram.org/bot${TG}/sendMessage" \
  -d chat_id="$CHAT" --data-urlencode "text=$MSG")

print -r -- "notify: telegram http=$HTTP"
[[ "$HTTP" == "200" ]] || exit 1
