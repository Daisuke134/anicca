# IG 垢をスケールで回す best-practice（3研究 + live 実験、2026-07-17）

出典 = `crwl`/`gh` で実際に fetch した公式 docs + 実 repo コード（URL は各項に明記、捏造なし）。firecrawl は credit 切れ、WebSearch 不使用。

## 結論（First principles）: 我々が間違えてる3つ

### ★1. 垢ごとの安定 proxy を使ってない（全垢が1つの IP を共有）= 最大の死因
instagrapi 公式 Best Practices: **"For production automation, the safest baseline is one account per stable proxy/IP... The exact provider matters less than consistency, reputation, and whether your request pattern fits the account history."**（https://subzeroid.github.io/instagrapi/usage-guide/best-practices.html ）
BadPassword の真因 = パスワードでなく**ネットワーク identity**: **"Datacenter IPs, noisy VPN exits, abused residential pool addresses, and cheap shared proxies all show this behavior. The upstream UI may still say 'incorrect password'; the fix is not a new password, it is a cleaner, stable network identity."**（https://instagrapi.com/guides/errors/bad-password/ ）
→ aiclipsvault の BadPassword も、複数垢が1 IP を共有してる事が原因の可能性大。**proxy-per-account が #1 の未実装レバー。**

### ★2. fresh 垢に warmup 無しで day-1 投稿している = 即 challenge を招く
研究 consensus: **"Accounts under a month old are flagged hard. Anything that even resembles automation on a fresh account triggers a challenge or worse."** / **"New, restored, or previously challenged accounts should not immediately run high-volume actions... Start with read-heavy authenticated actions before write-heavy actions... Increase volume slowly over days, not minutes."**（instagrapi Best Practices + https://instagrapi.com/guides/instagrapi-2fa-challenge/ ）
→ Dais の「1日目で投稿できないのはおかしい」への答え = **公式ソース的には、automation の fresh 垢は day-1 投稿すると challenge される。day-1 投稿こそが我々の繰り返してるミス。** warmup（read-heavy を数日→徐々に write）が必須。

### 3. relogin/session churn（← #12 で解決済、最大レバーは適用済）
**"Persisting the session pins the device fingerprint and cookie jar across runs, so Instagram's risk model sees the same client returning. In practice this single change eliminates roughly nine out of ten challenges."** / **"repeated fresh login() calls are themselves a risk signal."**（instagrapi Best Practices）
→ #12（golden session 再利用・relogin 廃止・device uuids 固定 via `set_uuids`）はこの 9/10 を潰すレバー。**方向性は完全に正しかった。**

## live 実験の裏付け（2026-07-17）
- aiclips_daily_hq を fresh 作成（共有 IP、day-1 post 試行）→ **作成直後に poisoned（bloks）、golden session すら残らず**。研究予測通り。proxy 無し + warmup 無しの fresh 垢は即死する。
- aiclipsvault: 24h 内に2回 login（bloks→BadPassword）→ 7日 freeze パターン該当。恒久放棄。
- world_hq2: golden session 死亡（churn 前に作成）。

## 正しい recipe（durable、スケール対応）
1. **垢ごとにユニークで安定した proxy**（mobile/residential、reputable、共有・datacenter・aggressive rotate 禁止）。provider より consistency が効く。
2. **session 永続 + device UUID 固定**（#12 ✓ 実装済）。
3. **warmup**: 作成後、数日 read-heavy（scroll/like）→ 徐々に write。fresh 垢 = 即投稿しない。
4. **PVA（電話認証）は任意だが、使うなら有料 reputable pool**（5sim/SMS-Activate、$0.014〜/番号）。**無料 throwaway 番号は IG が範囲ごと blacklist、即拒否**。instagrapi の `signup()` 自体は experimental で modern IG に SignupSpamError で弾かれがち → browser signup の方がまだ通る。
5. bloks/checkpoint の**自動突破ツールは存在しない**（`gh search` 0件、instagrapi 公式も manual confirmation のみ）。食らったら垢死＝予防（proxy+session+warmup）が唯一の道、新垢置換。

## ツールスタック（gh で実在確認）
- **subzeroid/instagrapi**（6,484★、pushed 2026-07-16 = 現役）— 投稿の本体。継続維持。
- **CloakHQ/CloakBrowser-Manager**（801★、現役）— 使用中の antidetect。
- **gologinapp/pygologin + gologin REST**（現役）— antidetect browser の選択肢。
- **akwin1234/damru**（239★、pushed 2026-07-05）— Docker 内実 Android を CDP 駆動、device 級 spoof。将来 device 信頼度が要る時の候補。
- **HikerAPI**（hikerapi.com、有料 SaaS）— session/device/proxy/challenge 維持を丸ごと外注。自前運用がキツければ選択肢。OSS repo は無い。
- 却下: 「instagram farm/account manager」系 repo の大半は 0-3★・2017-2023 放置の死んだ toy。

## Graph API の verdict = reel farm には使わない
公式（developers.facebook.com Content Publishing、2026-06-30 更新）: Business/Creator 垢 + FB Page linked + PPA + app review（`instagram_business_content_publish`）が必須。media は**公開 URL 必須（binary upload 不可、IG が curl する）**。rate = 50〜100件/24h/垢（公式2ページで数値が食い違い）。加えて **reel scheduling 不可・post 削除 不可・story sticker 不可**（複数 repo コメントで確認: francis-pang/ai-social-media-helper, etblues449/Faceless-Finance, gitroomhq/postiz-docs）。
→ 垢ごとに Business 化 + FB Page + app review の重い onboarding は fleet に不向き。Dais が踏んだ「FB Page 自動作成不可・browser login 失敗」の壁はこの重さの表れ。**instagrapi private API を継続、Graph API は使わない。**

## account registry data model（fleet dashboard 用、実 schema から）
出典: FayceMOTIV/instafarm `backend/models.py` + `anti_ban.py`、kang-van-gent/GainLike `schema.json`。
```
IgAccount:
  handle, email, proxy_id(FK→Proxy), device_id, user_agent, session_data(path/cookiePath),
  status: New|Warming|Ready|Active|Busy|Checkpoint|Banned|Retired,
  strength: Weak|Mid|Strong,
  warmup_day, warmup_started_at, last_login, last_action, last_post,
  posts_today/follows_today/likes_today + quota_reset_at,
  health: HEALTHY|WARNING|SHADOWBANNED|ACTION_BLOCKED|BANNED|UNKNOWN,
  total_bans, last_ban_at, role: active|standby|resting|banned
Proxy: id, endpoint, type(mobile/residential/isp), assigned_to(account), reputation, last_ok
```
→ 今の flat な `~/.cloak/clip-accounts.json` をこの schema に拡張 = 100s 垢の realtime dashboard（#7）の土台。

## 次の一手（roadmap、優先順）
1. **proxy-per-account を配線**（#1 レバー。1垢=1安定 proxy。provider 選定 = 少額コスト、これが無いと何垢作っても即死を繰り返す）。
2. **warmup フェーズを loop に組込む**（新垢は Warming→数日 read-heavy→Ready→post。day-1 投稿を廃止）。
3. **account registry を上記 schema に拡張** → fleet dashboard（#7）。
4. #12 golden session（✓済）は維持。
5. 1〜3 が入って初めて「fresh 垢が確実に投稿でき、100s に scale する」。それまでは fresh 垢を量産しても poisoned を繰り返すだけ。
