#!/usr/bin/env bash
# phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh — discover inbound/outbound targets and send {{profile.lateness.stakeholders.channel}} instead of calling
# Usage: phase2-discover-and-{{profile.lateness.stakeholders.channel}}.sh <domain> <subject>
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
SKILL=~/.openclaw/skills/anicca-outbound-recruit
MAIL_SKILL=~/.openclaw/skills/anicca-mail-auto-reply
DOMAIN="${1:?domain required}"
SUBJECT="${2:-recruit}"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN_DIR="$SKILL/data/{{profile.lateness.stakeholders.channel}}-runs/$NOW"
OUTBOX="$RUN_DIR/outbox.json"
mkdir -p "$RUN_DIR"

python3 - "$DOMAIN" "$OUTBOX" <<'PY'
import json, sys

domain=sys.argv[1]
outbox=sys.argv[2]

rows={
  "tomb": [{
    "to":"{{profile.contact.personalEmail}}",
    "subject":"[TODO outbound {{profile.lateness.stakeholders.channel}}] tomb temple recruit",
    "body":"信濃町 / 都内の寺院5件に、AI墓建立と供養スペース利用可否についてメール送信する。電話ではなくメールで進める。候補の寺院名・問い合わせ先・送信文面を調査して送ること。"
  }],
  "comedy": [{
    "to":"{{profile.contact.personalEmail}}",
    "subject":"[TODO outbound {{profile.lateness.stakeholders.channel}}] comedy open mic recruit",
    "body":"中野 / 新宿周辺の open mic 主催者5件に、Dais の5分ピン芸出演枠についてメール送信する。電話ではなくメールで進める。候補名・問い合わせ先・送信文面を調査して送ること。"
  }],
  "cafe": [{
    "to":"{{profile.contact.personalEmail}}",
    "subject":"[TODO outbound {{profile.lateness.stakeholders.channel}}] cafe property recruit",
    "body":"kashispace / 賃貸 / 飲食物件の候補5件に、ghost kitchen用スペースの条件確認メールを送る。電話ではなくメールで進める。候補名・問い合わせ先・送信文面を調査して送ること。"
  }],
  "retreat-volunteers": [{
    "to":"{{profile.contact.personalEmail}}",
    "subject":"[TODO outbound {{profile.lateness.stakeholders.channel}}] retreat volunteer recruit",
    "body":"Vipassana retreat の server volunteer 候補5名に、日程と参加可否確認メールを送る。電話ではなくメールで進める。候補名・連絡先・送信文面を調査して送ること。"
  }],
}
json.dump(rows[domain], open(outbox,'w'), ensure_ascii=False, indent=2)
print(outbox)
PY

python3 - "$OUTBOX" "$SUBJECT" <<'PY'
import json, os, subprocess, sys
outbox, subject = sys.argv[1:3]
account=os.environ.get('GMAIL_ACCOUNT','{{profile.contact.personalEmail}}')
rows=json.load(open(outbox))
sent=0
for row in rows:
    p=subprocess.run([
        '/opt/homebrew/bin/gog','-a',account,'gmail','send',
        '--to',row['to'],'--subject',row['subject'],'--body',row['body'],'--json'
    ], capture_output=True, text=True)
    if p.returncode==0:
        sent+=1
print(f'✅ outbound {{profile.lateness.stakeholders.channel}} seed sent: subject={subject} sent={sent} outbox={outbox}')
PY