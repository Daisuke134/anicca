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
