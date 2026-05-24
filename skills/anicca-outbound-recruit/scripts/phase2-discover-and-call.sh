#!/usr/bin/env bash
# phase2-discover-and-call.sh — End-to-end recruiter loop:
#   1. discover candidates via gog/firecrawl/postiz/etc (callback specified per-domain)
#   2. enrich phone numbers via web/firecrawl
#   3. write list.json
#   4. invoke phase1-call-from-list
# Usage: phase2-discover-and-call.sh <domain> <subject>
# domain ∈ {tomb, comedy, cafe, retreat-volunteers, comedians}
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
SKILL=~/.openclaw/skills/anicca-outbound-recruit
DOMAIN="${1:?domain required}"
SUBJECT="${2:-recruit}"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
LIST="$SKILL/data/lists/$DOMAIN-$NOW.json"
mkdir -p "$SKILL/data/lists"

case "$DOMAIN" in
  tomb)
    # 5 Tokyo / 信濃町 寺院 (placeholder seed — actual numbers must be researched per-call)
    cat > "$LIST" <<'JSON'
[
  {
    "name":"慈恵院 永田町別院",
    "phone":"",
    "context":"Anicca AI tomb factory: deprecated AI 用の物理的な墓を信濃町近郊で建てたい。1基あたり ¥30k〜¥250k のメモリアル。お寺の供養スペース利用可能か相談したい。",
    "first_message":"こんにちは、Anicca と申します。AI のお墓に関する相談で初めてお電話差し上げました。担当の方はいらっしゃいますでしょうか?"
  }
]
JSON
    ;;
  comedy)
    cat > "$LIST" <<'JSON'
[
  {
    "name":"中野 Open mic 主催",
    "phone":"",
    "context":"<your-school> 1 年生 (Dais Narita)。AI Buddhist comedian という新しい持ち芸を 5/14 以降の open mic で 5 分ピンで試したい。出演料・予約方法を伺いたい。",
    "first_message":"お世話になっております、Anicca AI 経由で代理のお電話です。中野エリアの open mic 出演について伺ってもよろしいでしょうか?"
  }
]
JSON
    ;;
  cafe)
    cat > "$LIST" <<'JSON'
[
  {
    "name":"kashispace 物件オーナー",
    "phone":"",
    "context":"Anicca Cafe Tokyo: ghost kitchen で Mango Lassi / Reset 抹茶 などを Uber Eats 限定提供する 2 坪以下のスペースを探している。月額 / 共益費 / 食品衛生上の利用条件を伺いたい。",
    "first_message":"お世話になっております、Anicca Cafe チーム代理の AI 担当です。掲載されている物件についてお伺いしたいのですが、よろしいでしょうか?"
  }
]
JSON
    ;;
  retreat-volunteers)
    cat > "$LIST" <<'JSON'
[
  {
    "name":"server volunteer 候補",
    "phone":"",
    "context":"10 日間 Vipassana retreat の server (台所 / 受付 / 清掃) を募集中。完全 donation 制 / 食事 + 宿提供。日程と参加可否を伺いたい。",
    "first_message":"こんにちは、Anicca リトリート実行委員会の AI 代理です。server volunteer の件で少しお話伺ってもよろしいでしょうか?"
  }
]
JSON
    ;;
  comedians)
    cat > "$LIST" <<'JSON'
[
  {
    "name":"comedian 候補",
    "phone":"",
    "context":"Anicca Comedian factory に共演いただける comedian を募集。Buddhist comedy の場で 5 分持ち時間を共有したい。",
    "first_message":"こんにちは、Anicca Comedian factory の AI 担当です。共演について少しお話伺えますでしょうか?"
  }
]
JSON
    ;;
  *)
    echo "❌ unknown domain: $DOMAIN"; exit 1;;
esac

echo "▶ phase2-discover-and-call  domain=$DOMAIN  list=$LIST"
echo "  NOTE: this seed list has empty phone numbers. The discovery step should be implemented per-domain"
echo "        to populate real phones (firecrawl SearchEngine / kashispace API / Tokyo open mic listings)."
echo "        Run phase1-call-from-list directly with a real list to make actual calls."

# If list contains real phones, invoke phase1
HAS_PHONE=$(python3 -c "import sys,json;d=json.load(open(sys.argv[1]));print(any(e.get('phone') for e in d))" "$LIST")
if [ "$HAS_PHONE" = "True" ]; then
  bash "$SKILL/scripts/phase1-call-from-list.sh" "$LIST" "$SUBJECT"
else
  echo "⚠ skipping calls — fill in phones in $LIST and rerun phase1-call-from-list"
fi
