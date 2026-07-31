# 発注: P0 修理 — prod Telegram webhook 401 を直し、D-1〜D-3 の実 Telegram E2E まで完走する

★これが今の全システムの栓。最優先★
役割: あなた(Sol) = execute+verify 全部（no human loop — Dais の Telegram で実測してよい、と Dais 裁定済み）。報告 = bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-fixwebhook fable-main '<msg>'。
★secret 値を stdout/agmsg/commit に出すな★

## 実測済みの現状（Fable、2026-07-21 早朝）
- 真因: rotate 用に Railway へ --skip-deploys で staged された新 secret 群（LM_TELEGRAM_WEBHOOK_SECRET 含む）が、dev→main 昇格の auto-deploy で本番に乗った。Telegram は旧 secret のまま → prod が全 update を 401 拒否。
- 証拠: getWebhookInfo = last_error "Wrong response from the webhook: 401 Unauthorized"、pending≥2。ボタン無反応・live location 不達の真因もこれ。
- Railway CLI/API = Unauthorized（token 失効）。`railway login` は TTY+browser 必須。

## 手順
1. **Railway 認証の回復（人手なし）**: CloakBrowser daily-driver（CDP、http://[::1]:9222 — IPv6 側。プロファイル ~/.cloak/profiles/daily-driver、既にヘッドで起動中）で railway.app に既存 cookie session が生きているか確認。生きていれば: `railway login --browserless` を pty 付き（script -q /dev/null または expect）で起動し、表示される pairing URL を CloakBrowser で開いて承認。cookie 切れなら Account Settings → Tokens で API token を発行し、env RAILWAY_API_TOKEN として使う（値は chmod 600 一時ファイル、使用後削除）。
   - railway.app の Google OAuth が要求されたら: daily-driver の Google session も切れている（実測済み）。その場合は camofox fallback か、Railway dashboard の email login を試す。全 tier 失敗なら BLOCKED-on-Dais で報告（「blocked」と言う前に4 tier 全部試せ）。
2. 認証回復後: `railway variable get/list -s life-call -e production` 相当で現 LM_TELEGRAM_WEBHOOK_SECRET と LM_TELEGRAM_BOT_TOKEN を取得（値は非表示のまま shell 変数で扱う）。
3. **setWebhook 再登録**: 現 prod の webhook URL は getWebhookInfo の url フィールドから取る。`allowed_updates=["message","callback_query","edited_message"]`（edited_message 追加 = LM-30 の live location に必須）+ `secret_token=<現 prod env の値>` で再登録 → getWebhookInfo で last_error が消え pending が流れることを確認。
4. **smoke**: /health 200、TG に test メッセージ送信→bot 応答、GEMINI/TELNYX/SUPABASE の staged 新値で動いているか（dial preflight: Telnyx balance API 200）。壊れていたら該当 env を旧値に戻す判断も可（報告してから）。
5. **D-1 location 遅刻連絡 E2E**: Dais は live location を共有済み（本人証言。401 で落ちた可能性 → 再共有が要る場合は TG で Dais に1行依頼を送ってよい: 「位置情報をもう一度ライブ共有してください（📎→位置情報→ライブ）」）。lm_user_locations に row が入ることを確認 → 間に合わないテストイベント（外部 attendee=keiodaisuke+lmtest@gmail.com、start が近く travel が大きい）を gog calendar で作成 → 遅刻メールが実際に届く（Resend 送信ログ + 受信確認）or「送れなかった」正直報告が TG に来ることを実測。
6. **D-2 discovery E2E**: 前回送信は成功済み（last_discovery_at 実測済み）。[やり方を見る] ボタンをあなたが Telethon（MTProto user session、~/.openclaw 系に既存）で実際にタップ → callback が 200 で処理され、手順説明メッセージが返ることを実測。解錠済み gate に送られないことは unit 済みなので、location 解錠後に discovery が location を再告知しないことだけ DB で確認。
7. **D-3 panel E2E**: /panel を Telethon で送信 → 返ってきた単回 URL を CloakBrowser で開く → 5要素が実データで表示されるのを screenshot で記録（path を報告）。
8. **spec 更新**: consolidation spec §10 の順6/7/8a-c の行を「done (L3 実測値付き)」に更新、§10.1 に「webhook 401 事故と修理」の1行記録 → commit+push（anicca-project、feature/clip-rewards）。

## 禁止
secret 平文出力 / Dais の個人 SNS への投稿（TG の LM bot チャット内のみ可）/ 旧 Stripe endpoint の disable / 破壊的 env 変更。

DONE 報告: getWebhookInfo 実出力（error 消滅）+ D-1 メール証拠 + D-2 callback 応答 + D-3 screenshot path + spec commit hash。
