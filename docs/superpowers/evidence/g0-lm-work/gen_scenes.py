#!/usr/bin/env python3
"""LM reel scene generator: 6x 1080x1920 PNG mock UI frames (calendar/maps pain -> Anicca fix -> CTA)."""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1080, 1920
OUT = os.path.dirname(os.path.abspath(__file__))

FONT_BOLD = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
FONT_MED  = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_REG  = "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"

def font(path, size):
    return ImageFont.truetype(path, size)

def rrect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def center_text(draw, cx, y, text, f, fill, max_width=920, line_h=None):
    """Wrap text to max_width (rough char-based for CJK) and draw centered, return bottom y."""
    # crude CJK wrap: measure per-char
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        w = draw.textlength(test, font=f)
        if w > max_width and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    lh = line_h or int(f.size * 1.5)
    yy = y
    for ln in lines:
        w = draw.textlength(ln, font=f)
        draw.text((cx - w / 2, yy), ln, font=f, fill=fill)
        yy += lh
    return yy

def status_bar(draw, dark=False):
    c = (20, 20, 26) if not dark else (240, 240, 245)
    draw.text((60, 70), "9:41", font=font(FONT_MED, 34), fill=c)

def base_canvas(bg=(247, 247, 250)):
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img)

BRAND = (91, 79, 235)      # Anicca purple-blue
RED   = (220, 60, 60)
GREEN = (52, 168, 83)
MAPS_GREEN = (33, 140, 116)

# ---------- Scene 1: calendar add (hook) ----------
img, d = base_canvas()
status_bar(d)
center_text(d, W/2, 150, "予定を入れるたびに、グーグルマップを開いていませんか", font(FONT_BOLD, 62), (25, 25, 35), max_width=880, line_h=88)
# calendar card
rrect(d, (90, 560, 990, 900), 40, fill=(255,255,255), outline=(225,225,232), width=2)
d.text((140, 610), "7月13日(月)", font=font(FONT_MED, 40), fill=(120,120,130))
rrect(d, (140, 690, 940, 840), 24, fill=(238,236,255), outline=BRAND, width=3)
d.text((175, 715), "16:00  クライアント打ち合わせ", font=font(FONT_MED, 38), fill=(40,40,60))
d.text((175, 770), "渋谷オフィス", font=font(FONT_REG, 32), fill=(100,100,115))
# tap ripple hint
d.ellipse((900, 660, 960, 720), outline=BRAND, width=4)
img.save(f"{OUT}/scene1_calendar_add.png")

# ---------- Scene 2: maps search (pain) ----------
img, d = base_canvas(bg=(232, 244, 238))
status_bar(d)
rrect(d, (0, 260, W, 1180), 0, fill=(214, 233, 224))
# fake route line
d.line([(150, 1150), (350, 900), (300, 700), (620, 560), (900, 420)], fill=MAPS_GREEN, width=14, joint="curve")
d.ellipse((130,1130,170,1170), fill=RED)
d.ellipse((880,400,920,440), fill=MAPS_GREEN)
d.text((110, 320), "渋谷オフィスへの経路", font=font(FONT_MED, 40), fill=(30,60,50))
# result card
rrect(d, (90, 1230, 990, 1470), 40, fill=(255,255,255), outline=(220,230,225), width=2)
d.text((140, 1270), "経路 1", font=font(FONT_REG, 32), fill=(120,120,130))
d.text((140, 1320), "所要時間", font=font(FONT_MED, 36), fill=(60,60,70))
d.text((140, 1375), "45分", font=font(FONT_BOLD, 96), fill=MAPS_GREEN)
d.text((520, 1400), "電車 + 徒歩", font=font(FONT_REG, 34), fill=(110,110,120))
center_text(d, W/2, 1560, "グーグルマップを開いていませんか", font(FONT_BOLD, 54), (25,60,45), max_width=880, line_h=76)
img.save(f"{OUT}/scene2_maps_search.png")

# ---------- Scene 3: calendar manual entry (pain) ----------
img, d = base_canvas()
status_bar(d)
center_text(d, W/2, 160, "カレンダーに戻り、出発時刻を手入力する", font(FONT_BOLD, 58), (25,25,35), max_width=880, line_h=82)
rrect(d, (90, 520, 990, 980), 40, fill=(255,255,255), outline=(225,225,232), width=2)
d.text((140, 570), "7月13日(月)", font=font(FONT_MED, 40), fill=(120,120,130))
rrect(d, (140, 650, 940, 790), 24, fill=(238,236,255), outline=BRAND, width=3)
d.text((175, 675), "16:00  クライアント打ち合わせ", font=font(FONT_MED, 36), fill=(40,40,60))
# manual entry row with blinking cursor look
rrect(d, (140, 830, 940, 930), 24, fill=(255,247,235), outline=(230,180,90), width=3)
d.text((175, 855), "出発  15:", font=font(FONT_MED, 40), fill=(90,70,20))
d.line([(430, 858), (430, 908)], fill=(90,70,20), width=4)  # cursor
d.text((175, 900), "…えっと、15時何分だっけ", font=font(FONT_REG, 28), fill=(150,120,60))
img.save(f"{OUT}/scene3_manual_entry.png")

# ---------- Scene 4: conflict warning (pain climax) ----------
img, d = base_canvas(bg=(255, 244, 244))
status_bar(d)
center_text(d, W/2, 160, "気づけば、次の予定と被っていて青ざめる", font(FONT_BOLD, 60), (30,20,20), max_width=880, line_h=86)
rrect(d, (90, 620, 990, 1020), 40, fill=(255,255,255), outline=RED, width=4)
rrect(d, (140, 660, 940, 780), 24, fill=(255,235,235), outline=RED, width=3)
d.text((175, 685), "15:15  出発 (未定)", font=font(FONT_MED, 36), fill=(150,30,30))
rrect(d, (140, 800, 940, 960), 24, fill=(255,235,235), outline=RED, width=3)
d.text((175, 825), "15:30  次のオンライン会議", font=font(FONT_MED, 36), fill=(150,30,30))
d.text((175, 880), "⚠ 移動時間が確保できません", font=font(FONT_MED, 34), fill=RED)
img.save(f"{OUT}/scene4_conflict.png")

# ---------- Scene 5: Anicca auto-fix (solution) ----------
img, d = base_canvas(bg=(245, 244, 255))
status_bar(d)
center_text(d, W/2, 130, "アニッカは予定を入れた瞬間に、移動時間を自動で計算し、出発のブロックまで登録します", font(FONT_BOLD, 50), (30,25,60), max_width=900, line_h=72)
rrect(d, (90, 560, 990, 1080), 40, fill=(255,255,255), outline=(225,225,232), width=2)
d.text((140, 600), "7月13日(月)", font=font(FONT_MED, 40), fill=(120,120,130))
# auto-added departure block (brand color, "auto" badge)
rrect(d, (140, 680, 940, 800), 24, fill=(238,236,255), outline=BRAND, width=3)
d.text((175, 700), "15:15  出発 → 渋谷", font=font(FONT_MED, 36), fill=(60,50,140))
rrect(d, (760, 705, 900, 750), 14, fill=BRAND)
d.text((785, 712), "自動", font=font(FONT_MED, 26), fill=(255,255,255))
rrect(d, (140, 820, 940, 940), 24, fill=(255,255,255), outline=(225,225,232), width=3)
d.text((175, 845), "16:00  クライアント打ち合わせ", font=font(FONT_MED, 34), fill=(40,40,60))
rrect(d, (140, 960, 940, 1050), 24, fill=(255,255,255), outline=(225,225,232), width=3)
d.text((175, 985), "17:30  オンライン会議", font=font(FONT_MED, 34), fill=(40,40,60))
img.save(f"{OUT}/scene5_anicca_auto.png")

# ---------- Scene 6: CTA ----------
img = Image.new("RGB", (W, H), BRAND)
d = ImageDraw.Draw(img)
center_text(d, W/2, 780, "カレンダーは、任せるものへ", font(FONT_BOLD, 96), (255,255,255), max_width=920, line_h=136)
d.text((0,0),"",font=font(FONT_REG,10))
w = d.textlength("aniccaai.com/life-manager", font=font(FONT_MED, 44))
d.text((W/2 - w/2, 1120), "aniccaai.com/life-manager", font=font(FONT_MED, 44), fill=(255,255,255))
rrect(d, (W/2-220, 1220, W/2+220, 1310), 45, fill=(255,255,255))
w2 = d.textlength("Anicca を試す", font=font(FONT_MED, 40))
d.text((W/2-w2/2, 1250), "Anicca を試す", font=font(FONT_MED, 40), fill=BRAND)
img.save(f"{OUT}/scene6_cta.png")

print("6 scenes written to", OUT)
