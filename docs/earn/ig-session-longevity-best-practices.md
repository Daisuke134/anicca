# IG session を殺さず長期維持する — 一次情報ベースの best practice

最終更新: 2026-07-16 / 出典 = instagrapi 公式 + instagrapi.com ガイド + GitHub issues（crwl/gh のみ、WebSearch 不使用）

## なぜこの文書があるか（症状）

aiclipsvault の session が「login は通る（BadPassword ではない）が数分〜数時間で revoke」される。
2026-07-16 に3連続 revoke（04:07 web / 04:40 app / 04:45 app）。account 自体は生存（匿名 API 200）。

## 核心原因（最有力仮説）= web と app の concurrent session

**instagrapi 公式が名指しでアンチパターンと呼ぶ状況に一致**: CloakBrowser(Chromium=web sessionid) と
instagrapi(Android app 偽装 private session) を**同一アカウントに対して併用**すること。

出典: https://subzeroid.github.io/instagrapi/usage-guide/best-practices.html
> "mixing browser `sessionid` reuse with frequent private API password logins... treating a browser/web
> `sessionid` as equivalent to a stable private mobile session after Instagram returns `login_required`"

出典: https://instagrapi.com/guides/errors/login-required/ (logout_reason の値)
> `signature_revoked`, `password_changed`, `concurrent_session`
> "If you accidentally run the same session.json from two places at once... Instagram sees a single account
> hitting two IPs concurrently and treats it as session hijack. The token gets revoked in flight...
> what kills the cookie is the same cookie on two IPs."
> "Instagram also revokes sessions automatically when its risk model decides retroactively that the session
> looked suspicious — this is the `signature_revoked` case and it can fire hours after the original login."

## 我々のアーキテクチャへの含意（★要設計判断★）

現状: keepalive は **web(CloakBrowser :9223)** で instagram.com を開く / poster は **app(instagrapi)** で
sessionid を使う。= 同一 aiclipsvault に web と app の2経路。これが concurrent_session revoke の温床。
※ clip_pass 実行中は keepalive を skip するガードはあるが、「経路が2つある」構造自体が risk。

→ 収斂案（どちらかに寄せる）:
- **案A: app 一本化** — login も keepalive も投稿も instagrapi の同一 device session で。web browser は使わない。
  keepalive = `cl.get_timeline_feed()` 等の軽い read を定期実行。最も公式推奨に沿う。
- **案B: web 一本化** — 投稿も browser 内で（ただし過去 IG が web 自動投稿を silently drop した経緯あり=POST-11 で instagrapi に移行した）。∴ 案A が本命。

## 正しい login / session 運用（次の1回に適用するレシピ）

1. **web と app を同一アカウントで同時稼働させない**（concurrent_session の直接原因）。app 一本化を推奨。
2. **login() は最初の1回だけ** → `dump_settings()` → 次回以降は `load_settings()`/`set_settings()` を
   **login より前に**呼んでから warm。fresh `Client()` を毎回作らない（毎回新 device UUID = challenge 誘発）。
   出典: https://instagrapi.com/guides/instagrapi-session-persistence
   > "Re-fingerprinting on every login is the single most common cause of challenge_required"
3. **session が死んだら `relogin()`（`login()` ではない）**。relogin は device fingerprint を保持し cookie だけ更新。
   login は fingerprint をリセットし challenge_required を誘発。
4. **device settings・proxy IP・country/locale を固定**。account history と一致させる（"one stable proxy/IP per account"）。
5. `cl.delay_range = [1,3]` 等ランダム遅延必須。write 系（follow/like/DM/upload）連発禁止。read-heavy から。
6. **1 account = 1 in-flight request**。同一 session を並列実行しない。並列性は「アカウントを増やす」で得る。
7. login 直後は write を避け、数時間〜数日 read 中心の warmup（新規/復旧アカ全般のルール）。
8. **login 時に `cl.last_response.json()` の `logout_reason` を必ずログ**（signature_revoked / password_changed /
   concurrent_session を判別 → 次に同現象が起きたら一次情報で原因確定できる）。今は「BadPassword でない」までしか不明。

## cooldown

新規/復旧 login 後の具体的 cooldown 時間を明記した一次情報は見つからず（"days" 程度の記述のみ）。
安全側 = 直近3連続 revoke 後は最低 24h 空けてから relogin を1回だけ（現行の tier3 cooldown guard と整合）。

## GitHub issues（実ユーザー報告、subzeroid/instagrapi）
- #969 Login required every 2-3 days → メンテナ: instagrapi のバグでなく server-side trust 判定
- #1744 Unrecognized device alert → "avoid fresh Client() per login / keep proxy country・locale・device consistent /
  avoid rotating proxy identity during login or challenge"
- #1982 photo_upload fails when logged in via sessionid → uuid 保持で relogin。web/app 境界の sessionid は不安定

## 未解決
- `signature_revoked` が IG 公式エラーコード名か instagrapi 側の通称か特定できず（gh code 検索 0 ヒット、
  instagrapi.com ガイド内のみ言及）。
