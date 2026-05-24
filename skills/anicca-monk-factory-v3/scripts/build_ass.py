import json, sys
src, out = sys.argv[1], sys.argv[2]
CHUNK = int(sys.argv[3]) if len(sys.argv)>3 else 2
LEAD  = float(sys.argv[4]) if len(sys.argv)>4 else 0.0  # shift earlier by LEAD sec
d = json.load(open(src))
words=[]
for seg in d.get('segments',[]):
    for w in seg.get('words',[]):
        t=w['word'].strip()
        if t: words.append({'w':t,'s':w['start'],'e':w['end']})
STOP=set("a an the and or but if of to in on at for is are was were be been i you he she it we they my your his her our their this that with do one no not".split())
def clean(w): return ''.join(c for c in w if c.isalnum() or c in "'-")
def at(t):
    t=max(0,t); h=int(t//3600); m=int((t%3600)//60); s=t%60
    return f"{h:d}:{m:02d}:{s:05.2f}"
W="&H00FFFFFF"; Y="&H0000FFFF"
lines=[]; i=0
while i<len(words):
    grp=words[i:i+CHUNK]; i+=CHUNK
    s=grp[0]['s']-LEAD; e=grp[-1]['e']-LEAD
    cand=[(len(clean(g['w'])),idx) for idx,g in enumerate(grp) if clean(g['w']).lower() not in STOP and len(clean(g['w']))>=3]
    kw=max(cand)[1] if cand else len(grp)-1
    parts=[(f"{{\\c{Y}}}{clean(g['w']).upper()}{{\\c{W}}}" if idx==kw else clean(g['w']).upper()) for idx,g in enumerate(grp)]
    lines.append(f"Dialogue: 0,{at(s)},{at(e)},Default,,0,0,0,,{' '.join(parts)}")
hdr=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,TikTok Sans Display Black,90,{W},{W},&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,3,1,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(out,'w').write(hdr+"\n".join(lines)+"\n")
print(f"{len(lines)} chunks (size {CHUNK}, lead {LEAD}s), {len(words)} words")
