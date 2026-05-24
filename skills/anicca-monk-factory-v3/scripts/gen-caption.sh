#!/usr/bin/env bash
# Deterministically generate a UNIQUE caption per script (no runtime LLM — keeps the cron a pure pipeline).
# Each of the 30 bank scripts yields its own caption (rotation cycles 30 → 30 distinct captions before repeat).
# Usage: gen-caption.sh <ID> <out_tiktok.txt> <out_ig.txt>
set -euo pipefail
SKILL="$HOME/.openclaw/skills/anicca-monk-factory-v3"
BANK="$SKILL/04-script/bank_en.jsonl"
ID="$1"; OUT_TT="$2"; OUT_IG="$3"
python3 - "$BANK" "$ID" "$OUT_TT" "$OUT_IG" <<'PY'
import json,sys,re,hashlib
bank,ID,out_tt,out_ig=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
o=None
for line in open(bank):
    line=line.strip()
    if not line: continue
    j=json.loads(line)
    if j.get("id")==ID: o=j; break
if not o: sys.exit("script id not found: "+ID)
script=o.get("script",""); track=o.get("track","T1")
# hook = first 1-2 sentences, stripped of the self-intro
sents=re.split(r'(?<=[.!?])\s+', script)
hook=sents[0].strip()
if len(hook)<25 and len(sents)>1: hook=(hook+" "+sents[1]).strip()
hook=re.sub(r'\s+',' ',hook)[:150]
COMMON=["#monk","#buddhism","#ajahnsutta","#wisdom","#mindfulness"]
T1=["#sleep","#cantsleep","#insomnia","#tired","#fatigue","#recovery","#nervoussystem","#sleeptok","#wellness","#burnout","#restfulsleep","#calm"]
T2=["#overthinking","#anxiety","#stillness","#peace","#meditation","#letgo","#mentalhealth","#healing","#innerpeace","#quietmind","#stress","#presence"]
pool = T1 if track=="T1" else T2
# rotate selection by a stable hash of the ID so each script differs
h=int(hashlib.md5(ID.encode()).hexdigest(),16)
def pick(lst,n,seed):
    out=[]; i=seed%len(lst)
    while len(out)<n and len(out)<len(lst):
        c=lst[i%len(lst)]
        if c not in out: out.append(c)
        i+=1
    return out
tags=pick(pool,7,h)+pick(COMMON,3,h>>5)
tagline=" ".join(tags[:10])
tt=f"{hook} Comment STILL if this is you. \U0001f64f {tagline}"
ig=f"{hook} An old forest monk's reminder. Comment STILL if this is you. {tagline}"
open(out_tt,"w").write(tt+"\n")
open(out_ig,"w").write(ig+"\n")
print("TT:",tt[:90])
print("IG:",ig[:90])
PY
