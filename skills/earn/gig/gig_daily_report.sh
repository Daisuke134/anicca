#!/usr/bin/env bash
# gig_daily_report.sh — daily gig loop digest to the configured Telegram chat, same channel as
# OpenClaw reports. Reads the gig ledgers (honest ¥, no fake) and sends via `openclaw message send`.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
set -uo pipefail
set -a; . "$HOME/.local/state/life-manager/.env" 2>/dev/null; set +a
CHAT="${GIG_REPORT_CHAT:-${TELEGRAM_ALERT_CHAT_ID:?GIG_REPORT_CHAT or TELEGRAM_ALERT_CHAT_ID is required}}"
MSG=$(python3 - <<'PY'
import json,os,datetime
G=os.path.expanduser("~/gig")
def rows(f):
    p=os.path.join(G,f);o=[]
    if os.path.exists(p):
        for l in open(p):
            l=l.strip()
            if l:
                try:o.append(json.loads(l))
                except:pass
    return o
ap=rows("applied.jsonl"); applied=[r for r in ap if r.get("status")=="applied"]
rep=[r for r in ap if r.get("status") in ("replied","評価依頼","delivered")]
pub=[r for r in rows("shuppin.jsonl") if r.get("action")=="shuppin_published"]
S={"検収","支払","検収完了","completed","paid"}
earn=[r for r in rows("earnings.jsonl") if r.get("status") in S and r.get("evidence")]
jpy=sum(float(str(r.get('jpy',0)).replace(',','') or 0) for r in earn)
today=datetime.date.today().isoformat()
msg=f"""🧰 gig日報 (Coconala/mtdc) {today}
応募累計:{len(applied)} / 返信・納品:{len(rep)} / 出品公開:{len(pub)}
売上(検収済):{len(earn)}件 ¥{jpy:.0f}
{'✅ 実¥あり' if jpy>0 else '(実¥まだ0=受注待ち・正直報告)'}"""
print(msg)
PY
)
openclaw message send --channel telegram --target "$CHAT" --message "$MSG" 2>&1 | grep -iE "Sent|Message ID|error" | head -3
