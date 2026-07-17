# 56 — X(Twitter) session が「常時起動なのに切れる」真因と恒久策（2026-07-17 実測）

## 症状
daily-driver（常時起動 CDP :9222）で X 投稿。07-16 まで staged 成功、07-17 日中に `x_session_logged_out_stale_auth_token`、x.com/home が「Something went wrong」（/login へリダイレクトせず現 URL に留まる）。

## 真因（実 vault 履歴 + ログで確定）

**ct0（CSRF token）cookie の失効。** auth_token は生きているが ct0 が抜けると X の React クライアントがクラッシュして "Something went wrong" を出す。

決定的証拠:
- `~/.cloak/vault/daily-driver/auth-state.*.json` の cookie 履歴: 16:01 は auth_token+ct0 両方あり（唯一の完全ログイン）→ 16:31 以降 ct0 だけ消失。
- `cdp-daily-driver-guard.log`: **13:41 の relaunch 以降クラッシュ/再起動ゼロ**。ブラウザは生きたまま、ライブ cookie jar から ct0 だけ消えた = X 側の **CSRF ローテーション**（サーバが ct0 を再発行したが、アイドルタブが新 Set-Cookie を受け取れなかった）。
- `session_vault_tick.sh`（30分 launchd tick）の keepalive URL リストは **coconala.com と instagram.com のみ。x.com が無い** → X を定期 touch する仕組みが存在せず、ct0 再発行の機会がなかった。`_logged_out_for()` の x.com 判定はコードにあるが tick から未接続の死に分岐。
- digest 実測: vault の auth_token が `.env` の値とバイト一致 = 無効化済みの古いトークンを空復元してた（同じ状態の別断面）。

**保存の仕組み自体は正常**（dump は ct0 も対象）。問題は「保存対象外」ではなく「保存時点で既に ct0 がライブから消えていた」こと。

## GH 先行解（実測、車輪の再発明回避）
- **d60/twikit**（★4,561）: `dict(self.http.cookies)` で jar 全体を保存。`cookies_file` があれば `login()` を完全スキップ。「login() を繰り返すな、save_cookies→load_cookies で再利用しろ」（ToProtectYourAccount）= login 試行自体が不審行動として監視される。
- **vladkens/twscrape**（★2,586）: cookie 一式 + headers をアカウント単位でバンドル保存/復元。`assert "ct0" in client.cookies`。
- **the-convocation/twitter-scraper**: `isLoggedIn()` は ct0 + auth_token 両方要求（「ct0 alone is NOT sufficient - without auth_token, Twitter returns 401」）。各レスポンスの Set-Cookie を毎回 jar に反映 → ct0 ローテーションを自動追従。

→ 最低必須 = **ct0 + auth_token ペア**、実運用は **jar 全体**（twid/guest_id/kdt/__cf_bm 等含む）。

## 恒久策（= #75 で実装済み、commit anicca 7f37dc9f + 726e906f）
1. ✅ **x.com/home + zenn.dev/dashboard を keepalive 監視に追加**: 30分毎 touch → ct0 再発行(Set-Cookie)受信で CSRF ローテ失効を防ぐ。死亡即 telegram アラート。
2. ✅ **ct0 健全性ゲート**（`SITE_HEALTH_REQUIRED = {"x.com": ("auth_token","ct0")}`）: dump 時に x.com の auth_token+ct0 が揃わない半死状態なら、prior vault が健全だった時だけ差し戻す（他サイト無干渉）。negative test 実測済み。
3. ✅ **password 再ログイン self-heal**（`relogin_x` + `RELOGIN_COOLDOWN_SEC=6h` + marker）: keepalive が logged_out:true を返した時だけ1回、TWITTER_PASSWORD で再ログイン。login() 連打を cooldown で厳格禁止（twikit 警告）。phone/SMS 要求検知で即停止 + Dais エスカレーション。

## 未解決（Dais 判断）
X の password-recovery は今も本人携帯 SMS のみ。relogin self-heal が SMS 要求に当たると止まる。恒久解 = 復旧手段を AI 読取可能チャネル（AI 所有 email or .env の Twilio 番号）に変更。

## 一般法則
「プロセス常時起動」≠「session 有効」。SaaS の session は cookie の**集合**（auth_token だけでなく CSRF/ct0）で成立し、サーバ側ローテーションで一部だけ失効しうる。keepalive は「ログインが要る全ドメインを監視リストに入れて初めて機能」— リスト外のドメインの session は静かに腐る。「装備済み ≠ 配線済み」の再演。復旧の前に必ず「どの cookie が欠けたか」を vault 履歴の断面で見る。
