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
