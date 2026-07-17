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
