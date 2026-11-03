"""Original, data-grounded article illustrations for Anicca Research.
No external artwork, private customer data or model output is embedded.
Run: python3 docs/research/manager/publication/artwork/render-editorial.py
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT=Path(__file__).parent/"generated"
OUT.mkdir(parents=True,exist_ok=True)
W,H=1600,900
INK="#18263A"; MUTE="#556575"; PAPER="#F6F7F7"; WHITE="#FFFFFF"
BLUE="#4967D9"; TEAL="#008B8B"; ORANGE="#D87837"; PALE="#E5EFF8"
try:
    F="/System/Library/Fonts/Supplemental/Arial.ttf"
    B="/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    ImageFont.truetype(B,36)
except OSError:
    F="/System/Library/Fonts/Arial.ttf"; B=F

def font(size,bold=False):
    return ImageFont.truetype(B if bold else F,size)

def text(draw,xy,s,size=28,color=INK,bold=False):
    draw.text(xy,s,font=font(size,bold),fill=color)

def pill(draw,box,label,fill=INK,foreground=WHITE):
    draw.rounded_rectangle(box,radius=22,fill=fill)
    text(draw,(box[0]+19,box[1]+10),label,20,foreground,True)

def base(kicker,headline,strap):
    im=Image.new("RGB",(W,H),PAPER); d=ImageDraw.Draw(im)
    d.rectangle([0,0,W,12],fill=BLUE)
    d.ellipse([76,71,93,88],fill=ORANGE)
    text(d,(107,60),kicker.upper(),24,MUTE,True)
    text(d,(76,120),headline,61,INK,True)
    text(d,(78,211),strap,30,MUTE)
    return im,d

def card(d,xy,size=2,color=WHITE):
    x,y,w,h=xy
    d.rounded_rectangle([x,y,x+w,y+h],radius=28,fill=color,outline="#D8E1EB",width=size)

# 1. Ampersand: two conversations, the distinction between a certain/uncertain fact.
im,d=base("Anicca Research / Humans&", "When should an AI speak up?", "A fictional Friday meeting, and a real two-turn API session.")
card(d,(74,315,698,413));card(d,(826,315,698,413))
pill(d,(100,340,330,389),"TURN 1 / FACT",BLUE)
text(d,(109,414),"Sam said:",26,MUTE)
text(d,(109,469),'"Friday is impossible."',35,INK,True)
d.rounded_rectangle([105,553,736,697],radius=17,fill="#E6F0FA")
text(d,(129,574),"Verified recommendation:",25,BLUE,True)
text(d,(129,614),"Flag the conflict.",31,INK,True)
text(d,(129,653),"Let the team choose.",28,INK)
pill(d,(851,340,1180,389),"TURN 2 / UPDATE",ORANGE)
text(d,(860,414),"Sam now says:",26,MUTE)
text(d,(860,469),'"Friday might work."',35,INK,True)
d.rounded_rectangle([856,553,1488,697],radius=17,fill="#FFF1E5")
text(d,(878,574),"What our records verify:",25,ORANGE,True)
text(d,(878,614),"A follow-up was received",28,INK,True)
text(d,(878,654),"in the same saved session.",27,INK)
text(d,(77,785),"2 completed turns",26,INK,True)
text(d,(390,785),"4 saved items",26,INK,True)
text(d,(650,785),"No real calendar action",26,INK,True)
text(d,(77,846),"The full follow-up wording was not independently scored.",21,MUTE)
im.save(OUT/"ampersand-editorial.png",optimize=True)

# 2. Jordan: real matched 24-person human mean shift vs flat local model.
im,d=base("Anicca Research / Artificial Societies", "48 simulated respondents. One answer.", "The model passed the format check and missed the human response shift.")
card(d,(70,305,1460,470))
candidates=[("Wording A",0.6458333333333334,1.0),("Wording B",0.7916666666666666,1.0)]
x0,x1=230,1250
for i,(label,human,model) in enumerate(candidates):
    y=405+i*158
    text(d,(113,y-18),label,30,INK,True)
    d.line([x0,y+45,x1,y+45],fill="#D5E2E7",width=7)
    for tick in [0,.25,.5,.75,1]:
        px=x0+int(tick*(x1-x0))
        d.line([px,y+33,px,y+60],fill="#B8CBD6",width=3)
    pxh=x0+round(human*(x1-x0)); pxm=x0+round(model*(x1-x0))
    d.ellipse([pxh-19,y+25,pxh+19,y+65],fill=TEAL)
    d.ellipse([pxm-19,y+25,pxm+19,y+65],fill=ORANGE)
    text(d,(pxh-34,y-11),f"{human:.3f}",23,TEAL,True)
    text(d,(pxm-42,y-11),"1.000",23,ORANGE,True)
text(d,(130,741),"HUMAN CHANGE +0.146",27,TEAL,True)
text(d,(730,741),"MODEL CHANGE 0.000",27,ORANGE,True)
d.ellipse([93,807,116,830],fill=TEAL); text(d,(130,799),"Human reference mean (24 people per wording)",22,MUTE)
d.ellipse([823,807,846,830],fill=ORANGE); text(d,(859,799),"Local Qwen model (24 prompts per wording)",22,MUTE)
im.save(OUT/"as-survey-editorial.png",optimize=True)

# 3. Data leakage: identical participants crossing train/test.
im,d=base("Anicca Research / Data Integrity","One test. Two ways to split 120 rows.","The unit you hold out determines what the score can tell you.")
card(d,(80,318,688,448));card(d,(835,318,688,448))
pill(d,(107,343,428,392),"RANDOM ROWS",ORANGE)
pill(d,(862,343,1221,392),"HOLD OUT PEOPLE",BLUE)
text(d,(120,415),"25 people on both sides",31,INK,True)
text(d,(875,415),"0 people on both sides",31,INK,True)
dots_left=[ORANGE]*25+[BLUE]*14+[TEAL]*1
dots_right=[BLUE]*30+[TEAL]*10
for col,arr in [(0,dots_left),(1,dots_right)]:
    xstart=125 if col==0 else 874
    for i,fill in enumerate(arr):
        x=xstart+(i%8)*67; y=505+(i//8)*49
        d.ellipse([x,y,x+25,y+25],fill=fill)
text(d,(126,738),"25 overlap / 14 train-only / 1 test-only",22,MUTE)
text(d,(873,738),"30 train / 10 completely new people",22,MUTE)
d.ellipse([110,818,130,838],fill=ORANGE)
text(d,(142,811),"Seen in both",21,MUTE)
d.ellipse([360,818,380,838],fill=BLUE)
text(d,(392,811),"Training only",21,MUTE)
d.ellipse([617,818,637,838],fill=TEAL)
text(d,(649,811),"Test only",21,MUTE)
text(d,(882,813),"Fictional 40 people, three answers each",20,MUTE)
im.save(OUT/"data-split-editorial.png",optimize=True)

print("RENDERED",[str(p)+":"+str(p.stat().st_size) for p in OUT.glob("*.png")])
