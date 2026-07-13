# 38 — SNS per-post メトリクス取得: 実測で確定した方式（2026-07-13）

**結論（先に）**: **instagrapi + CloakBrowser daily-driver(:9222) から抜いた `sessionid`** が我々の答え。
無料・Meta app 申請不要・ビジネス垢転換不要・今日から動く。**我々の実投稿で `plays=13` を実取得して検証済み**。
Postiz クラウドへの課金は不要（セルフホストも我々の用途には過剰）。

## 我々が必要な metric（Dais 2026-07-13 明示）
**per-post の views と engagement だけ。** reach/saves/website_clicks は不要。
→ この一文が設計を決定づけた。owner-only insights（Graph API）が要らないので、
   ビジネス垢転換も Meta app 審査も**全部スキップできる**。

## 実測ログ（全て本セッションの実出力。推測ゼロ）

### ✅ 採用: instagrapi + logged-in sessionid
```
LOGGED IN AS: anicca.affirms2 | pk: 43475841194 | is_business: False
  DarB2Qikt3d: owner=@anicca.affirms2 type=1/feed  likes=0 comments=0 plays=0  views=0
  DanlbElPLGr: owner=@aiclipsvault  type=2/clips likes=0 comments=0 plays=13 views=0
```
- `plays=13` が返った = **play_count は本物に読める**（後述の無認証時の 0 は「抑制された偽ゼロ」だった）
- sessionid は CDP `Network.getAllCookies` で daily-driver から抜く（**要 `suppress_origin=True`**。
  素で繋ぐと `403 Rejected an incoming WebSocket connection ... Use --remote-allow-origins`）
- **ライブラリ**: subzeroid/instagrapi（6.4k★、2026-07-12 更新）。`login_by_sessionid()` → `media_info()`
- **副産物の残酷な実測**: LM マーケ投稿は **本当に likes=0 / plays=0**。「投稿している」≠「見られている」

### ❌ 却下: instagrapi 無認証（public GQL）
```
DanlbElPLGr: media_type=2/clips like_count=0 comment_count=0 play_count=0 video_duration=0.0
RAW KEYS: [... 'play_count', 'view_count', 'like_and_view_counts_disabled' ...]   ← キーは在る
```
キーは返るが**値が抑制されて 0**（logged-in で 13 と判明したので確定）。**funnel をこれに載せてはいけない**。

### ❌ 却下: instaloader 無認証
```
JSON Query to graphql/query: 403 Forbidden ... [retrying]
OURS DanlbElPLGr FAILED: BadResponseException Fetching Post metadata failed.
NASA FAILED: ProfileNotExistsException
```
匿名 GQL が IG に 403 で塞がれている（2026-07 時点）。

### ❌ 却下: Instagram Graph API（公式）
公式docs（developers.facebook.com/docs/instagram-platform/insights、firecrawl 実取得）:
> "This API returns only data for media owned by Instagram **professional accounts**.
>  It cannot be used to get data for media owned by personal Instagram accounts."
- per-post insights は `GET /<INSTAGRAM_MEDIA_ID>/insights?metric=views,reach,likes,comments,shares,saved`
  で**確かに取れる**が、**professional 垢 + Meta app が前提**。我々の垢は `is_business: False`
- 我々は views/engagement しか要らない → **この申請コストを払う理由が無い**
- （将来 reach/saves が欲しくなったら初めて professional 化すればよい。今は不要）
- 制約メモ: `follower_count` / `follows_and_unfollows` / demographics は **フォロワー100人未満では返らない**
  → 新規垢では最初から使えない。ここでも Graph API は当てにならない

### ❌ 却下: Postiz セルフホスト（gitroomhq/postiz-app、AGPL、33k★）
- **セルフホストは無料**（クラウド課金は不要という発見自体は本物）
- `analytics` 実装は instagram / tiktok / x / youtube / threads / pinterest 等に**存在する**
  （`libraries/nestjs-libraries/src/integrations/social/*.provider.ts`）
- **しかし IG の analytics は アカウント単位**であって per-post ではない。実コード:
  ```ts
  // instagram.provider.ts:920 async analytics(...)
  fetch(`https://${type}/v21.0/${id}/insights?metric=follower_count,reach&...`)
  fetch(`https://${type}/v21.0/${id}/insights?metric_type=total_value&metric=likes,views,comments,shares,saves,replies&...`)
  ```
  = 結局 **Graph API のラッパ**。professional 垢が前提で、per-post ですらない
- 常駐サービス（DB+backend+frontend+worker）を増やすコストに見合わない → **却下**

### 参考: 他媒体（G5 で必要になった時に）
| 媒体 | 手段 | 状態 |
|---|---|---|
| TikTok | davidteather/TikTok-Api（6.5k★、非公式・無料） | 未検証。必要時に実測する |
| YouTube | Data API v3（無料クォータ、公開 statistics は API key だけで取れる） | 未検証 |
| X | free tier は read が実質不可。要調査 | 未検証 |

## 「他人の自己改善マーケloop」の調査結果（正直に）
`gh search` を複数角度で実行（"autonomous social media agent" / "ai influencer automation" /
"social media growth agent" / "content engine growth loop" 等）:
- **ヒットは全部 0〜7★ の個人プロジェクト**。真面目に回っている OSS の自己改善マーケループは**存在しない**
- 再利用できるのは**部品だけ**: Postiz(投稿)・instagrapi(読取)・MoneyPrinterTurbo(動画)・viral-hook-creator(フック)
- **ループ本体（変異 → 実測 → 採否 → 嘘の検出）は我々が組む**。ここに先行者はいない
- （memory `reference_graduation_economics...` の「既存の稼ぐOSSは全部vaporware」と一致）

## 実装仕様（growth-engine ④ metrics 回収に焼く）
```
skills/growth-engine/metrics_fetch.py
  1. CDP :9222 → Network.getAllCookies（suppress_origin=True 必須）→ instagram.com の sessionid
     ※ cdp_lock.sh の mkdir 排他を取ってから触る（daily-driver タブ規約: 複製/close 禁止）
  2. instagrapi Client().login_by_sessionid(sessionid)
  3. 各 post_id について media_info() → {plays, likes, comments, taken_at}
  4. funnel jsonl へ1行 append（post_id / 台本の変異 / 投稿時刻 / views / engagement）
  5. sessionid が死んでいたら → 数字を捏造せず CANNOT_VERIFY として報告（沈黙は違反）
```
判断（どの変異を採るか）は LLM。metrics_fetch は**決定的な bookkeeping のみ**（regex 判定を持ち込まない）。

## ★ V0-5: IG 診断可能性 実験の結果（2026-07-13 実測。REQ-012 Phase 2a の答え）★

**verifier は metrics とは別物**: 欲しいのは数字ではなく「**その投稿が本当に公開されているか**」。
よって **logged-out（cookie 無し）の instagrapi** を使う（logged-in で見ると shadowban/失敗投稿も
本人にだけは見えて偽 PASS が出る＝我々が殺そうとしている病気そのもの）。

### 採用シグナル = 固定公開面（プロフィール）のメンバーシップ検査
```
LOGGED-OUT instagrapi:
  user_id_from_username("anicca.affirms2") -> 43475841194
  user_medias_gql(uid, 12) -> ['DarB2Qikt3d', 'Daoa_TREugW', 'DanT6ChmUVC', 'DajR2tDjRyH']
  "DarB2Qikt3d"(実在) in codes -> True
  "ZZZZZZZZZZZ"(偽物) in codes -> False   ← ★陽性の矛盾証拠 = FAIL を出せる★
```
| ログアウトで観測される状態 | verdict |
|---|---|
| 固定公開面が開け、主張の post code が一覧に**在る** | **PASS** |
| 固定公開面は開けるのに post code が一覧に**無い** | **FAIL**（陽性の矛盾＝「投稿した」は嘘） |
| 固定公開面自体が取れない（例外/レート制限） | **CANNOT_VERIFY**（正直に「読めなかった」） |

→ 3値すべてが機械的に出る = **`automatedVerification: true` を IG に対して正当に立てられる**（gate が飾りにならない）。

### 却下した弱いシグナル
`media_info(code)` の単体呼び出し: 実在 → 構造化データ / 非実在 → `LoginRequired` 例外。
**差は出るが例外が曖昧**（レート制限でも同じ例外）→ これ単体では「削除された」を FAIL と断定できず
CANNOT_VERIFY 止まり。**FAIL を出すには固定公開面のメンバーシップ検査が必須**。

## 引用
- Meta 公式: developers.facebook.com/docs/instagram-platform/insights —
  「This API returns only data for media owned by Instagram professional accounts.」
- subzeroid/instagrapi (6.4k★) — 「The fastest and powerful Python library for Instagram Private API」
- gitroomhq/postiz-app (33k★, AGPL-3.0) — 「The ultimate agentic social media scheduling tool」
