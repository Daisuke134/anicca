# Instagram 4アカ × (Reels + Carousel) self-improve loop — 設計プラン

最終更新: 2026-07-16 / 出典 = gh(subzeroid/instagrapi 実コード) + gh search（実 repo 実測）。TikTok は使わない、Instagram のみ。

## 確定した事実（実測）

### instagrapi は reels も carousel も同一 session で投稿できる（gh 実コードで確認）
- `subzeroid/instagrapi/mixins/clip.py` → `clip_upload()` = **Reels（動画）**。今 clip loop が使用中。
- `subzeroid/instagrapi/mixins/album.py` → `album_upload(paths: List[str], caption, ...)` = **Carousel（画像スライドショー）**。複数画像パスを渡すだけ。
- `photo.py`/`video.py` も有り。**4種すべて同じ Client（同じ CloakBrowser sessionid）で動く** → slideshow は clip と全く同じ投稿経路。別 API 不要。
- 出典: `gh api repos/subzeroid/instagrapi/contents/instagrapi/mixins` で album.py/clip.py/photo.py/video.py の存在を確認。`album_upload` は実 repo（au-re/i-love-my-architecture 等）で production 使用実績あり。

### open source（我々と同じ事をやってる、copy/tweak 候補）
| repo | 何を | 我々がどう使う |
|---|---|---|
| `itsrafiul/auto-reels-uploader` | instagrapi でフォルダ内動画を Reels 自動投稿（moviepy/pillow 前処理込み） | POST 部の参照（我々は既に instagrapi_post.py で同等を実装済み） |
| `Oxooi/Automated-Instagram-Bot` | 画像生成(DALL-E3)→GPT-Vision で title/desc/hashtag→instagrapi upload | PRODUCE→POST の caption/hashtag 自動化の参照 |
| `cporter202/automate-faceless-content` | faceless short/long content を idea→script→video→scheduled post 自動化 | エンジン全体の設計参照 |
| `the-data-circle/instagram-bot` | instagrapi で scrape/like/follow（engagement） | WARM/keepalive の action 参照 |

## 我々の構成（既存 clip loop = 完成した土台）

```
4 CloakBrowser profiles（各アカ = 別 identity・別 profile・別 CDP port）
  clip-en  :9223  @aiclipsvault      (AI/money/wealth)  ← 今 login 生存
  clip-en2 :9224  @aiclips_studio_hq
  clip-en3 :9227  @aiclips_world_hq
  clip-en4 :9228  @aiclips_hub_hq

各アカ共通エンジン（launchd 6h毎、既存 clip_pass.sh）:
  LEARN → AFF-FIND → WARM → PRODUCE → POST → BIO → MEASURE → REFLECT
  投稿 = CloakBrowser sessionid → instagrapi（clip_upload or album_upload）
```

## プラン（既存 clip loop に足す/変える。最小・確実優先）

### STEP 1: PRODUCE を format 差し替え可能に（reels + carousel）
- 今 `producer.sh` は動画 clip のみ生成。ここに「carousel 生成」ノードを足す（画像複数枚 → paths[]）。
- format 選択は playbook/offer 由来（judgment、hardcode しない）。

### STEP 2: POST を album_upload に対応
- `instagrapi_post.py` に `--kind reels|carousel` を追加。carousel なら `cl.album_upload(paths, caption)`。
- login 経路（tier1/2 = CloakBrowser sessionid）は**変えない**。upload 関数だけ分岐。

### STEP 3: 4アカ orchestration
- clip-accounts.json の全 ready アカを iterate（既存構造）。**直列**で回す（1アカずつ、concurrent_session revoke 回避 = 前回研究）。
- 各アカ 1日 ≤1-2 投稿（cadence gate 既存）。アカ間で delay。

### STEP 4: keepalive を確実化（web session forever）
- ※research 継続中。方向性: 「instagram.com を開くだけ」では ~24h で死んだ実績 → instagrapi の軽い authenticated read（get_timeline_feed 等）を定期実行して cookie を延命する方が確実。
- cookie の disk 永続（Chromium Cookies SQLite flush）も確認要。

### STEP 5: 金の計測（既存 measure_dollar.py）
- Digistore key 投入 → sid1 別 EPC を REFLECT に渡す。carousel は Amazon Associates も可（別アカ・別 ASP）。

## 鉄則（変えない）
- Instagram のみ。TikTok 不使用。
- login flow = CloakBrowser session + API。relogin/password 不使用。
- 1アカ1 niche・1 identity。初 sale が出るまで format 横展開しても投稿数を無闇に増やさない。
- 全 format 共通エンジン（LEARN→PRODUCE→POST→MEASURE→REFLECT）。差し替えは PRODUCE ノード（clip/carousel）と MONETIZE ノード（Digistore/Amazon）のみ。

## 実測スナップショット 2026-07-17 10:30 JST（fix 前の現状。次セッションはここから）

| 項目 | 実測値 |
|---|---|
| loop プロセス | 稼働中。launchd `ai.anicca.clip-loop-aiclipsvault`（6h 間隔、last exit 0、2026-07-17 08:39 pass complete） |
| 実投稿 | **2026-07-14 19:33 が最終確定投稿**。以降 3日間、毎パス `LoginRequired` で POST/BIO skip |
| 直接原因 | instagrapi session 失効（`bio_step: session invalid (LoginRequired)` が毎パス、`~/.cloak/instagrapi-aiclipsvault.json` は更新されるが auth 通らず） |
| queue | 未投稿 mp4 17本滞留（PRODUCE は生きている）。pending-verify 2本が 07-13 から放置 |
| metrics | `~/clips/clip-metrics.jsonl` = 0 バイト（07-14 20:21 以降）。LEARN が4パス連続で「pipeline broken」と自己申告 |
| 収益 | ledger 全112行 earn_usdc=0。Digistore key も unset＝$計測配線ゼロ |
| アカウント | 実ログイン済み（instagrapi settings 保持）= aiclipsvault のみ。world_hq/hub_hq は status=ready だが settings ファイル無し。studio_hq=investigating（5/5 publish 未確認） |
| run.sh アカ選択 | 配列順 first-ready で break＝常に aiclipsvault 固定。ローテーションなし |
| STEP 1〜5 | 全て未実装（album_upload grep 0ヒット、--kind フラグ無し、measure_dollar.py は存在するが loop から未呼出、keepalive 無し） |
| 誤り是正 | 「4アカ loop が回っている」は誤り。回っているのは単一アカ Reels loop で、それも 07-14 から投稿停止中 |

### fix 優先順 → 廃止。§「TODO 正本 2026-07-17」が上書き（旧3「world_hq/hub_hq settings 生成」は one-loop-one-acc 決定で不要になった。旧 STEP1-3 の carousel/4アカ化も defer）

## 再実測 2026-07-17 10:55 JST — 「解決したはず」は誤り、未解決

| 事実 | 証拠 |
|---|---|
| session 復旧していない | 今日 08:35 パスも `{"outcome": "skip", "reason": "no valid session"}`、bio_step 直近6回連続 `LoginRequired: login_required` |
| 最終確定投稿は 07-14 19:33 のまま | `.last-post-aiclipsvault` = epoch 1784025225、posted/ に 07-14 以降の新規ファイルなし |
| 真因（コードに実測記録あり） | `instagrapi_post.py:83-90`「tier3 password login は数分以内に2回 "成功" → どちらも clip_upload 中に IG が revoke」。24h クールダウン (b0a80b65) は緩和策で根本修正ではない。**password login は焼け石。fix は tier1 = CloakBrowser 実ブラウザ session からの sessionid 再 export** |
| 4アカに増えた経緯 | aiclipsvault の投稿/検証不調期（07-11 web composer 死亡、07-12 studio_hq を診断用に投入、07-13 world/hub warming 開始）に代替として順次増えた（clip-accounts.json note で確認） |
| affiliate link は実在・未反映 | `~/clips/offer.json`: Q-Money + E-Mail Funnel、50% (~$88 net/sale)、`digistore24.com/redir/569951/keiodaisukeaiclips1f031/`、joined=true。**bio には一度も載っていない**（bio_step が LoginRequired で毎パス skip）。API key 不要設計（redir リンクのみ） |
| 収益 | ledger 全行 earn_usdc=0 |

## 方針決定（Dais 2026-07-17 — 上の STEP1-5 プランを上書き。これが正本）

1. **one loop = one acc**。clip loop = aiclipsvault 専任。他3アカ（studio/world/hub）は freeze（削除しない、増殖用に温存）。
2. **loop 増殖の唯一のゲート = validated $**。realized sale ≥1 を Digistore 画面 + ledger で確認できた loop だけが、token コストを自弁できるとみなして複製解禁（1 acc = 1 loop で spawn）。
3. **carousel/slideshow は今やらない**。順番: main marketing engine（共通 core）→ clip loop で実証 → video loop → affiliate loop（slideshow loop に改名）。
4. engine core（LEARN→PRODUCE→POST→MEASURE→REFLECT）は全 channel 共有。channel 差分 = PRODUCE format / POST upload 関数 / MONETIZE ASP だけ plug-in。

## TODO 正本 2026-07-17（TaskList tool に同 ID で登録済み）

| # | タスク | blockedBy | 状態 |
|---|---|---|---|
| 1 | aiclipsvault session 根本復旧（tier1 sessionid 再注入経路の修理。password login は IG が revoke するので捨てる） | - | pending |
| 2 | Digistore link を bio に反映、実ブラウザで表示確認（offer.json 実在、bio_step 実装済み、session だけがブロッカー） | 1 | pending |
| 3 | metrics pipeline 復旧（clip-metrics.jsonl 0バイト since 07-14、REFLECT 盲目） | - | pending |
| 4 | keepalive 実装（authenticated read 定期実行で session 延命。無いとまた3日で死ぬ） | 1 | pending |
| 5 | one-loop-one-acc codify（他3アカ freeze、loop の aiclipsvault 専任明示） | - | pending |
| 6 | $ validation gate 定義（sale 1件を自分の目で確認 → loop 増殖解禁） | 2 | pending |
| 7 | shared marketing engine 抽出（channel-agnostic core spec 化。clip→video→slideshow） | 6 | pending |

## v3 — session-vault 発見 & 真の壁の特定（Dais + 実測 2026-07-17 11:10 JST。これが最新 SSOT）

### 実測で判明した現実（前セッションが知らずに tier3 pw login に走った真因）
- **session-vault は実在・稼働中**: `ai.anicca.session-vault`（launchd, 30分毎）→ `~/anicca/skills/browser/scripts/session_vault_tick.sh` + `session_vault.py`。daily-driver(:9222) と 4 clip アカ(clip-en〜en4)のブラウザを起動維持し、cookie を `~/.cloak/vault/<profile>/auth-state.json` に bank する。
- **その keepalive の "logged_out" 信号は嘘（false-positive バグ）**: `session_vault.py:210` の判定は「final URL が /login にリダイレクトするか」だけ。sessionid を一度も見ない（grep sessionid = 0）。IG は ds_user_id だけ残った半ログインを /login に飛ばさない（homepage にモーダル重ねるだけ）ので、sessionid が死んでいても永遠に `logged_out:false` を返し続ける。→ 失効を検知できない。
- **sessionid はどこにも生きていない（全部実測 2026-07-17）**: clip-en/en2/en3/en4 の profile Cookies SQLite = sessionid 0件。vault/clip-en/auth-state.json（10:56 最新 dump）= sessionid 0件。`instagrapi-aiclipsvault.json` の authorization_data には saved sessionid が有るが tier1 の get_timeline_feed → LoginRequired = **IG がサーバ側で 07-14 に revoke 済み**。vault はサーバ側で殺された session を蘇生できない。
- **アーキ的ギャップ**: clip loop の tier2 は vault を読まず自前で CDP getAllCookies している。session の SSOT が二重化（vault と loop の直読み）。ただし今日は vault も空なので、vault 直読みに直しても今すぐは救えない。

### 真の壁は1個
**reCAPTCHA Enterprise を通してブラウザ UI 経由で fresh sessionid を1個発行させる。** credential は IG に受理される（ds_user_id 付与まで到達）が、reCAPTCHA チェックボックスで停止。ここを越えれば sessionid が発行され、vault が bank し始め、以後 keepalive で延命できる。

### アーキテクチャ改訂（session の SSOT を一本化）
1. session の唯一の正本 = `~/.cloak/vault/<profile>/auth-state.json`。
2. clip loop の login は「vault の sessionid を instagrapi settings に注入」を tier1 にする（自前 CDP getAllCookies は tier2 に降格）。
3. keepalive の logged_out 判定を **sessionid 実在チェック**に変える（URL リダイレクトだけ見るのをやめる）。sessionid が消えたら即 alert/re-login をトリガー。これが無いと今回の「3日気づかず」を繰り返す。
4. fresh login（reCAPTCHA 突破）は Fable が CDP で直接実行する critical execution。search と定型 impl は Sonnet。

### 改訂 TODO（TaskList tool と同 ID 同期。SDD→TDD→VDD で回す）
| # | タスク | 実行者 | blockedBy |
|---|---|---|---|
| 1 | fresh login: reCAPTCHA 突破 → 生 sessionid 発行 → vault + instagrapi settings に着床、get_timeline_feed green を目視 | **Fable 直接**（critical exec） | - |
| 8 | keepalive の logged_out 判定を sessionid ベースに修正（false-positive バグ） | Sonnet impl / Fable verify | - |
| 9 | clip loop login を vault-first に配線（sessionid SSOT 一本化。tier1=vault 読み、CDP 直読みは tier2 降格） | Sonnet impl / Fable verify | 1 |
| 2 | Digistore link を bio に反映、実ブラウザで表示確認 | Sonnet / Fable verify | 1 |
| 3 | metrics pipeline 復旧（clip-metrics.jsonl 0バイト） | Sonnet / Fable verify | - |
| 4 | keepalive warming 強化（authenticated read で server-side session を温める） | Sonnet / Fable verify | 8 |
| 5 | one-loop-one-acc codify（他3アカ freeze） | Sonnet / Fable verify | - |
| 6 | $ validation gate 定義（realized sale ≥1 → loop 増殖解禁） | Fable | 2 |
| 7 | shared marketing engine 抽出（channel core spec、clip→video→slideshow） | Fable plan | 6 |

### 開発規律（全タスク共通）
- **SDD**: 各タスク着手前に spec（この doc の該当行＝不変条件）を確定。散文 spec の adversary は1ラウンドのみ。
- **TDD**: negative test を先に書く（例: sessionid 無し settings で get_timeline_feed が LoginRequired を返すこと、直後に vault 注入で green になること）。
- **VDD**: fresh-context adversary が仕様一致を判定 + Fable が実ブラウザ/実 API で E2E。両 PASS まで fix→再検証。
- 分業: **Fable = planner + verifier + critical execution（reCAPTCHA/login/on-chain）**。**Sonnet = search + 定型 impl + adversary**。

## v4 — 真犯人は reCAPTCHA ではなく IG の anti-bot soft-block（実測 2026-07-17 12:xx JST）

### やったこと（Fable 直接 execution）
- 無料 OSS solver 採用: `sarperavci/GoogleRecaptchaBypass`（audio 方式・キー不要・DrissionPage で :9223 の clip-en に attach）。venv に vendor 済み（scratchpad/solver/）。
- Meta の reCAPTCHA は instagram の referer_frame 配下にネストされた標準 reCAPTCHA Enterprise（anchor=checkbox / bframe=challenge）と判明。DrissionPage で明示的に frame 階層を降りる版を書き、**harness は端から端まで動作**（checkbox arm → audio 切替 → mp3 DL → 文字起こし → 入力 → verify）。
- login form は `<input type=submit>` の plain form（name=email/pass）。JS submit で reCAPTCHA チェックポイントに到達させることに成功。

### 判明した本当の壁（investigation）
- **reCAPTCHA audio が難化フレーズを返す**: transcript が毎回 "and then the validator at" 等の濁ったフレーズ（数字列でない）。Google が bot 疑いの低 trust クライアントに hard audio を出し、recognize_google が聞き取れない。→ audio 突破が成立しない。
- **さらに login 自体が拒否**: 突破を試みた後 login ページに「入力されたログイン情報は正しくありません（Find your account and log in）」。= IG が credential を拒否。
- **pw は正しい（重要な反証）**: tier3 API login はつい最近 instagrapi で成功していた（`instagrapi_post.py:83-90` の実測コメント「two tier3 logins both succeeded then got revoked」）。同じ pw ファイルで API は通る。→ browser login の「incorrect」は真に間違いではなく **IG の anti-automation soft-block（deflection）**。Google の hard audio と符合（IP/デバイス/挙動が flagged）。

### 却下した仮説
- 「pw が古い/間違い」→ 却下。tier3 API が同 pw で最近成功しているため。
- 「reCAPTCHA だけが壁」→ 却下。reCAPTCHA を越えても login が「incorrect」で弾かれる。壁は2枚（Google hard audio + IG soft-block）で、根は同じ = **このIP/セッションが flagged**。

### 結論と次の分岐（Dais 判断待ち）
連続の自動 login 試行は @aiclipsvault の hard-lock を招くので**一旦停止**。真の対処は「flagged 状態の解除」= 検索で得た公式知見「Rotating IP is the most reliable way」（sarperavci issue #20）。選択肢:
- **A. IP ローテーション**（Tailscale exit node / 住宅系 proxy）で clean IP から1回だけ login → sessionid 取得 → 以後 keepalive(#8 修正済) で延命。Google hard audio も clean IP なら緩む可能性。
- **B. cool-down**（数時間〜1日 放置）してから A。flagged スコアは時間で減衰する。
- **C. instagrapi tier3 を clean IP から実行**（browser UI を経由せず API login）。最近成功実績あり。revoke されたのも datacenter IP が bot 臭かった可能性 → clean IP で改善余地。
- solver harness 自体は完成・再利用可（clean IP で audio が数字列に戻れば通る）。

### harness の保存先
`scratchpad/solver/`（RecaptchaSolver.py vendor + solve_loop.py + login_solve.py）。clean IP 確保後に本採用したら `~/anicca/skills/earn/clip/scripts/` へ移して commit する。

## v5 — 正しい instagrapi 運用 + 真犯人の確定（実測 2026-07-17 13:xx JST。SSOT）

### 3仮説の検証（investigation）
- **H1 datacenter IP → 棄却**: egress IP = `AS17676 SoftBank Corp.`（三重県、consumer 住宅 ISP）。datacenter ではない。**proxy 購入は不要**（公式が否定するのは datacenter IP。我々は既に住宅系）。issue #2001 も「residential proxy でも直らない場合あり」= proxy は主因でない裏付け。
- **H2 device 再生成（re-fingerprint）→ 部分棄却**: `instagrapi_post.py` は tier1 で load_settings 済み（uuids 保持）→ tier3 relogin も基本 device 保持。ただし cooldown guard 追加(b0a80b65, 07-16)より前は tier3 が頻発、settings 破損時に fresh uuids の余地あり。寄与はするが主犯でない。
- **H3 relogin ハンマリング → 最有力（確定）**: コード自身のコメント（instagrapi_post.py:85）「two tier3 logins within minutes both succeeded then got revoked」。07-14〜16 に password login を短期連打 = instagrapi 公式が名指しする最悪アンチパターン「logging in with username/password on every run」。これがアカウントを flagged に焼いた。今日の reCAPTCHA hard audio / browser "incorrect" deflection はその reputation の結果。

### instagrapi の正しい運用（公式 best-practices より、これが正本）
出典: subzeroid/instagrapi `docs/usage-guide/best-practices.md`「Use Sessions」+ instagrapi.com/guides（2026-04-30）。核心: *"If you call .login() from scratch on every run, Instagram sees repeated fresh logins. That is much more suspicious than reusing a stable device session."*

正しい順序:
1. `set_proxy()` は login 前（ただし我々は住宅IPなので当面 proxy 無しで可）
2. `set_settings(load)` を login より前（device uuids 固定）
3. `login()` は「cookie 検証」であって毎回新規ではない（settings あれば cookie 再利用、切れた時だけ本 login に fallback）
4. keepalive = 書き込みでなく `get_timeline_feed()` の軽い authenticated read
5. LoginRequired 時のみ: `old=get_settings(); set_settings({}); set_uuids(old["uuids"]); login()`（device は変えない）
6. challenge(email code) は `challenge_code_handler` で自動解決（我々は make_gmail_handler 配線済 = instagrapi_post.py:136）
7. 成功後 `dump_settings()` で書き戻す

### ★重要: 今の flagged 状態は instagrapi でも自動救済不可
公式 `challenge_resolver.md`: Bloks redirect / reCAPTCHA checkpoint は「trusted device での手動確認が要る、instagrapi は ChallengeRequired を raise する」。email code challenge は**新規 clean login 時のみ**有効。
→ 復旧手順 = clean restart: **cooldown で flag 減衰**（数時間〜1日）→ device uuids は保持したまま 1回だけ instagrapi login（email challenge 自動解決）→ 成功したら以後 load_settings のみ、二度と password login しない。住宅IPなので proxy 不要。

### コード修正 TODO（login-once を強制する）
- tier3 の relogin を「24h cooldown」からさらに厳格化: tier1 が生きてる限り絶対 relogin しない + backoff 指数化。
- keepalive を「browser で instagram.com 開く」→「instagrapi settings で get_timeline_feed」に変更（session-vault はブラウザを温めてたが loop の実 auth は instagrapi settings。対象ズレ = #9 vault-first で統一）。
- relogin 時に明示的 `set_uuids(old_uuids)` を追加（device 保持を保証）。
- （将来）`set_proxy` を settings 由来で受ける口だけ用意（今は住宅IPで不要、oサブアカ増殖時に有用）。

### 更新した分岐（proxy 不要が判明）
- #11 を「clean IP 手配」→「**cooldown + clean instagrapi restart**」に読み替え。proxy 購入は保留（住宅IP で足りる）。
- 次の実行: (1) 今日はこれ以上 login を叩かない（flag 減衰待ち）(2) その間に login_resilient を上記に hardening（コードは書ける、E2E は cooldown 明け）(3) cooldown 明けに1回 clean login。

## v6 — 根本解 = 公式 Instagram Graph API へ移行（一次原理。SSOT・2026-07-17）

### なぜこれが根本解か（private API の構造的限界）
okgram README の技術説明: IG は session を「sessionid 単体」でなく **sessionid + device + X-MID + IG-U-RUR(地域ルーティング) + egress IP/geo + TLS(JA3/JA4) fingerprint の内部整合性**で判定する。relogin のたびにこの整合性が壊れ takeover 判定 → login_required/challenge。= private API(instagrapi) は session 死・reCAPTCHA を**構造的に排除できない**。我々の relogin 地獄はこの構造の必然。
→ 公式 Graph API は別ドメイン `graph.instagram.com` の正規 OAuth。この fingerprint 層を一切通らない = **reCAPTCHA も checkpoint も session 死も存在しない**。

### Graph API の要点（一次資料 developers.facebook.com）
- Reels 投稿: `POST /<IG_ID>/media`(media_type=REELS, video_url, caption) → `POST /<IG_ID>/media_publish`。
- rate limit: 100 投稿/24h（我々の 1-2本/日 に十分）。
- long-lived token: 60日有効、`GET graph.instagram.com/refresh_access_token` で更新 → **cron 自動 refresh で完全無人**。
- ★App Review 不要★: 自分の IG アカを Meta app の「役割(role)」に加えれば Standard Access が自動承認 = Business認証も審査も無しで即日投稿可（access-levels doc の一般規定からの推論、App ダッシュボードで要実機確認）。
- video_url は公開 URL 必須 → 我々は既に `CLOUDFLARE_TUNNEL_URL` を持つ（動画を tunnel 経由で公開 URL 化できる）。

### 唯一の関門 = 「1回だけアカウントに入る」
Graph API 化には (a) aiclipsvault を Business/Creator に変換 (b) FB Page 連携 (c) Meta app 作成 + token 発行 が要る。(a)(b) は IG にログインした状態が要る。今 automation login は flagged で reCAPTCHA 壁。**最もクリーンな1回入場 = 実機スマホの IG アプリ（trusted device、reCAPTCHA 出ない）**。それが無ければ cooldown 後の1回 clean login。
→ 一度入って Business 化 + token 発行したら、**以後 private-API login は永久に不要**。壊れる層が消える。

### 移行手順（one-time）
1. 実機 or cooldown 後の1回ログインで aiclipsvault に入る
2. プロアカウント(Business/Creator)に変換
3. Facebook Page を作成・連携
4. developers.facebook.com で Business type app 作成 → 自分の IG アカを role に追加（Standard Access）
5. 60日 long-lived token 発行
6. clip loop の POST を instagrapi clip_upload → Graph API `/media`→`/media_publish` に差し替え
7. 動画を CLOUDFLARE_TUNNEL_URL 経由で公開 URL 化して video_url に渡す
8. token 自動 refresh cron 設置（60日前に叩く）→ 完全無人 24/7

### 「今すぐ復旧」の現実（実測補足）
- 他アカに逃げる道は無い（全 clip アカ session 死、実測済 v6前段）。
- session 抽出も源が無い（daily-driver に IG login 無し、実測済）。
- instagrapi-aiclipsvault.json の sessionid は revoke 済（tier1 get_timeline_feed=LoginRequired、生きてない。ファイルに文字列がある≠生きてる）。
→ 結局「1回入場」が要る。それを Graph API 化と兼ねる（同じ1回入場で Business 変換 + token 発行まで済ませる）のが最短。

### engine への影響（横展開が更に堅くなる）
POST ノードが「instagrapi clip_upload」→「Graph API publish」になる = fragile session 層が消え、どの IG Business アカでも同じ公式経路で投稿できる。video/slide/carousel も同じ Graph API（media_type 切替）。profitable-claude repo に OSS 化する際、壊れやすい session ハックを持ち込まずに済む。

## v7 — 決定: instagrapi 継続（Graph API は fallback に降格）2026-07-17 Dais

### なぜ instagrapi を継続するか（v6 の Graph API 一択を修正）
- instagrapi は投稿を実証済み（過去110本、最終 07-14 19:33）。壊れたのは投稿能力でなく session（relogin 自滅 + flag）。投稿方式を捨てる理由は無い。
- Dais が実機アプリで aiclipsvault にログイン(trusted device)する → checkpoint が human 確認で解除・flag 減衰 → その後 Mac から instagrapi login 1回は email challenge のみ（reCAPTCHA でなく。gmail で自動解決）→ dump_settings → login-once 規律で永続。
- = Business 変換/FB Page/動画公開URL 不要。今すぐ動く。早すぎる作り込みをしない。

### 決定（正本）
- **PRIMARY = instagrapi 継続**: phone unflag → 1回 clean login → login-once 規律（#12）+ keepalive read（#4）+ session 正本統一（#9）。
- **FALLBACK = Graph API（#13）**: instagrapi が規律を守っても死に続けた場合のみ、$ 出てから構造解として移行。今はやらない。

### 実行順（phone login 前提）
1. Dais が実機 IG アプリで @aiclipsvault にログイン（credential は keiodaisuke@gmail.com へ送付済、2026-07-17）。checkpoint 解除。
2. その状態で Mac から instagrapi login を1回（tier3 cooldown stamp を一時解除して実行）。email challenge は make_gmail_handler で自動解決。成功したら dump_settings。
3. #12 login-once hardening を適用（relogin 封印 / set_uuids 保持 / keepalive=get_timeline_feed）。
4. loop 再開 → 投稿確認 → bio に Digistore link（#2）→ metrics 復活（#3）。

### 競合 Claude の整理（実測補足）
- `kankatsugai` = 架空、存在しない。
- `aiclipper.daily`(ig-myclaude.json) = メモに「別Claude」とあるが実際に clipping している別実体は無い。clipping は @aiclipsvault の loop 1本のみ。競合なし。clip は aiclipsvault 専任で正しい。

## v8 — アーキ決定: 2 repo 分離 + 共有 engine + PC 両レール（2026-07-17）

### 4つの根本問題
- P1 session 死 → login-once 規律 + keepalive read（#12/#4）
- P2 skill 散在（anicca と openclaw 二分裂）→ anicca / profitable-claude の2 repo に分離
- P3 engine 未抽出 → channel-agnostic core 1個に（#7）
- P4 session 正本二重（vault と instagrapi settings）→ 一本化（#9）

### あるべき folder tree
```
profitable-claude/            AI→fiat/crypto→人間の口座（OSS単体、外部依存なし）
├─ engine/                    ★P3 全チャネル共有 core（1個）★
│  ├─ nodes/  learn produce post measure reflect
│  ├─ session/  store.py(login-once/dump-load) keepalive.py(read/relogin封印) identity.py(uuids固定/gmail challenge)  ★P1/P4★
│  └─ loop.py  GLVS
├─ channels/  clip(reels/clip_upload/digistore) video slide(carousel/album_upload) life_manager(webapp/Stripe) capafy
├─ rails/     fiat(stripe/bank) crypto(blockrun/x402)  ★P2 出口★
├─ accounts/ state/ cron/     (openclaw から移設)
anicca/                       AI→crypto→AI自身（agent economy、self-funded）
├─ engine/(共有) earn/(trade) rails/crypto/(x402) blockrun/
```
分類基準 = 稼ぎが誰の口座に入るか1本: AIの wallet→anicca / 人間の口座→profitable-claude。

### profitable-claude は fiat + crypto 両レール（出口は全て人間）
- fiat: clip→affiliate→Digistore→人間 bank、gig/製品/Stripe→人間 bank。
- crypto: anicca/blockrun の稼ぎ方を borrow、trade(DeFi)/x402→人間の crypto wallet。
- anicca は「どんな AI も crypto で稼げる」土台を提供 → PC はそれで crypto でも稼げる（稼ぎ口増）。違いは出口が人間である点のみ。Claude は tradfi+defi 両方で no-human-loop、全額を人間へ。

### engine core（6ノード + session 層）
SESSION 層（login-once/load_settings毎回/relogin封印/keepalive=get_timeline_feed/死判定=sessionid実在#8）が全ノードの土台。
CORE: ①LEARN ②AFF-FIND ③PRODUCE(format) ④POST(投稿関数) ⑤BIO ⑥MEASURE(収益) ⑦REFLECT→①。
channel 差分は3点のみ: PRODUCE format / POST 投稿関数 / MONETIZE 収益先。clip で実証 → video → slide → life_manager → capafy → openclaw loop 移設。

## v9 — 2 repo の完全 to-be folder tree（self-contained OSS）+ gig 移行（2026-07-17）

### 独立の原則
profitable-claude は **anicca repo にも ~/.openclaw にも依存しない**。共有 engine は「sibling フォルダ import」でなく **published package `anicca-loop-engine`（PyPI, MIT）** として両 repo が install する（or vendor/ に copy）。runtime state・cron・secrets も repo 内に閉じる。

### profitable-claude/（AI→fiat+crypto→人間の口座。OSS 単体で動く）
```
profitable-claude/
├─ pyproject.toml            deps: anicca-loop-engine（package、repo path 依存なし）
├─ README.md  LICENSE(MIT)
├─ engine/                   ← ここは薄い。核は package。repo 固有の拡張のみ
├─ channels/                ← 稼ぐ手段（各 self-improve loop）
│  ├─ clip/    produce(reels) post(instagrapi.clip_upload) monetize(digistore)  offer.json accounts.json
│  ├─ gig/     ★openclaw から移設★ produce(提案) deliver(納品) monetize(human bank)
│  ├─ video/   produce(長尺) post monetize(affiliate/ad)
│  ├─ slide/   produce(carousel) post(album_upload) monetize(affiliate)
│  ├─ life_manager/  web app(自社配信) monetize(Stripe→人間)
│  └─ capafy/  製品+marketing
├─ rails/                   ← 出口（全て人間の受取先）
│  ├─ fiat/    stripe.py  bank_payout.py
│  └─ crypto/  blockrun_client.py（vendored、~/.openclaw 参照なし） x402.py → 人間 wallet
├─ session/                 ← IG 等の login-once/keepalive（fragile層を隔離）
│  ├─ store.py  keepalive.py  identity.py  challenge_gmail.py
├─ accounts/  clip-accounts.json 等（frozen 予備軍含む）
├─ state/     ledger.jsonl metrics.jsonl（不揮発、repo 内）
├─ secrets/   .env.example（実 secret は repo 外の secure store 参照、値は commit しない）
├─ cron/      launchd/*.plist と schedule 定義（openclaw gateway 非依存）
└─ tests/     各 channel の negative test + E2E
```

### anicca/（AI→crypto→AI自身。OSS framework。self-funded）
```
anicca/
├─ pyproject.toml            deps: anicca-loop-engine（同じ package）
├─ engine/                   ← ここが engine package の開発元 or 別 repo anicca-loop-engine
│  ├─ nodes/  learn produce post measure reflect
│  ├─ loop.py  GLVS
│  └─ session/  login-once 抽象（channel 非依存）
├─ earn/                     ← AI 自身のための稼ぎ
│  ├─ trade/  pm/ sol/ hl/   （PM/SOL/HL 3エンジン）
│  └─ content/  将来 clip 等（稼ぎは AI wallet へ）
├─ rails/crypto/  x402 wallet（franklin1/2）
├─ blockrun/   x402 生命線（food/shelter）
├─ citizens/   franklin1 franklin2（HOME/wallet/loop 定義）
├─ state/  cron/  tests/
```

### 共有 engine の所在（依存を断つ設計）
- 案A（推奨）: engine を独立 repo/PyPI package `anicca-loop-engine` に切り出す。anicca も profitable-claude も `pip install anicca-loop-engine`。互いの repo path を import しない = OSS 単体で動く。
- 案B: 各 repo の `vendor/engine/` に copy（package 未整備の初期）。

### gig loop の移行（動かしたまま移す = strangler-fig）
現状: gig skill は ~/anicca 配下（human-bank 専用なのに）+ cron は ~/.openclaw gateway。これを profitable-claude/channels/gig へ移す。**移行中も loop を止めない**:
1. gig skill を profitable-claude/channels/gig に copy（元は消さない）。
2. profitable-claude 側に新 cron を設置、旧 openclaw cron は残したまま**新を dry で検証**。
3. 新 loop が実際に gig を1件回して human bank へ payout する E2E を確認（vcsdd-adversary + 自分の目）。
4. 新が green を確認してから旧 openclaw cron を disable → 削除、元 skill 削除。
5. 二重稼働は最小時間に留める（共有 resource の待機規律）。

### 登録タスク
- #14 engine を anicca-loop-engine package に切り出し（両 repo が path 依存でなく package 依存に）
- #15 profitable-claude repo を作成し folder tree を敷く（channels/rails/session/state/cron）
- #16 gig loop を strangler-fig で profitable-claude/channels/gig へ移行（動かしたまま）
- #17 openclaw の全 earn skill/cron を profitable-claude へ移設し openclaw 依存を断つ

## v10 — 実証: 自動 login は壁。決定を Graph API primary に更新（2026-07-17）

### この session で試して全部 false だったこと（証拠）
- instagrapi password login（pw 修正後）→ `ChallengeRequired`（bloks native checkpoint、instagrapi が構造的に解決不可）。スマホ承認しても消えず。
- instagrapi settings の saved sessionid → `LoginRequired`（revoke 済、生きてない）。
- CloakBrowser web login（pw 修正 + 垢 un-flag 後）→ login ページに留まり sessionid 出ず。
- → **Mac からの自動 login は password 経路も browser 経路も壁**。垢はスマホ(trusted device)では入れるが、自動化 login は IG が弾く。

### 決定の更新（v7 の instagrapi-primary を修正）
v7 は「1回 clean login が取れる」前提で instagrapi 継続とした。本 session でその前提が**実証的に false**。よって:
- **PRIMARY = Graph API**。理由: one-time setup（Business 変換 + FB Page + token）は **Dais の trusted スマホ**でできる（= 現に効く手段）。自動 login（= 効かないと実証された手段）を要求しない。以後 token 投稿で login 永久不要。
- **FALLBACK = instagrapi**。もし将来 browser web session を安定取得できたら login_by_sessionid で投稿可（clip_upload は proven）。password login は使わない（bloks 壁）。
- = 「効く手段(trusted phone)に賭け、効かない手段(自動login)を捨てる」判断。flip-flop でなく証拠での更新。

### Graph API の one-time setup（Dais がスマホ/web で、自動化なし）
1. IG アプリ: aiclipsvault を プロアカウント(Business/Creator) に変換
2. Facebook Page 作成 + 連携
3. developers.facebook.com で app 作成 → 自分の IG を role 追加(Standard Access=審査不要)
4. 60日 long-lived token 発行 → Dais が token を安全に渡す（gmail 経由等）
その後 Fable が: POST を `/media`(REELS,video_url)→`/media_publish` に差替、動画を CLOUDFLARE_TUNNEL で公開URL化、token refresh cron 設置。

### profitable-claude は既存 repo（greenfield tree を実態へ修正）
`~/profitable-claude`（github Daisuke134/profitable-claude）が既に在る: bin/ config/ launchd/ ledgers/ lib/ skills/human-funded/gig/ state/ tests/。gig は **anicca(skills/{economy,earn,self-improve}/gig) と profitable-claude(skills/human-funded/gig) に二重**存在 = P2。前回 anicca→profitable-claude 移動時に gig loop が停止した（要 fix）。to-be tree は greenfield でなくこの実 repo をベースに再構成する（v9 tree は方向性、実装は実 repo 準拠）。

### 追加タスク
- #18 Graph API one-time setup を Dais に依頼（スマホ手順）+ token 受領 → POST を Graph API 化
- #19 gig loop の現状監査（二重存在 anicca vs profitable-claude、どちらが launchd 対象か、実際に earn しているか）+ 壊れているなら fix

## v11 — Graph API token 経路 確定（公式 docs 実測 2026-07-17）

出典 = developers.facebook.com 公式（crwl 実取得）。旧 doc `docs/earn/ig-posting-method-graph-api-pivot.md` line35/40「Business必須・app review必須」は**誤り、最新公式で覆る**（→ 後で是正）。

### 確定事項
- **経路 = Instagram Login**（Facebook Login でなく）→ **FB Page 不要**。host=`graph.instagram.com`、permission=`instagram_business_basic`+`instagram_business_content_publish`。
- **Creator アカで可**（Business 化不要）。`/me?fields=account_type`=Media_Creator でOK。
- **App Review 不要**（自分の垢のみ・Standard Access。自垢を App に tester 追加して使う）。
- **token 取得 = App Dashboard 直接生成**が最小: (1)Meta dev account (2)App作成 type=Business (3)Instagram 製品追加 (4)自IGを tester 追加(IG authorize popup) (5)「トークン生成」click→**60日 long-lived token が dashboard に直表示** → DOM から読む。全ステップ CloakBrowser で automation 可。
- **auto-refresh**: `GET graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=…`、50日毎 cron で無期限無人。
- **video_url**: 公開 URL の mp4 必須（resumable local upload は FB Login 限定=使えない）。CLOUDFLARE_TUNNEL で公開URL化。Reels: MP4/H264, 3s〜15min, ≤300MB, 9:16。

### 唯一の摩擦 = Meta developer account（= Facebook ログイン）
ローカルに FB session 無し（daily-driver/dd-preview に facebook cookie 0、実測）。→ Dais の既存 FB account があるか、AI 用に新規作成（新規は電話/CAPTCHA=tier-a-bypass 領域）かを決める必要。これが #13 の実質ブロッカー。

### #13 の実行ステップ（no-human-loop、Fable が drive）
1. Meta dev account の FB ログインを確保（既存 or 新規作成）
2. CloakBrowser で developers.facebook.com → App作成(Business) → Instagram 製品追加
3. 自IG(aiclipsvault)を tester 追加 → IG authorize（垢 un-flag 済なので通る見込み）
4. 「トークン生成」→ 60日 token を DOM から取得 → secure 保存
5. instagrapi_post.py の POST を Graph API `/media`(REELS,video_url)→`/media_publish` に差替（別 poster 新設、instagrapi は fallback 保持）
6. producer 出力 mp4 を CLOUDFLARE_TUNNEL で公開URL化して video_url に
7. 50日毎 refresh_access_token cron 設置
done = Graph API で reel 1本を公式投稿 + IG 確認 + refresh cron 稼働。

## v12 — openclaw earn 資産の監査 + 移設マップ（実測 2026-07-17）

openclaw = `~/.openclaw`（github Daisuke134/anicca-dais private、trunk main-internal）。skills 約400、cron jobs.json 222 job。

### earn 資産の生死（実測）
| 資産 | loop | 生死 | profitable-claude に既存? |
|---|---|---|---|
| bounty | GitHub bug bounty 自動応募 | 生（07-15に$50 PR merge実績。ただし$700で stuck-loop バグ） | あり(human-funded/bounty) |
| gig | gig 探索・応募 | 実体は **~/anicca/skills/earn/gig（OSS側）が正本**。openclaw の anicca-earn-gig は**未参照の死んだ重複**。profitable-claude/human-funded/gig は E2E テスト行のみ（本番証拠なし=前回移動で壊れた実体） | あり(但し非稼働) |
| larry/reelclaw/honne | TikTok/IG スライド・リール factory | 生（本日まで連続生成）。ただし realized $ は未確認 | なし |
| capafy | 製品+marketing | capafy-loop-daily enabled、実体 ~/anicca/skills/self/capafy-loop | 一部alias |
| stripe-revenue-listener/poller | 決済検知 | 生 | なし |
| vibe-trading / monk-factory / cfo-earner-* | - | 空箱 or 休眠 or disabled | なし |

### 依存マップ（openclaw を消すと壊れる箇所 = 実測）
- ~/anicca → ~/.openclaw 依存（**これを断てば自立可**）:
  - `earn/run.sh:27,46,315` = `~/.openclaw/.env`（共有 secrets 源）
  - `earn/gig/gig_reality_verify.sh:27` = `~/.openclaw/state/.gig-core-selfheal-request.json`
  - `earn/clip/run.sh:196` = `~/.openclaw/logs/clip-insta-poster.err.log`
  - `anicca-life-manager/SKILL.md` = `~/.openclaw/identity/profile.json` 等を正本明記
  - ほぼ全 launchd plist の Std*Path = `~/.openclaw/logs/*.log`
- profitable-claude → ~/.openclaw 依存 = **コードには無し**（README/.env.example の doc 言及のみ）。
- openclaw → profitable-claude 参照 = **grep 0件**。
- **最大の壁**: larry/reelclaw/honne は openclaw gateway（Node dist/index.js + jobs.json cron）に強結合。gig/clip/capafy/bounty は ~/anicca に実体があり openclaw 依存は .env + logs パスのみ = env の向き先変更で自立可。

### 移設仕分け
- 移設: gig(env切替で自立)/bounty($700バグ修正込)/larry・reelclaw・honne(gateway 脱却が要る)/stripe-listener/.env の実キー
- 破棄: openclaw の anicca-earn-gig(死んだ重複)/vibe-trading(空箱)/disabled一括/jobs.json.bak 40個/profitable-claude の e2e-bid 行

### 移設の順序（strangler-fig、止めずに）
1. **secrets**: profitable-claude/secrets に .env 相当を用意（値を持っていく）→ ~/anicca の run.sh 系の `~/.openclaw/.env` 参照を新パスへ。
2. **gig**: ~/anicca/skills/earn/gig を正本として profitable-claude/channels/gig に移し、openclaw の死んだ重複を削除。前回停止の真因（env/log パス依存）を env 切替で解消。launchd を新パスへ、旧を検証後 disable。
3. **larry/reelclaw/honne**: openclaw gateway 依存を外す（jobs.json cron → launchd or profitable-claude cron へ）。最難関、最後。
4. **logs**: 全 plist の Std*Path を profitable-claude/state/logs へ。
5. 各段階で copy→新検証→実 earn/E2E green→旧削除。openclaw 参照 0 を grep で確認して初めて openclaw 削除。

## v13 — Inkbox を AI identity 層に採用（2026-07-17、Dais 提案）

### #19 の結果と新方針
#19: AI-owned FB account は作成成功("Alex Vaulton", ~/.cloak/fb-aiclips.json)。だが Meta developer 登録が**電話認証で停止** — Twilio 番号が VOIP 判定で無言 reject。token 未取得。ブラウザは :9228(profile meta-dev)で Verify 画面のまま起動継続中。
※ security: subagent の grep が `AGENTMAIL_API_KEY` 値を transcript に漏洩 → **rotate 必須**（下記 #21）。

### Inkbox（inkbox.ai）採用理由
identity layer for AI agents: 実 email + **実 phone(SMS/voice)** + iMessage + **Vault(2FA/TOTP/creds保管)**。agent-signup API で account/key 不要から self-register 可（human_email に6桁コード、Dais が1回承認）。
- 今の壁を解く: Meta 電話認証を Inkbox 実番号で突破（Twilio VOIP 失敗の代替）。
- scaling: TT/IG/YT/X 各アカの email+phone を 1 persistent identity で供給。
- secret: Vault で creds 保管 → 平文 .env(今回漏洩)を卒業。plugins: claude-code-plugin あり。
- 出典: inkbox.ai/llms.txt, /docs/get-started/agent-signup.md（crwl 実取得 2026-07-17）。

### 新しい #19 実行（Inkbox 経由）
1. Inkbox agent-signup（`POST inkbox.ai/api/v1/agent-signup/` human_email=Dais, harness=claude-code）→ api_key + email + phone 取得（Dais が6桁コード承認1回）。
2. その Inkbox 番号で Meta dev の Verify を突破（:9228 の Verify 画面から resume。番号入れ替え）。
3. 以降 v11 手順: App作成→IG tester→token生成→refresh cron。
4. ※ Inkbox 番号も VOIP 判定される可能性は残る → 弾かれたら Meta の card 認証 or 別番号。要実測。

### 追加/更新タスク
- #19 更新: Inkbox 経由で phone 確保 → Meta dev verify 突破 → token
- #20 Inkbox を AI identity 基盤として採用（agent-signup + vault + phone）。TT/IG/YT/X scaling の共通土台。
- #21 ★security★ 漏洩した AGENTMAIL_API_KEY を rotate（agentmail.to）+ 使用箇所(clip/video/clip-promote CLI 等)を新keyへ。将来は Inkbox vault へ移行。

## v14 — Inkbox identity 成立、但し phone は有料（2026-07-17）

- Inkbox agent-signup 成功: `~/.cloak/inkbox.json`、handle=aiclips-agent-11a830、gmail 6桁コードを gog 自動読取で verify(agent_claimed)。identity/email は無料で使える。
- **phone は有料**: Free=3 identity・phone 無し、$10/月 Hobbyist から実 10DLC 番号1つ。= 番号取得にカード登録必須 → subagent 停止（金=Dais判断、停止点①）。
- 電話番号の選択肢（全て金 or 実番号）:
  - Inkbox $10/月 = 実10DLC番号、TT/IG/YT/X 全展開の scaling 基盤（推奨・戦略投資だが recurring）
  - SMSPool = 実mobile、小額 Stripe deposit（one-time、tier-a-bypass Pattern1）
  - Dais 実番号 = 無料・chat.db で code 自動読取。但し 1番号=1Meta垢（Dais個人Metaで使用済なら不可）
  - Twilio(既存) = VOIP で Meta reject 済（不可）
- Meta ブラウザ :9228(profile meta-dev) は Verify 画面のまま保持 → 番号さえ用意できれば即 resume → App→token。
- 決定待ち = どの番号経路にするか（Dais の money/personal-phone 判断）。

## v15 — AGENTMAIL rotate 部分完了 + Meta verify 継続（2026-07-17）
- AGENTMAIL_API_KEY rotate: 新key発行+`~/.openclaw/.env`配線済(新key auth/me=200実測、ハードコード無し)。漏洩は本体キーのみ(他6 org別キーは無関係)。★旧(漏洩)key は API DELETE が全パターン403で失効不可、旧key=まだ200生存。dashboard所有アカ不明。封じ込め=漏洩先ローカルtranscriptのみ(外部push無し)。残=AgentMailサポート手動失効依頼 or dashboard所有特定。
- Meta verify(Dais番号): subagent 継続中、token未取得、chat.dbにMeta SMS未着(番号入力〜送信の途中 or 詰まり)。:9228 保持。

## v16 — Text Message Forwarding ON、Meta SMS 未着（2026-07-17）
- Dais が iPhone の Text Message Forwarding を ON（Mac Mini + MacBook Pro 両方に共有）。番号 = Dais 実番号（正値は memory `user_phone_number.md`、public repo には書かない）。
- ★ただし Meta の認証コードが **Dais のスマホ Messages 自体にも届いていない**（転送以前に Meta SMS が未着）。= 先に送った2回は不達。resend で配信を再試行する必要。
- 状態: ブラウザ :9228(profile meta-dev) は日本番号入力済・コード待ちで保持。次の一手 = :9228 で resend → chat.db(転送ONで着信するはず) から6桁自動読取 → 入力 → dev登録完了 → App作成→IG tester→60d token。
- 未着が続くなら仮説: (a)Meta の対日本SMS遅延 (b)番号入力の国コード/形式ズレ (c)Meta が短時間の再送を抑制 → 数分空けて resend、それでも来なければ別番号(SMSPool/Inkbox$10)へ。

## v17 — Meta SMS が Mac Mini に未着で block（2026-07-17）
- resend(14:55)しても Meta の6桁が この Mac Mini の chat.db に一件も来ない（全着信ゼロ、転送 ON にしたはずだが実測ゼロ）。
- Meta UI は同一番号への再送を disabled でブロック（別番号でのみ再有効化）。フェイク番号送信はせず実番号に戻して停止（不可逆なし）。
- 切り分け（Dais 依存）: (A)iPhone 本体に Meta コードが届いてるか? YES→転送先に Mac mini が入ってないだけ（設定>メッセージ>テキストメッセージ転送で Mac mini をチェック）or コードを直接読んで貼る。NO→Meta が対象番号に配信してない→別番号(SMSPool ~$1-2 / Inkbox $10)=money 判断。
- ブラウザ :9228(tab E3973A99...) Verify 画面保持。番号 or コードが得られ次第、App作成→IG tester→60d token→POST を Graph API 化。
- ★セッション超長・token 大量消費・security事故1件 → handover 推奨。全状態は spec v1-v17 + task #1-21 に永続化済み、新セッションが :9228 と file から resume 可。

## v18 — 方向確定: loop が「垢作成→稼ぐ」を全自律（harness 原則）2026-07-17

### 決着した事実
- aiclipsvault instagrapi login = 再テストでも `ChallengeRequired`(bloks) 継続。password login はこの垢では構造的に常に壁。スマホ login 済でも自動 login のたびに新 checkpoint 生成 = **自動投稿用として poisoned**。
- Graph API 経路は電話認証で block（Meta SMS が Mac mini に未着 + 同番号 resend ブロック）。→ **Graph API は fallback に格下げ**（FB app "App Anicca" が既存＝将来やるなら app 作成は省ける）。

### 新方針（Dais 原則）: システムを作る→loop が job→我々は観測
clip loop 自身が end-to-end を自律実行できるようにする。手動 subagent で1回作るのでなく、**account 自己プロビジョニングを loop の能力(node)にする**:
```
LOOP 自律パイプライン（人間ゼロ、我々は観測のみ）:
  ①PROVISION ── fresh IG 垢を自作（email=AgentMail/Inkbox、signup、
                 flag履歴ゼロ=クリーン）→ instagrapi login-once → dump_settings
                 （既存ヒント: clip skill に test_clip_cli_self_provision_prompt.sh あり）
  ②AFFILIATE ── Digistore offer を選定 → bio に link（offer.json）
  ③PRODUCE ──── reels mp4 生成
  ④POST ─────── instagrapi clip_upload（fresh垢=login通る）
  ⑤MEASURE ──── 再生/CTR + Digistore $ 計測
  ⑥REFLECT ──── playbook 更新（self-improve）
  ⑦KEEPALIVE ── get_timeline_feed の read で session 永続（relogin 封印）
  垢が死んだら①に戻って新垢を自作（self-heal）
```
= 「垢作成→affiliate→投稿→稼ぐ」を loop が回す。我々は system を作り観測するだけ。これで end-to-end を実データでテストできる。

### login を永続させる規律（docs 研究済 v5、fresh垢に適用）
login once → dump_settings → load_settings のみ → keepalive=get_timeline_feed の read → 死判定は sessionid 実在(v8) → relogin 封印 + device uuids 保持。fresh 垢は flag 履歴が無いので初回 login がクリーンに通る見込み。

### タスク再構成（primary = loop 自律化）
- #22 [PRIMARY] clip loop に PROVISION node を組む: fresh IG 垢を自作 → instagrapi login-once → dump_settings。既存 self-provision ヒントを活かす。account 死亡時に自作し直す self-heal も。
- #12 login-once hardening（relogin封印/uuid保持/keepalive=read）を PROVISION と統合。
- #2 AFFILIATE（offer.json→bio link）を loop node 化。
- #6 $ validation gate（sale≥1）。
- #13/#19 Graph API + Meta dev token → fallback に格下げ（App Anicca 利用は将来）。
- aiclipsvault → 手動投稿の予備に温存（自動 loop からは外す。poisoned）。

## v19 — #22 設計確定（proven skill 活用、電話は無関係、email訂正）2026-07-17

### 訂正（v18 の誤り是正）
- v18「email=AgentMail/Inkbox」は**誤り**。AgentMail 等 disposable email は IG の fraud filter で自動 suspend される（実例 @aiclipper.daily 2026-06-28）。→ **fresh 垢の email は Gmail 実アドレスの plus-address（keiodaisuke+<tag>@gmail.com）のみ使う**。OTP は gog で自動読取。
- 電話認証は IG signup には出ない（実測0回）。詰まったのは Meta dev/Graph API 専用フロー。fresh 垢作成に電話は不要。

### PROVISION node 設計（proven 資産を再利用、車輪の再発明なし）
再利用する既存コード:
- `~/.claude/skills/ig-account-create/`（SKILL.md + scripts/cdp.py + cdp_incognito.py + setup_profile.py）= IG signup 自動化、E2E 実証済（0 phone/captcha/human）。email=Gmail plus-address、OTP=gog。出力 `~/.cloak/ig-<handle>.json`。
- `~/anicca/skills/earn/clip/scripts/instagrapi_post.py` の `make_gmail_handler`(L16-41、signup の email challenge に転用)・`login_resilient`(L56〜、login-once のお手本)。
- `self_heal.py`（死んだ垢の再構築パターン）。
- instagrapi `signup_caa_email`(mixins/signup.py:461) は未検証 → **ブラウザ CDP の ig-account-create（実証済）を優先**、instagrapi signup は使わない。

PROVISION node の実装:
1. `ready_account=none` を検知したら（run.sh に実コード分岐を足す。今は clip-cli.sh の自然文指示だけ＝不足）
2. ig-account-create skill を呼んで fresh 垢を作る（Gmail plus-address、CDP、gog OTP、電話なし）→ `~/.cloak/ig-<handle>.json` + clip-accounts.json に handle/port 追記
3. その垢で instagrapi login-once（make_gmail_handler で email challenge 自動）→ dump_settings
4. 以後 login-once 規律（load_settings のみ / keepalive=get_timeline_feed / relogin封印 / sessionid実在で死判定 v8）
5. 垢が死んだら self_heal が①に戻して新垢を自作

### E2E 検証（我々は観測）
fresh 垢作成 → instagrapi get_timeline_feed green → queue の reel を1本 clip_upload → IG で投稿確認 → bio に offer.json の Digistore link → 以後 loop が自律で回る。これで create→affiliate→post→earn を実データでテスト。

## v20 — 実 E2E 1周目の結果: signup/profile は完全成功、live post は session churn で未達（実測 2026-07-17 15:xx JST）

### 実施した内容（すべて手動 E2E、v19 の設計通り）
1. 専用 CloakBrowser を新規 port **9225**（9222/9223 とは別、profile `~/.cloak/profiles/clip-en5`）で起動。
2. `ig-account-create` skill の手順どおり signup: email=`keiodaisuke+aiclips27572@gmail.com`（Gmail plus-address）、OTP=`gog gmail`（SPAMから自動取得）。**0 phone / 0 captcha / 0 human** で LIVE。→ `@aiclips_world_hq2`。
3. `setup_profile.py` で icon（PIL 生成の紺地ゴールドモノグラム "AW"）+ bio 設定 → VERIFY `{bio:True, avatar:True}`。
4. `instagrapi_post.py`（`--handle aiclips_world_hq2 --port 9225`、`--live` なし）で login-once → `outcome:"dry", reached:"login-ok"` 2回とも成功。`~/.cloak/instagrapi-aiclips_world_hq2.json` に dump_settings 保存確認。
5. `--live` で `clip_upload` を2回試行 → **両方とも failed**: tier1(saved session)が数秒で `LoginRequired`、tier2(browser sessionid再取得)も `TooManyRedirects` で死亡。1回目は tier3(password login) まで自動フォールバックして「サイレント成功」した形跡があるが、その直後の clip_upload 自体が `login_required` で失敗（＝tier3 ログイン成功の直後にセッションが死ぬ）。2回目は 24h cooldown ガード(3a, `.last-pwlogin-*`)が正しく発火し tier3 を拒否（ハンマー化を自動的に防止＝設計通り）。
6. `bio_step.py`（tier-1-only、read-onlyのget_timeline_feedのみでrelogin厳禁の設計）は仕様通り `outcome:"skip", reason:"no valid session"` で正しく安全側に倒れた。

### 結論・仮説
- これは **suspension でも checkpoint でもない**（challenge UI は一度も出ていない、ブラウザの web パスワード再ログインは毎回クリーンに通った）。
- 真因の仮説: **ブラウザ web セッションと instagrapi 自身のデバイス fingerprint が互いを invalidate し合う「セッション競合」**。新規垢は IG 側の信頼スコアが低いため、この競合がより速く／確実に起きる（既存の frozen 垢群が抱えていた「3d/7d warmup 前は投稿0%成功」という過去の実測と同じ根っこの可能性が高い）。
- `instagrapi_post.py` の 24h tier3 cooldown ガード（2026-07-16 実装済）はこのケースで**意図通りに機能した**＝ハンマーを防いだ。これを迂回するのは今回禁止事項（hammer 禁止）に反するため、しなかった。

### セキュリティ上の副産物（このパスの罪の自己申告 + 是正）
- signup 中に `cdp.py insert` で入力した password が、コマンドの stdout echo（`{"inserted": "<text>"}`）を通じてこのセッションの tool 出力に露出した（`feedback_capture_secrets_dom_to_file_never_through_stdout.md` 違反）。**同一ターン内でパスワードを IG 側で rotate**（アカウントセンター→パスワードを変更、UIから native-setter JS で入力＝値は一切 print せず length のみ確認）し、`~/.cloak/ig-aiclips_world_hq2.json` を新パスワードで上書き。以後 `insert` は OTP 等の使い捨てコードのみに限定し、パスワード等の永続 secret は必ず native-setter JS（`.value` を print しない）で入力する。

### 状態（実測、誇張なし）
- `~/.cloak/ig-aiclips_world_hq2.json` created・LIVE・profile完成（chmod 600）。
- `~/.cloak/instagrapi-aiclips_world_hq2.json` は現在 **dead**（次回 `--live` 実行時に自動で作り直される想定、tier1が失敗すればtier2/3にフォールバック）。
- `clip-accounts.json` に新エントリ追加: `status: "provisioned_pending_live_post"`（**"ready" ではない** — live post 未証明のまま ready を名乗らない）。
- bio の Digistore link は **未設定**（有効な instagrapi session が無いと bio_step.py は書けない設計のため）。

### NEXT（次パスへの引き継ぎ）
1. 24h cooldown が明けたら（目安 2026-07-18 15:xx JST 以降）`instagrapi_post.py --handle aiclips_world_hq2 --port 9225 --live` を**1回だけ**再試行。成功したら直後に `bio_step.py --handle aiclips_world_hq2` で Digistore link を設定。
2. それでも同じ session churn が起きるなら、根本原因は「新規垢そのものの信頼スコア」と確定 → 既存の frozen 垢（`aiclips_world_hq3` 相当、warm_step.py の 3日 warmup 実績あり）に準じて **数日 warmup してから live post** する設計に倒す（ig-account-warmer skill を先に回す）。
3. secret を扱うあらゆる cdp.py `insert`/`eval` 呼び出しは、今後 native-setter JS（値を返さない・lengthのみ）に統一する（このファイルの上の教訓を general skill 側にも反映すること = `ig-account-create/SKILL.md` の Gotchas に1行足す価値あり、未実施）。

## v21 — 原則: 全ノード配線して1個ずつ観測(observe→fix→observe) 2026-07-17
- post 状況: 動いてない。@aiclips_world_hq2 は作成/login 成功したが投稿失敗(session churn + warmup不足)、24h cooldown(~07-18 15時)。
- Dais 原則: warm_step.py も loop の中身。provision→warmup→post→measure→reflect の**全ノードが実際に配線されて動くか、1個ずつ観測して直す**。「システムを作る→loop が job→我々は観測→壊れてたら直す→また観測」。
- 次の一手 = warmup ノードを配線して動かす: (1)warm_step.py がどう発火するか/warmup→ready 遷移の条件を map (2)@aiclips_world_hq2(status=provisioned_pending_live_post)を warmup 対象にする (3)session churn(browser web session と instagrapi device session が新垢で互いを無効化)を直す=posting/warmup 中は片方の session に統一 (4)warmup 1パス実行して観測。
- 各ノードを個別に verify: provision✅ / warmup(要配線) / post(churn+warmup待ち) / measure(#3) / bio(#2) / reflect。

## v22 — session churn 真因確定 + 修正設計（explore 実測 2026-07-17）

### 真因（3つの構造的穴）
1. **session churn**: 同一 IG 垢に「instagrapi mobile device session(投稿)」と「browser web session(session_vault_tick.sh が30分毎に warm + warm.py が生成)」の**2認証系統が並行して生きる**。新垢は信頼スコアが低く IG が「不審な同時 session」と判定→数秒で両方 invalidate。frozen 世代(world_hq/hub_hq)は3日 warmup で ready になったが、production 投稿の成功ログは**皆無**（真に post 可能だったか未検証のまま freeze）。
2. **孤児 status**: @aiclips_world_hq2 = `provisioned_pending_live_post`。warm_step.py は `status=="warming"` のみ、run.sh は `"ready"` のみ拾う → どちらのループにも入らず一度も warmup されない。
3. **昇格バグ**: warm_step.py の warming→ready 昇格は `log[-1].day>=3` だけ見て `aborts`(login失敗)を無視 → world_hq が login 失敗直後に day3 で誤 promote された実測。

### 修正設計（1垢=1 session system に統一）
- **統一方針**: signup(browser)完了後は、その垢を **instagrapi device session だけ**で運用。browser は signup 後に閉じ、session_vault_tick.sh / warm.py の browser-warm 対象から外す。warmup も instagrapi の read(get_timeline_feed/get_reels_tray/たまに like)で行い、browser を張らない → 2系統の並行が消え churn 解消。
  - 実装: clip-accounts.json に `session_owner:"instagrapi"` フラグ。session_vault_tick.sh の jq フィルタ(`select(.status=="ready" or .status=="warming")`)に「session_owner!=instagrapi」除外を追加。
- **孤児 status 修正**: `provisioned_pending_live_post` を warmup 対象にする。ただし browser warmup でなく instagrapi warmup に載せる（上記統一に合わせる）。status 遷移: provisioned → warming(instagrapi read で数日) → ready。
- **昇格バグ修正**: warm_step.py の昇格判定に「最新 aborts が最新 log より新しければ昇格しない」ガードを足す。
- **cooldown 注意**: tier3 24h cooldown(~07-18 15時)明けまで instagrapi password relogin 不可。それまでは settings(既存 device session)で read を試す。

### #23 の実装単位（observe→fix→observe）
(a) session_owner フラグ + session_vault 除外（churn 解消）(b) instagrapi ベース warmup ノード（browser 不使用）(c) warm_step.py 昇格バグ guard (d) @world_hq2 を warming に載せて instagrapi read で warmup 開始 → 観測。各々 verify。

## v23 — 真因の核心: golden session を殺すな、relogin=bloks（実測 2026-07-17）
- 実測: churn 修正後、@aiclips_world_hq2(fresh 垢)の instagrapi device session は既に死んでおり(LoginRequired)、clean relogin を試すと **ChallengeRequired(bloks native checkpoint)** = aiclipsvault と全く同じ。
- ★真因の核心★: signup 直後の最初の login(=golden session)は通る。だがその session が一度死ぬと、password relogin で必ず bloks が出て垢が semi-poison 化する。= **「最初の session を永遠に生かし、relogin をゼロにする」ことが全て。死なせた瞬間に relogin→bloks で詰む。**
- 我々の失敗の連鎖: churn(browser+device 並行)で golden session を殺す → relogin を試す → bloks → 垢が semi-poison。aiclipsvault も world_hq2 も同じ経路で焼けた。
- 含意: (1)垢作成は churn 修正が入った状態でやり、golden session を最初から死なせない (2)keepalive は「死なせない」ための最優先機能(get_timeline_feed read、relogin 封印) (3)一度でも死んだら relogin でなく**新垢に置換**(self-heal、relogin で bloks を招くより早い)。
- 進行中: 成功してる長期運用 IG bot の**実コードを読む**深い検索(session を月単位で生かす実装、relogin 回避、churn 対策、device/proxy 一貫性)。結果を v24 に反映。

## v24 — 成功IG botの実コードから学んだ session 永続実装（copy元付き 2026-07-17）
出典=実コード読解: alsk1992/instagram-ai-agent(plugins/ig.py,device.py,human_mimic.py)+subzeroid/instagrapi(mixins/auth.py,challenge.py)。
1. 強制relogin無効化: session_refresh_days=0。relogin は LoginRequired 時のみ1回まで(2度目BadPasswordで7日freeze)。copy=ig.py L297-318 + auth.py L779-786。
2. keepalive2段: get_timeline_feed 定期probe + gentle_ping(launcher/sync 直叩き)。copy=ig.py L1142-1250。
3. device UUIDs永久固定(rotateでchallenge)。copy=device.py。
4. gold standard login: full cookie→set_settings()で/login 0回。copy=ig.py L556-708。
5. client rotation≠relogin: TCP接続だけ2-4hローテ、loginしない。copy=human_mimic.py L192-206。
bloks=avoid一択。食らったら垢死、蘇生せず新垢置換(self-heal)。#12/#4=login_resilientを上記に置換。

## v25 — MEASURE/REFLECT/BIO/telegram/dashboard の現状と欠落（deep read 2026-07-17）
### 動いてる
- MEASURE(views/likes): clip_pass.sh の LLM+CDP sub-call が直近3リールを目視→clip-metrics.jsonl。$ は measure_dollar.py あるが未呼出+Digistore key 未設定=死。
- REFLECT: imitate/optimize phase を reflection.jsonl に。LEARN=★良い例学習 実装済★(競合5アカ outlier scout→playbook.json、hook/thumbnail/retention 等7カテゴリ+source URL、tier core/candidate)。現 phase=imitate。
- BIO: offer.json の affiliate_link を profile external_url に sid1 付きで(冪等、TIER1限定)。
- Telegram: `~/anicca/skills/_shared/send-telegram.sh`(chat_id 8547730585)。clip run.sh が POST後 reel link を送信。
- copy元: producer.sh=github SamurAIGPT/AI-Youtube-Shorts-Generator を clone。clip_pass.sh=Reflexion論文パターン(gig_pass から)。clip-cli=Sutando パターン。
### 欠落（Dais の狙い = metrics通知 + dashboard + metrics/例で self-improve）
1. metrics→Telegram 未配線: reel link だけ送られ、views/likes/revenue_usd は送られない。
2. 全アカ横断 realtime dashboard 不在: ~/anicca-rtdash は別物(anicca iOS repo)。colony-status.sh/telemetry-collect.sh は3AI wallet集計で clip IG metrics 対象外。clip 単体は monitor.sh(CLI)のみ、UI無し。
3. measure_dollar.py が clip_pass.sh から未呼出(docstring自身が未配線と明記)+Digistore key 未設定。
4. evaluator.py/weekly_compare.py(自己スコア週次比較)が weekly_report.py CLI にあるが cron 未配線。
5. metrics pipeline が静かに壊れる履歴(reflection.jsonl に「pipeline broken」複数)、自動 self-heal 無し。
### 次 = /superpowers:brainstorm で設計（SDD→TDD→VDD）。対象:
metrics(views/likes/$)→Telegram 定期通知 + 全アカ(clip/gig/trade)横断 realtime dashboard(1画面) + measure_dollar/$ 配線 + self-score週次自動 + pipeline self-heal + 良い例学習の強化。既存(send-telegram.sh/playbook.json/monitor.sh)を土台に。

## v26 — churn修正済みの新垢でも初回ログインでbloks（真因の再考、実測 2026-07-17 18時台）

### 実測
- #12(login_resilient置換, commit e1f487f9まで)マージ後、task #2として @aiclips_world_hq2 の golden session tier1(--keepalive) を試すも死亡(feed_ok:false)確認 → 戦略(B)に従いfresh垢を**churn修正が完全に効いた状態で**新規作成。
- 新垢 **@aiclips_daily_hq** をig-account-createで作成: 0電話/0captcha、Gmail plus-addr、OTP gog gmail経由、profile(icon+bio)設定済み(setup_profile.py verify bio=True avatar=True)。★v22の修正を全て適用★: signup直後にbrowser tab/context即クローズ、clip-accounts.jsonにsession_owner:instagrapiを**作成と同時に**設定(browser-warmを一度も経由させていない)。
- それでも **instagrapi login-once(tier3、初回ログイン)が即 bloks ChallengeRequired**。code側のmark_poisoned()が自動発火し、clip-accounts.jsonのstatusを`poisoned_manual_backup`に自動降格(poisoned_reason: "tier3 login ChallengeRequired: challenge_required")。tier3 24hクールダウンは正しく機能(2回目の診断実行は正しくrefuseされ、IGへの二重打鍵にはなっていない)。

### 含意（v23の核心仮説の一部否定）
- v23は「signup直後の最初のloginは必ず通る、死んだ後のrelogin だけがblocksを誘発する」としていたが、**今回は真に最初のloginそのものがblocksになった**。churn(browser+instagrapi並行session)が原因という説明では説明できない — churnを完全に断っても初回で死んだため。
- 同日中に同一マシン/同一residential IPから **3垢連続作成**(aiclipsvault[経緯は別]、world_hq2、daily_hq)。IGの自動化対策は「session挙動」だけでなく「同一IP/デバイスフィンガープリントから短時間に複数アカウントが作られている」こと自体を検知しているのが濃厚な仮説 — 短時間の複数account creationがIP/device reputationを枯渇させ、後続アカウントのlogin自体を即challengeに落とす。
- 対応: (1)このマシン/IPからの新規IG垢作成を**当面停止**(4垢目を今すぐ作ってもほぼ同じ結果になる可能性が高く、かつresidential IPの評判をさらに悪化させてDaisの日常的なIG利用にも影響しうる) (2)代替: 数日〜1週間空けて1垢ずつ作る/別の residential IP(別ネットワーク)を検討 (3)aiclipsvaultの手動投稿バックアップ運用を当面の主経路として維持。

### 状態
- @aiclips_daily_hq: status=poisoned_manual_backup（自動降格済み、settings fileは一度も保存されず=golden sessionは一度も確立していない）。
- 今回のtask #2は「fresh垢での投稿1本」を達成できずクローズ。次回このtask を再開する際は、まずこのv26の含意（IP/device疲弊説）を検証してから再度account creationに入ること。

### 決着（2026-07-17 team-lead確認）
team-lead側の独立したscale research(`docs/earn/ig-account-scale-best-practices.md`)も同じ結論(同一IPからの短時間複数垢作成が最大の死因、per-account bugではない)に到達済み。task #2は「IP評判が焼けたためblocked、クリーンな別residential/mobileプロキシIPが必要」として正式クローズ。無料datacenterプロキシはIGがブロックするため不可、別エージェントが安価な実用プロキシを選定中。**プロキシIPが配線されるまで、このマシン/IPからのIGアカウント新規作成・既存アカウントへのログイン試行は一切禁止**。

## v27 — 統合診断 + roadmap（team-lead、2026-07-17 セッション末）

### 確定した真因（3研究 + live 実験で三重に裏付け）
投稿ゼロ（07-14以来）の真因は「session 実装のバグ」ではなく、優先順に:
1. **共有 IP（全垢 + Dais 個人が1 residential IP）** = 最大の死因。同日3垢連続作成で daily-driver IP が burned。churn 修正フル適用の daily_hq でさえ初回 login で即 bloks（v26）。instagrapi 公式「one account per stable proxy/IP」「BadPassword = clean で stable な network identity が要る」。
2. **warmup 無しの day-1 投稿** = 「1ヶ月未満の垢は強く flag、fresh 垢の automation は challenge を招く」。
3. **relogin/churn** = **#12 で解決済**（golden session 再利用・relogin 廃止・device uuid 固定、公式「session 永続で challenge の 9/10 が消える」）。

### 完了（このセッション）
- **#12 login-once hardening = 完了・LIVE**（main merge+push、51 passed）: keepalive 2段（probe が bloks を握り潰さず propagate）、--keepalive mode、tier1 cookie 永続、session_vault_tick が instagrapi-owned 垢を keepalive。
- **#24 cdp.py pw stdout 漏洩 = 修正済**（insert が char count のみ返す、test green）。
- research 2本 MD 化 push: `ig-account-scale-best-practices.md`（proxy/PVA/warmup/Graph/registry）+ `profitable-claude-clip-loop-migration-plan.md`。

### cold の2種（重要な区別）
- **inactivity で cold**（session 切れ、未 challenge）→ 再ログイン/warmup で復活可。
- **bloks/challenge で cold（poisoned）**→ 復活不可、突破ツール無し（gh 0件）、新垢置換のみ。我々の3垢は全部これ。

### roadmap（優先順、投稿再開への唯一の道）
1. **clean な別 proxy IP**（#9）= 唯一の残り blocker。無料 datacenter（proxifly 等）は IG block で不可、悪化する。調査中: 携帯テザリング+機内モード toggle の**無料 mobile IP**（CGNAT で ban 不可、IG 最高信頼）が free unlock かを実検証中。ダメなら最安 paid mobile/residential。★proxy 購入は金がかかるので額を Dais に確認★
2. **warmup フェーズ**（#10）= 新垢は Warming→数日 read-heavy→Ready→post。day-1 投稿を廃止。ig-account-warmer skill 活用。
3. **1垢を clean IP で durable poster 化**（#2、#9 待ち）→ queue の reel 18本から投稿→IG 実在確認。
4. **account registry を実 schema 拡張**（instafarm/GainLike 由来: status/warmup_day/proxy_id/device_id/health/last_post…）→ 100s 垢 fleet dashboard（#7）。
5. **#25 lifecycle 自動配線** = ready 垢なし→自動で(warmup 経由の)新垢→post を loop 自身に。
6. **profitable-claude 単一 repo 化**（#8）= clip loop を PC repo に copy+path 直し（既に正しい launchd 形、`ig-account-scale-best-practices.md` の manifest 参照）。openclaw 削除。

### 掟（このセッションで確定）
- proxy IP 配線まで、このマシン/IP からの IG 垢新規作成・login 試行は一切禁止（Dais 個人 IG IP 保護）。
- vcsdd/adversary subagent は使わない（Dais が単語を言った時のみ、global CLAUDE.md に焼済）。検証は自分で実テスト。

## v28 — proxy 発注中 + 並列化戦略（2026-07-17）
- clean IP 決定: Dais 認可「crypto 優先→ダメなら $7 カード、cred 全部渡済」。proxy-acquire が residential proxy 購入中($15 hard cap、ASN で datacenter でない事を検証、cred は ~/.cloak/proxy-clip-1.json 600perm 直結)。取得後: CloakBrowser + instagrapi に per-account 配線 → 1垢を専用IP固定 → warmup(#10) → queue の reel 18本から投稿(#2)。
- ★クラウド = 無料 no-IP は嘘★(scale 研究 doc `ig-scaling-architecture-and-economics.md` commit b2e389a25)。cloud VM は datacenter ASN で IG 即拒否。compute の場所と IG egress IP は別レイヤー。cloud を使うなら residential/mobile proxy を前段に置き cloud IP を IG に触れさせない構成のみ可。1:1:1(account:proxy:profile)が数百まで、それ以上は mobile proxy farm + device farm。100垢≈$200-500/月、1000垢≈$1.5-3k/月、free at scale は神話。
- ★並列化: エンジンは2半分★ = (1)DISTRIBUTION(垢/投稿側、今 proxy で blocked)と (2)CONTENT(動画/slideshow 生成、IP 問題と無関係=並列可)。CONTENT は proxy を待たず作れる(queue に reel 18本既存)。carousel 生成・他 content type・PC 移設・dashboard/registry は proxy と独立に並列進行できる。

## v29 — clean IP インフラ完成 + signup 実証（2026-07-17 実行、team-lead 自身が実行）
★共有 IP 焼けの blocker を解決した★:
1. **proxy 購入済・検証済**: IPRoyal residential sticky(geo.iproyal.com:12321、exit 87.19.19.64 = Telecom Italia ADSL = 本物 residential、datacenter でない事を whois で自分で確認)。$7.42 crypto(franklin1 self-funded Solana wallet、on-chain tx 3Q3bps… 確定、Dais のカード不使用)。creds=~/.cloak/proxy-clip-1.json(600perm)。
2. **instagrapi proxy 配線済(commit)**: `account_proxy_url`/`apply_proxy` が clip-accounts.json の `proxy` field から set_proxy、全 IG 通信を residential IP に通す。cred は echo しない。51 tests green。
3. **proxy browser launcher(commit)**: `launch_proxy_browser.py` が CloakBrowser を residential proxy 経由で起動(port 9233、profile clip-proxy-1)。exit IP を in-browser で 87.19.19.64 と検証済。新垢を clean IP 上で作れる。
4. **signup 実証(commit `ig_signup_proxy.py`)**: :9233(clean IP)で emailsignup を end-to-end 駆動成功 — cookie modal dismiss → 全 text field を TRUSTED typing(insert_text)で記入(native-setter は React state に commit されず re-render で消える=重要 gotcha) → DOB combobox(clickxy) → 送信 → OTP 画面到達 → IG が code 送信、まで全部動く。
★未完(タイミング問題のみ)★: 最初の pass で DOB/form 格闘に 30分かかり **OTP(547082)が失効**(IG code は~30分で expire)、resend が新 code を生成せず。=垢はまだ live でない。**残り = clean な FAST な signup pass 1回**(cookie→fill→DOB→submit→OTP を数分で。gotcha は全部 ig_signup_proxy.py に encode 済)。次に垢 live → clip-accounts.json に proxy 割当 → instagrapi login-once(proxy 経由) → warmup → queue の reel 投稿。

## v30 — 垢作成を subagent 化 + 並列 agent /goal 配布（2026-07-17）
- Dais 承認により垢作成は subagent 委譲（clip-account-create、Sonnet）: :9233 の clean proxy browser 上で ig_signup_proxy.py の gotcha 全適用（cookie先/trusted typing/DOB は inline or 2画面目の両対応/OTP は submit 後数分以内）→ 垢 live → clip-accounts.json に proxy 割当+session_owner=instagrapi → instagrapi login-once(proxy 経由 dry)で login-ok 検証 → golden session 保存。Done=ログアウトで垢ページが開ける + get_timeline_feed True。★clean residential IP 上で bloks が出るかが最終検証点（出たら major finding）★。
- IG signup フローは A/B variant あり（DOB が inline のことも、email/pw/name/user 送信後の2画面目のことも）。両対応を subagent prompt に明記。
- 並列ワークストリーム4本の /goal を Dais の Gmail に送付（clip 配信=main session、独立=動画量産/carousel/capafy/PC移設）。capafy はこの clip SSOT には無い（別 earn loop、PC earn loops spec 側 + 並列 Agent3）。

## v31 — ★MAJOR: clean residential IP でも phone wall★（2026-07-17 live signup、subagent 実測）
clean residential IP(87.19.19.64 Telecom Italia、in-browser で exit 検証)上で signup を CAPTCHA まで突破したが **携帯電話番号の必須認証(IT +39、SMS/WhatsApp、skip 無し)** に到達。=2026-06-29 の @aiclipsvault email-only 成功と矛盾。IG が厳格化 or この IPRoyal IP(freshly-bought、shared Italian)の評判。研究が予言した **PVA(phone-verified account)が scale で必須** の裏付け。
実測した signup gotcha(全て記録):
- DOB combobox は **aria-label("年を選択")** で match(title でない)。ig_signup_proxy.py 修正済(aria-label||title 両対応)。
- OTP は SPAM 着、email SUBJECT に "NNNNNN is your Instagram code"、~30分で失効。
- CAPTCHA = facebook.com/captcha/tfbimage の歪み文字(Arkose/Turnstile でない)。**CapSolver ImageToText は誤読(377048 を "37-8=?" と 0.91 で誤答)** → 手読み/vision or digit-OCR が要る。入力欄は `<textarea>`(input でない、querySelectorAll('input') 空)。
- phone wall の後は skip 無し = paid real-SIM OTP(5sim/SMS-Activate、reputable。無料 throwaway は IG が範囲 blacklist)が必須。
→ **account 作成コスト = proxy($7/1GB) + SMS($0.1-0.5/番号) per account**。fleet 経済に反映。次: paid real-SIM で phone wall 突破 → 垢 live → login-once(proxy) → warmup → 投稿。aiclips_daily_hq2 は phone 画面で待機(status=blocked_phone_wall、:9233 tid 6B50…)。

## v32 — 5sim PVA 突破中 + /loop 監視（2026-07-17）
- clip-account-create subagent が phone wall を 5sim(paid real-SIM)で突破中。5sim-account.json 作成済(signup 完了)、crypto funding + IT 番号取得の段階。突破後 aiclips_daily_hq2 を live→登録→login-once(proxy)→初投稿。
- account 作成の実フロー(全 gate)= proxy(clean residential) → email signup(Gmail plus, trusted typing) → email OTP(gog gmail, SPAM) → 画像CAPTCHA(手読み/vision、CapSolver 不可、textarea) → ★phone(paid real-SIM OTP)★ → live。1垢コスト = proxy$7/1GB + SMS$0.2。
- 並列 agent(動画/carousel/capafy/PC移設)の /goal は Dais Gmail に送付済。main session が clip engine を駆動、/loop で全 agent + 垢状態を定期監視。

## v33 — IG 垢作成 repo 探索の結論（no magic bullet、instagrapi が土台）2026-07-17
ig-creator-repo-hunt(gh+crwl)の結論: proxy+email+CAPTCHA+SMS を全部無人自動化する魔法 repo は存在しない。最良 = **subzeroid/instagrapi**(6485★、2026-07-16 push、Python)。browser でなく IG mobile API プロトコルを直接叩く:
- signup() に check_phone_number + send_signup_sms_code + challenge_code_handler 内蔵。signup_caa_email() で email。captcha_resolve() フック。
- 我々が書くのは callback のみ: email OTP=gog gmail / SMS OTP=5sim callback / CAPTCHA=CapSolver。IG プロトコル層はメンテナ任せ = DOM 格闘卒業。
- ★caveat: selfie captcha / bloks redirect は公式に突破不能(手動)。SignupSpamError 残存(大量登録 spam 判定)。tfbimage 型 CAPTCHA を CapSolver で解けるか未検証(汎用 OCR は失敗歴)。★
- ★scam 警告: selsabil-webdev/Automation-Studio-Instagram-Toolkit = 悪性(難読化 JS リダイレクト+偽コミット bot)。踏むな。★
- 却下: CoderNamaste/Instagram_Web_Gen(captcha/phone 0ヒット、自前と同じ制約)、zile42O/instagram-generator(2023 死亡、sms-activate 連携の参考のみ)。
戦略: (今)browser 経由で aiclips_daily_hq2 を 5sim で live 化→初投稿。(scale)instagrapi signup()+5sim callback+CapSolver glue を skillify。実装小(番号購入API→poll→callback)。
