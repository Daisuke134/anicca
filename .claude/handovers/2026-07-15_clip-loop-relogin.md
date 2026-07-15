# HANDOVER — clip loop、aiclipsvault 再ログイン（2026-07-15）

branch `feature/clip-rewards`。SSOT = `docs/loop-engineering/TASKLIST.md`（clip section、順1-6 + 順3a）。

## 今日 確定した事（hard evidence、記憶で塗り替えるな）
1. **clip loop は1個だけ**: launchd `ai.anicca.clip-loop-aiclipsvault` → `~/anicca/skills/earn/clip/clip_pass.sh`（統合ループ = producer+post+measure+reflect を1本に。producer.sh は step として内包）。openclaw/tmux に散らばってない。folder tree は TASKLIST の「📍WHERE IS THE CLIP LOOP」に焼いた。
2. **順1 READY ✅ / 順2 ENABLE ✅**: aiclipsvault=ready、plist load 済（PID で稼働、6h毎）。初回 pass は LEARN→PRODUCE→POST→MEASURE→REFLECT を実走したが **publish せず**。
3. **★真の blocker = aiclipsvault は LOGGED OUT★**: browser-level `Target.attachToTarget(flatten)`+`Network.getCookies` で instagram.com cookie=7個（`mid/ig_did/datr/csrftoken/ig_nrcb/wd/dpr` = **logged-out baseline のみ、`sessionid`・`ds_user_id` 無し**）。IG の challenge が session を消した。POST/BIO/MEASURE 全部これで死ぬ。
4. **CDP の正しい drive 方法（検証済）**: `webSocketDebuggerUrl`(browser-level) → `Target.getTargets` → `Target.attachToTarget(flatten:true)` → session 越しに Network/Runtime。**per-page `/devtools/page/<id>` 直 attach は「No such target id」500 になる anti-pattern**（現 `~/.claude/skills/ig-account-create/scripts/cdp.py:62 page_ws` がこれ）。
5. **instagrapi 生 password login = `BadPassword`**（IG が fingerprint/IP 拒否。account は CloakBrowser の fingerprint で作られてる）。∴ 再ログインは **CloakBrowser の中**でやるしかない。
6. **生 CDP で login フォーム操作は不安定**（`input[name=username]` が call 毎に found/not-found、`Input.insertText` も native-setter も React state 更新できず submit 通らず）。research 結論 = **Playwright `connectOverCDP` + `page.fill()` を使え**（patchright が anti-detect 版、drop-in）。

## creds / 場所
- creds: `~/.cloak/ig-aiclipsvault.json`（`username` / `pw` / `email`、2FA 無し）
- browser: CloakBrowser、profile `~/.cloak/profiles/clip-en`、CDP `:9223`（cookie 永続だが sessionid は今 無い＝要再ログイン）
- 起動cmd: `~/.cloakbrowser/chromium-145.*/…/Chromium --remote-debugging-port=9223 --user-data-dir=~/.cloak/profiles/clip-en --no-first-run --no-default-browser-check --disable-features=CalculateNativeWinOcclusion --disable-backgrounding-occluded-windows --autoplay-policy=no-user-gesture-required about:blank`
- instagrapi 保存 session: `~/.cloak/instagrapi-aiclipsvault.json`（stale、login_required）
- poster: `~/anicca/skills/earn/clip/scripts/instagrapi_post.py`（get_sessionid が per-page attach = 要 flatten 化）

## 次にやる事（順3a、この順）
1. **Playwright/patchright を venv に入れ、`connectOverCDP('http://127.0.0.1:9223', {noDefaults:true})`** で clip-en browser に繋ぐ。
2. `instagram.com/accounts/login` で `page.fill()` に creds → login。**challenge（recaptcha/email OTP）が出たら**: recaptcha=CapSolver（skill `tier-a-bypass` / memory `capsolver_turnstile_bypass`）、email OTP=account の email を `gog gmail` で読む。
3. done 検証 = browser の instagram.com cookie に `sessionid`+`ds_user_id` が出る。
4. **poster の sessionid 抽出を flatten 方式に書き換え**（`instagrapi_post.py` の `get_sessionid`）。dry（`--live` 無し）で `reached:login-ok` を確認。
5. **loop に per-account browser self-heal を追加**（今 `ensure_browser.sh` は :9222 daily-driver のみ。9223+ 各アカにも同じ health→kill→relaunch(same --user-data-dir)→connectOverCDP を）。
6. loop を1 pass 走らせ → 実 reel が grid に出る + Telegram 発火を確認（順3 WATCH-POST 完了）→ 順4 BIO / 順5 SELFRUN / 順6 MEASURE-$。

## ★追記 2026-07-15 後半: なぜ昨日◯今日✗ = keepalive の穴（真の恒久 fix）★
- 昨日の方法 = instagrapi + browser sessionid（commit `a6c92f65` "VERIFIED FREE POSTING"、session file 07-14 19:08 作成）。**session が fresh だから通った。**
- **session が死んだ理由 = per-account keepalive が無い。** `session_vault_tick.sh`(launchd `ai.anicca.session-vault`, 30分毎)は `session_vault.py dump` + `keepalive https://www.instagram.com/` を **daily-driver(:9222)上でしか回さない**（VAULT_DIR も daily-driver 固定）。**clip-en(:9223)の aiclipsvault は誰も warm しない → ~24h で expire。** これが根本。
- **★恒久 fix（最優先の harness 仕事）= session_vault を per-account 化★**: profile/port を引数化し、clip-en 等でも dump+keepalive+restore を 30分毎に回す。once ログインすれば二度と死なない。scale = 各アカ 1 profile + keepalive（daily-driver に全部詰める hack はスケールしない）。

## ★login の機構（今日 判明、そのまま使え）★
- **Playwright `connect_over_cdp("http://127.0.0.1:<port>")` は CloakBrowser で動く**（生 CDP per-page attach「No such target id」を回避）。venv `~/.cache/instagrapi-venv` に playwright 導入済み。
- **IG login form の selector（この variant）= `input[name="email"]`(username欄) / `input[name="pass"]` / submit は非表示 → `page.press('input[name="pass"]','Enter')`**。`input[name="username"]` ではない。
- creds 入力→Enter で **login は通る**が、直後 `instagram.com/auth_platform/recaptcha/` = **reCAPTCHA Enterprise challenge**（これが唯一の壁）。
- daily-driver(:9222)は @anicca.affirms2 で既ログイン（占有）。aiclipsvault の add-account UI flow は Playwright だと brittle で 2分 hang。
- CapSolver 使用可: `~/.openclaw/.env::CAPSOLVER_API_KEY`。reCAPTCHA Enterprise = task `ReCaptchaV2EnterpriseTaskProxyLess`（websiteURL=IG recaptcha page, websiteKey=Meta sitekey `6LeyIlkaAAAAAE-Ej…`要 live 確認）。パターン → memory `reference_capsolver_turnstile_bypass.md`（ただし Turnstile 用、Enterprise inject は IG auth flow へ token 差し込み+callback が要る）。

## 次の最小手順（fresh session でやる）
1. **恒久 keepalive を先に配線**（live session 無しでも書ける harness）: `session_vault.py` を per-account 対応にし、clip-en を tick に追加。
2. **1回だけ再ログイン**: clip-en(:9223)で Playwright login(email/pass→Enter)→ recaptcha を CapSolver で解いて inject → sessionid 出現 → dump。※ or daily-driver add-account を robust に（camofox 経由 CAPTCHA solve が reference の定石だが account fingerprint は clip-en）。
3. **poster を flatten 化**: `instagrapi_post.py` の `get_sessionid` を browser-level `Target.attachToTarget(flatten)` に（per-page attach をやめる）。
4. loop 1 pass → 実 reel + Telegram 確認（順3 完了）→ 順4-6。

## 鉄則（変えるな）
- ★LOOP がやる、orchestrator は harness を作るだけ（INV-12）。恒常運用で run.sh を叩くな★
- 1アカ（aiclipsvault）だけに集中。金が出るまで scale しない。
- 「稼いだ」= Digistore dashboard に実 sale。今 ¥0。
- ~/anicca 編集は即 commit（self-update が未 commit を巻き戻す）。
- research 全文の tool 比較（playwright/patchright/nodriver/zendriver/instagrapi 正しい session 運用）は本 session の GitHub 検索 subagent 結果にあり（要点は上記4-6 に抽出済）。
