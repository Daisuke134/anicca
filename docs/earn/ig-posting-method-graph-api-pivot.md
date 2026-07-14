# IG 投稿方式の方向転換 — web composer は死に筋、Graph API へ（2026-07-14）

clip loop が「投稿できない」問題の**根本原因が判明**。犯人は python でもアカ休養不足でもなく、**投稿手法そのもの**。検索(crwl 一次情報)で確定。

## 症状（実測、俺が直接）
- post_reel は upload+caption+share まで正常到達（screenshot 6-sharing.png で「シェア中」spinner 実見）。
- share 後、reel が publish されない。aiclipsvault×3 + world_hq×1、全部 240s 待って新reel無し。独立読取(cache-bust)でも新reel無し。
- 3種のファイル(28MB/28MB faststart/2.6MB)全て同一 hang = コンテンツ非依存。
- = python/composer バグでも verify 誤判定でもない。IG が share を受けて publish を **silently 拒否**。

## 根本原因（検索で確定）
**desktop web(instagram.com)の Reel 投稿機能自体が構造的に不安定 + 自動ブラウザ + 新規アカ = bot 検知の silent reject**。
- "on a laptop, the reel upload is just a spinning wheel, nothing more"（VideoProc/Reddit、非自動化ユーザーですら発生）
- "Upload fails or gets stuck" を web composer の既知欠陥として明記、Meta Business Suite / 3rd-party を推奨（posteverywhere.ai）
- "silent flags... users don't know what went wrong"（botpenguin、新規/自動化疑いに対する無言フラグ）
- Brandwatch: 素の web は元々 Reel 非対応の後付けで脆い。

→ **desktop web composer 経由の自動投稿は本番デッドエンド。恒久採用しない。**

## 解決策（信頼性順、出典付き）
| 順 | 方法 | 根拠 | 制約 |
|---|---|---|---|
| 1 | **Graph API (Content Publishing)** developers.facebook.com/docs/instagram-platform/content-publishing | 公式、100投稿/24h(`GET /{ig-id}/content_publishing_limit`で実測)、silent drop 無し | Business アカ必須(Creator不可)、FB Page 紐付け、`instagram_business_content_publish` の app review 2-4週 |
| 2 (繋ぎ) | **upload-post.com** (app-review 済 managed) www.upload-post.com/how-to/automate-instagram-posts | 同じ Graph パイプライン、shadowban リスク無し、無料10件/月、審査不要 | Business/Creator+FB Page は要 |
| 3 | **instagrapi** github.com/subzeroid/instagrapi (6.5k★, 2026-07-12更新) | clip_upload() で Reel、現役 | 開発元「本番非推奨、公式API推奨」。既知バグ Issue #2263 |
| ✗ | desktop web composer (現行 CloakBrowser CDP) | — | デッドエンド |

**共通前提**: IG アカを Business/Creator 化 + FB Page 紐付け（1回のアカ設定、自動可）。

## 方向転換（投稿アーキテクチャ）
```
 旧(死に筋): producer → clip → CloakBrowser で web composer → silent 失敗
 新(確実):   producer → clip → Graph API(直 or upload-post) → 確実 publish
             前提: アカ Business化 + FB Page 紐付け
```

## 実装計画（新タスク CLIP-POST-11）
1. aiclipsvault を Business/Creator 化 + FB Page 紐付け（browser で1回設定、no-human）。
2. 繋ぎ = upload-post.com 無料枠で Reel を1本 E2E 投稿し、silent 失敗せず公開されるか実測。
3. 本命 = Graph API 直叩き（app review 申請 → 承認後、producer→Graph API 配線）。
4. run.sh/post_reel の web-composer 経路は fallback に降格（恒久採用しない）。
5. warm/cadence/proxy 対策(FIX-1)は継続（Graph API でも新規アカの信頼構築に効く）。

## 出典
videoproc.com/resource/instagram-video-upload-stuck.htm / posteverywhere.ai/blog/how-to-post-instagram-reels-from-desktop / brandwatch.com/blog/post-to-instagram-from-pc / botpenguin.com/blogs/what-is-instagram-automated-behavior-and-how-to-fix-it / developers.facebook.com/docs/instagram-platform/content-publishing / upload-post.com / github.com/subzeroid/instagrapi / postproxy.dev/blog/instagram-reels-api-publishing-guide
