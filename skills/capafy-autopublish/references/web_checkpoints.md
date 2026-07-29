# camofox Web Checkpoints (CP1-3) — 手順

token=config.json::access_token / camofox :9377 / Capafyは Google login cookie 永続。ref は snapshot で都度取得(動く)。React制御は react_set.js、logo は logo_gen.js を /evaluate で注入。

## CP1 (page=edit) Agent Card
1. Pricing tab: mode(Run on Capafy=subscription / Download)。subscriptionなら period/price/cap/Free Trial/LLM Model(Claude Sonnet 4.6)/provider=Anthropic/DPA✓/第三者未チェック。Downloadなら oneTimeFee + DPA✓
2. Basic Info: title(≤50)/short/details/**logo(logo_gen.js)**/category/support email=contact@aniccaai.com
3. **★Workspace Documents "Deselect All" 必須★**(CLAUDE.md等の同梱=リーク防止)
4. "Confirm Submit" → "Agent Card Saved"

## configure後 leak gate
publish_chain.sh configure --deep-scan → `leak_scan.sh <staging>` (fail-closed)。staging = `$LIFE_MANAGER_REPO/skills/capafy-publisher/.temp/staging`

## CP2 (page=credential・subscription時のみ・Downloadはskip)
LLM Config に Anthropic API key host(proxy-hosted)。settings由来の不要 generic config は "Unselect this key from hosting"。"Confirm & Save Keys"

## CP3 (page=review)
"Submit for Review" → モーダル "Confirm Submit" → `publish_chain.sh status` で status=1(審査中)/4(listed) 確認（status0/audit0=draft=未提出。嘘禁止）
