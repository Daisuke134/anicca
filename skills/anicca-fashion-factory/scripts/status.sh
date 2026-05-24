#!/usr/bin/env bash
# Fashion skill status — quick health summary.
#
# Output: human-readable summary of products, recent orders, reviews, coupons.
# Used for ad-hoc inspection (not on a cron).

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-fashion-factory"
DATA="$SKILL_DIR/data"

PYTHON="python3"

echo "=== anicca-fashion-factory status ==="
echo "skill dir: $SKILL_DIR"
echo

echo "[products.json]"
if [ -f "$DATA/products.json" ]; then
  $PYTHON -c "
import json
d=json.load(open('$DATA/products.json'))
ps=d.get('products', d) if isinstance(d, dict) else d
items = ps if isinstance(ps, list) else list(ps.values()) if isinstance(ps, dict) else []
for v in items:
    slug=v.get('slug','?'); price=v.get('price_usd', v.get('price','?'))
    title=v.get('title', v.get('name',''))
    link=v.get('payment_link','?')
    print(f'  {slug:14s} {title}  \${price}  link={link}')
"
else
  echo "  (none)"
fi
echo

echo "[printful-products.json]"
if [ -f "$DATA/printful-products.json" ]; then
  $PYTHON -c "
import json
d=json.load(open('$DATA/printful-products.json'))
items = d if isinstance(d, list) else (d.get('products', list(d.values())) if isinstance(d, dict) else [])
for v in items:
    slug=v.get('slug','?'); spid=v.get('sync_product_id','?'); vid=v.get('variant_id','?')
    print(f'  {slug:14s} sync_product_id={spid} variant={vid}')
"
else
  echo "  (none)"
fi
echo

echo "[recent reviews]"
if [ -f "$DATA/reviews.json" ]; then
  $PYTHON -c "
import json
d=json.load(open('$DATA/reviews.json'))
runs=d.get('runs',[])[-3:]
for r in runs:
    pos=len(r.get('positive',[])); neu=len(r.get('neutral',[])); neg=len(r.get('negative',[]))
    print(f'  {r.get(\"ran_at\",\"?\")[:19]} {pos}+/{neu}=/{neg}-')
"
else
  echo "  (none)"
fi
echo

echo "[recent coupons issued]"
if [ -f "$DATA/coupons.json" ]; then
  $PYTHON -c "
import json
d=json.load(open('$DATA/coupons.json'))
cps=d.get('coupons',[])[-5:]
for c in cps:
    print(f'  {c.get(\"issued_at\",\"?\")[:19]} {c.get(\"promo_code\",\"?\"):14s} → {c.get(\"customer_{{profile.lateness.stakeholders.channel}}\",\"?\")}')
"
else
  echo "  (none)"
fi
echo

echo "[active crons]"
$PYTHON -c "
import json,pathlib
p=pathlib.Path.home()/'.openclaw'/'cron'/'jobs.json'
d=json.load(open(p))
js=d.get('jobs',d)
if not isinstance(js,list): js=list(js.values())
for j in js:
    n=j.get('name','')
    if 'fashion' in n.lower():
        sc=j.get('schedule',{})
        expr=sc.get('expr') if isinstance(sc,dict) else ''
        print(f'  {n:42s} {expr}')
"

echo
echo "✅ status: ok"
