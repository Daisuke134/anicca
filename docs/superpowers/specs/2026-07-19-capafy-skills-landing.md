# Capafy Skills Landing

## Goal

Instagram bio の1本のクリック可能 URL から、公開中の全 Capafy skill へ移動できる landing を公開する。

`done="GET /agent/agents の agentStatus==online のみを mobile-first 単一HTMLへ生成し、公開URLがHTTP 200かつ capafy.ai/agent link数>0、日次loopが再生成・再deployしcommercial bio targetが公開URL、commit+push済み"`

## 不変条件

- `build_landing.py` は `select_listing.py` と同じ `CAPAFY_HTTP` で `GET /agent/agents` を呼び、`agentStatus == "online"` の listing だけを出力する。
- 出力は `skills/earn/capafy-marketing/site/index.html` 1ファイル。外部 CDN、JavaScript、画像、font 依存を持たない。
- page は mobile-first 1カラム。header は `Claude Skills Daily`、tagline は `Sharing Claude skills you can use, every day.`、各 card は name、2行以内に見える desc、`Use this skill →` link を持つ。
- card URL は `https://capafy.ai/agent/{agentId}?utm_source=instagram_bio&utm_medium=bio_link&utm_campaign=capafy_marketing` と完全一致する。
- light/dark、keyboard focus、reduced motion を扱う。生成順は name の case-insensitive 昇順で決定的にする。
- 毎回 `index.html` を上書きし、online 一覧が同じなら byte-identical にする。
- Netlify production URL は HTTP 200 を返し、HTML 内 `capafy.ai/agent` link数が1以上になる。
- `capafy-ig-marketing-daily.sh` は既存 STEP を保ち、各 pass で landing を再生成・production redeployする。`commercial_ok=yes` かつ live の STEP5 BIO target は個別 listing でなく landing URL にする。
- 新規 GitHub Actions workflow は作らない。

## Verification

| ID | 証拠 | PASS |
|---|---|---|
| V1 | unit test | offline 除外、escaping、UTM、件数、決定順、idempotence |
| V2 | live generator | 実 endpoint から card 数 > 0、online API 件数と一致 |
| V3 | browser | mobile viewport と desktop viewport で header/card/CTA/footer、light/dark、overflow を実表示 |
| V4 | Netlify | `curl` HTTP 200、`capafy.ai/agent` count > 0 |
| V5 | shell | `bash -n capafy-ig-marketing-daily.sh`、diff で regen/redeploy と STEP5 target を確認 |
| V6 | git | commit hash が remote branch に存在 |

## TODO

| Task | 状態 |
|---|---|
| generator + index.html | completed (21 online cards, idempotent MD5) |
| Netlify deploy | in_progress |
| daily regen + bio target | pending |
| browser/curl verify + commit/push | pending |
