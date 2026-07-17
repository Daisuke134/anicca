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

## Proxy verdict (free vs cheap, tested 2026-07-17)

**proxifly/free-proxy-list: USELESS for IG.** リポジトリ（`gh repo view proxifly/free-proxy-list`、6.2k★）は「every 5 min から web 上の公開 proxy を再スキャンして生死判定するだけの aggregator」（README: *"Every 5 minutes, Proxifly fetches fresh proxies—including HTTP, HTTPS, SOCKS4, and SOCKS5 proxies—from around the web."*）。実体を確認:
- **type = 全て datacenter/hosting、residential/mobile はゼロ**。サンプル3件の whois: `84.17.47.150`→`CDN77_AMS_DC1`（CDN77 のオランダDC）、`206.123.156.223`→`Secure Internet LLC`（米ホスティング業者）、`129.151.160.199`→`Oracle Corporation`（Oracle Cloud）。公開 proxy list は「誰かの datacenter サーバーに立てたプロキシソフトを世界中がスキャンして拾ってる」ものであり、residential/mobile が混ざる構造ではない。
- **anonymity 内訳（http protocol、605件中の JSON）**: `elite` 411件・`transparent` 194件・`anonymous` 0件。elite でも匿名性の話であって IP種別（DC/residential）とは無関係 — 411件全部が依然 datacenter。
- **live smoke test（`curl --proxy` / `curl --socks5-hostname`、8〜10s timeout、20サンプル = https 10件 + socks5 10件）**: **20件中 20件が実アクション不可**。https 10件 → httpbin.org/ip への到達 = `http_code=000`（接続拒否/即死）× 9、`400`（プロキシは繋がるが動かない）× 1。socks5 10件 → `000`×8、`503`×2。「5分ごとに検証済み」と README が謳っていても、fetch した瞬間には大半が死んでいる（無料 public proxy の宿命 = 世界中からの過負荷・即 IP 変更）。生きていた3件のうち1件を i.instagram.com / instagram.com へ直接叩いても `000`・`405`・`200`が混在し、200 が返った1件も IG のホームページを返しただけで、ログイン等アクションを試したわけではない（今回は口座を焼かないため未実施）。
- **結論: USELESS（理論でなく実測）**。type = datacenter確定 + 接続すら20/20中18件で失敗。仮に接続できても instagrapi 公式ガイドが明言する通り datacenter レンジは「pre-flagged、ログイン前から `challenge_required`」（下記引用）。

**datacenter proxy が IG で即死する一次ソース**（instagrapi 公式 `instagrapi.com/guides/instagrapi-proxy-setup/`、2026-04-30 更新）:
> "The two categories collapse to one rule: **datacenter IPs do not work for production Instagram automation, period.** A first login from a datacenter range typically hits `challenge_required` within seconds, sometimes before the password handshake completes."

同ガイドの価格軸（データ点として引用）:
> "Datacenter proxies sell for cents per GB; residential proxies sell for several dollars per GB; mobile proxies for tens of dollars per GB. The 10–100× spread is what you pay for IPs that are not pre-flagged."

`proxy_address_is_blocked` の一次ソース（`instagrapi.com/guides/errors/proxy-address-is-blocked/`）はさらに強い: datacenter は**range 単位で永久 pre-listing**（"The ban is not earned through misuse; it is the default state for those ranges."）— つまり無料 proxy を差しても account 側の問題ではなく IP レンジそのものが即拒否される。

### cheapest VIABLE paid path（実際に crwl した価格）
| Provider | Type | 最小購入 | 実質 $/GB |
|---|---|---|---|
| IPRoyal（`iproyal.com/pricing/residential-proxies/`） | Residential | **1GB = $7 一括**（月額commitなし、pay-as-you-go） | $7.00 → 10GBで$5.25 |
| IPRoyal（`iproyal.com/pricing/mobile-proxies/`） | Mobile (4G/5G, Vodafone/Three UK) | 24h test = $10.11/日、または30日 unlimited $130/月 | 50GBで$5.60/GB |
| SOAX（`soax.com/pricing`） | Residential/Mobile | Builder plan $200/月〜（100GB分） | $3.00/GB tier1（小規模には不向き＝月額commit前提） |

→ **IG 1垢だけなら IPRoyal residential の $7（1GB、買い切り、月額commitなし）が現実的な最安の入口。** 1アカウントの warmup+軽い投稿の月間トラフィックは数百MB〜1GB程度に収まる想定で、$7で足りる規模。mobile（$10台/GB〜）は信頼度がさらに高いが今は過剰投資。

### 1:1 は今 mandatory か
instagrapi 公式 FAQ（同ガイド）: *"Can I share one proxy across multiple accounts? Possible but risky. Instagram correlates accounts that share IPs and patterns; one bad apple can trigger holds on the others. Best practice: one residential IP per account, kept stable."* — 公式は「小規模なら共有可」という例外を明言してはいない。ただし**今は垢が1個なので 1:1 か否かは意味を持たない設問**（1垢=1proxyは自動的に満たされる）。本当に効くのは 1:1 そのものより「**residential/mobile であること」＋「同じIPをsession間で固定し続けること**」（同ガイド: *"Pin one IP per session and leave it alone... rotating per request is itself a fingerprint signal."*）。1:1 の厳格な必要性は数十〜数百垢にスケールした時（1IPに複数の"問題垢"が乗ると共倒れするリスク）に効いてくる話であり、今の1垢フェーズでは「datacenter を避けて安定した residential 1本を割り当てる」ことがすべて。

### 我々の CloakBrowser 共有IPは既に「焼けてる」可能性が高い（analysis、引用ではなく内部履歴からの推論）
このIPで直近 5+ 垢作成 + 複数回の failed login（aiclipsvault の bloks→BadPassword、aiclips_daily_hq の作成直後 poisoned、world_hq2 golden session 死亡）を積み上げている。`proxy_address_is_blocked` ガイドの「3の蓄積型」（*"an exit that started clean gradually accumulates listing weight over weeks... repeated rate-limit hits, accounts later flagged... login attempts that triggered checkpoints all stamp small amounts of risk"*）に完全に一致するパターン。**新しい clean な residential IP 1本が、次に作る垢を生かす一番の unlock である可能性が高い**（断定ではなく、良く一致する内部パターンからの推論）。

### Bottom line
**free proxy（proxifly等）は使うな — type が datacenter確定 + 実測20/20中18件が接続すら失敗、残りも実アクション未検証。** 今すぐ実行すべき最安の具体策 = **IPRoyal residential を 1GB=$7 で1本買い、CloakBrowser のプロキシ設定にそのIPを刺し、次に作る新規IG垢をそのIP専用に固定する**（他垢と共有しない、rotateしない）。これで「共有IPが焼けている」変数を1個消してから、warmup（day-1投稿の廃止）を重ねるのが次点。
