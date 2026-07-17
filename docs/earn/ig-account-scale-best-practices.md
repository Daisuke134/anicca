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

### ★真に FREE な手段: 携帯テザリング + 機内モード切替（実在・裏取り済み）
**これが唯一の「本物の無料 clean IP」経路。** 仕組みと裏取り:
- **原理 = CGNAT**。christinataft/4g-proxy（`gh repo view christinataft/4g-proxy`、DIY 4G proxy 手順）: *"4G mobile proxies are proxies created from the connection to a mobile... Thanks to CGNAT, 4G mobile proxies are superior to every other type of proxy as it camouflages the bots... the public IPV4 address used by the 4G mobile proxy is simultaneously used by hundreds or real users which makes IP bans a lot more difficult... not all mobile carriers do use CGNAT, but the vast majority of them do."* — instagrapi 公式ガイドの "mobile IPs sit even higher in trust because carriers NAT thousands of users behind one address" と完全に一致（同じ物理原理）。
- **商用化されてる実在手法**: proxidize/proxidize-android（本家、legacy版を open source 化）は Android 端末そのものを 4G/5G プロキシ化するアプリで、README の目次に **"Rotation/Changing the IP (How to Change Mobile Proxy IP Address Using Airplane Mode)"** という専用セクションがある — 機内モードの ON/OFF でキャリアが新しい IP を割り当てる、という技術は業界で確立済み（proxidize は Play Store 配布実績のある商用プロダクトの前身）。同種の DIY 実装が複数 gh 上に実在: `DevilData/proxydewa`（"allows anyone to create a 5G or 4G mobile proxy using their phone"）、`christinataft/4g-proxy`（Raspberry Pi + USB dongle 版）。
- **やり方（Mac + Android 前提。iPhone は adb 相当が無く手動タップのみ）**: Android 端末を USB でテザリング（またはローカル HTTP/SOCKS プロキシアプリ経由）→ Mac の CloakBrowser / instagrapi の proxy 設定にその端末のテザリング接続を指す → IP を変えたい時は `adb shell settings put global airplane_mode_on 1` → 数秒待つ → `airplane_mode_on 0`（実装確認済み: `X-PLUG/MobileAgent` の `adb_utils.py` の `toggle_airplane_mode()` がまさにこの2コマンドを発行している）。
- **限界（分析、引用ではなく物理的制約からの推論）**: (a) 全キャリアが CGNAT かつ機内モード毎に新IPを払い出すわけではない（同一セルの同一IPに戻ることもある。christinataft のREADME も"not all carriers"と留保）— 効くかはキャリア依存で試行必須。(b) 母艦(Mac)がWi-Fi、テザリング端末が回線契約者=Dais自身の実SIMなら「本人の携帯番号に紐づくIP」であり、複数IG垢をそこに集中させると本人の携帯契約自体がキャリア側で"多垢自動化のハブ"として見える risk はゼロではない。(c) 物理デバイス1台なので**同時に使える垢は事実上1個**（scaleしない=100s垢には向かない、今の1垢フェーズには最適）。
- **結論: 今この瞬間、コスト$0で確実に「datacenterでない・IG最高信頼のmobile ASN」を手に入れる手段はこれ。** IPRoyalの$7より安く($0)、かつtype がmobileなので residentialより格上（instagrapi公式: "Mobile (4G/5G) IPs sit even higher in trust"）。

### 他の free/cheap 手段（個別 verdict、引用付き）
| 手段 | Verdict | 根拠 |
|---|---|---|
| **家庭ルーター再起動→ISP動的IP変更** | **条件付き USABLE**（residential ASNなので type は良い。ただし新IPが払い出されるかはISPのDHCPリース次第で保証なし、かつ既存のCloakBrowser回線と同一ISPなら「隣接IP」で同じ /24 の焼け具合を引き継ぐ可能性）。datacenter回避という意味では有効な$0オプションだが「clean」かは実測が要る。 |
| **無料枠クラウド(AWS/GCP free tier等)を egress に使う** | **USELESS**。instagrapi公式が名指し: *"A datacenter ASN — AWS, GCP, DigitalOcean, Hetzner — is flagged immediately because no real Instagram user logs in from one."*（`instagrapi.com/guides/errors/challenge-required/`） |
| **Tor** | **USELESS**。Tor Project 自身が「サービス側がTorを一括ブロックできるように」正式に **TorBulkExitList を配布**（`check.torproject.org/torbulkexitlist`、実測1,410 IP、5分足らずで最新版取得可能）。Tor公式ガイド（`support.torproject.org/abuse/ban-tor/`）: *"It's easy to build an up-to-date list of Tor IP addresses that allow connections to your service"* — Meta 級サービスが使わない理由がない。exit node は公開列挙可能な時点で、instagrapi が言う「noisy VPN exits」（BadPassword原因の一つ）と同じ扱いを受ける。 |
| **無料VPNのIPローテーション** | **USELESS（analysis）**。無料VPNのサーバー実体はほぼ全て AWS/DigitalOcean/OVH等の datacenter VPS（VPNサーバーである以上、構造的に datacenter ASN）。上記の datacenter即challenge citationがそのまま当てはまる。residential-VPN型（Hola等、他人の家庭回線を借りる方式）は理論上 residential ASN だが、abuse履歴が蓄積した共有プールである可能性が高く `proxy_address_is_blocked` ガイドの「2. 転売residentialプールのabuse履歴」パターンに該当しやすい。 |

### Bottom line（更新版）
**free proxy（proxifly等の公開リスト）は使うな — type が datacenter確定 + 実測20/20中18件が接続すら失敗。Tor・無料クラウドegress・無料VPNも同じ理由でUSELESS。** ただし**本当に$0で使える経路が1つだけある: 携帯テザリング＋機内モード切替（CGNAT mobile IP）**。今すぐ実行できる優先順:
1. **($0) Android端末があればテザリング+機内モード切替を試す** — 新IPが払い出されるか2〜3回切替て実測、確認できれば今すぐ使える。
2. **それが無理/端末が無い場合は IPRoyal residential 1GB=$7（買い切り）** を CloakBrowser に刺す。
どちらの経路でも、次に作る新規IG垢はその専用IPに固定し、他垢と共有しない・rotateしない。これで「共有IPが焼けている」変数を1個消してから、warmup（day-1投稿の廃止）を重ねるのが次点。

## Cold-account の切り分け: 休眠(復活可) vs bloks/ChallengeRequired(復活不可)

instagrapi 公式ソースで2種類の「死んでる」を明確に区別できる。

**① 休眠(inactivity)= login_required（復活可能）**: セッション cookie の自然失効。原因は3つ（`instagrapi.com/guides/errors/login-required/`）— (1) サーバー側の能動的失効（パスワード変更・全端末ログアウト・risk model判断=`signature_revoked`）、(2) 同一sessionの複数IP同時使用、(3) **経過時間による自然失効**: *"Cookies have a finite useful life. The hard cap is roughly 90 days, but practical lifetime is shorter — typically 7 to 30 days for an active session, less for an account with low engagement signals."* → **復活手順は `relogin()`（`login()`ではない）。device fingerprintを維持したままcookieだけ更新するため、challengeを再発火させにくい**: *"call `relogin()`, not `login()`. `login()` discards the device fingerprint and re-runs the bootstrap handshake, which often triggers challenge_required... `relogin()` reuses the existing fingerprint and only refreshes the cookie jar."*

**② bloks/ChallengeRequired = 汚染(poisoned、事実上復活不可)**: instagrapi の実装（`subzeroid/instagrapi` の `docs/usage-guide/challenge_resolver.md`、`gh search code "bloks" repo:subzeroid/instagrapi` で実在確認）に明記された一次ソース: *"Bloks redirect checkpoints such as `bloks_action=\"com.bloks.www.ig.challenge.redirect.async\"` or placeholder `step_name=\"STEP_NAME\"` require manual confirmation in the official Instagram app or web flow on a trusted device; instagrapi raises `ChallengeRequired` with the sanitized challenge context instead of treating this as a legacy step."* — つまり **bloks 系の challenge は API/自動化からは原理的に解けない設計**（instagrapiのコード自体が「これは自動処理せず手動確認が要る」と明示的に別扱いしている）。さらに `challenge_required` ガイドは劣化パスも明記: soft な `challenge_required`（SMS/EMAILコードで解ける）が悪化すると `checkpoint_required` に昇格し、*"checkpoint_required generally cannot be resolved by your worker and should page an operator instead."*

→ **我々の bloks を食らった垢（aiclipsvault、aiclips_daily_hq）は②に該当し、公式ソース的にも復活不可（instagrapi自体が「手動確認 in the official app on a trusted device」を要求する設計）。新垢への置換が唯一の道**（既存 spec の記述と一致、再確認済み）。**逆に「ただ最後のlogin/postから日数が空いて止まってる」だけの垢（bloks/checkpointを食らっていないもの）は①に該当し、`relogin()`で復活を試す価値がある** — 見分け方は `cl.last_response.json()['message']` が `challenge_required`/`checkpoint_required`/bloks系かどうかで判定できる。
