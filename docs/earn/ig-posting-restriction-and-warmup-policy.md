# IG 投稿制限 と warm-up/cadence ポリシー（2026-07-14、FIX-1 で判明）

clip loop の「投稿が全部失敗」の真因調査で判明した、**若いアカウントの投稿制限**と、それを避ける warm-up/投稿頻度ポリシー。全 social loop（clip/video/slideshow）共通の運用鉄則。

## FIX-1 で実測した事実（俺が直接、@aiclipsvault port 9223 login済）
- queue clip を実投稿 → `outcome=failed / post_url=null`。profile 独立確認で新 reel 出ず = **本当に publish されてない**（H1）。
- 3ファイル（28MB原本 / 28MB faststart / **2.6MB/15s 軽量**）が **全て `シェア中` spinner で同一 hang**。= **コンテンツ非依存**。
- ❌ faststart(moov位置) 仮説 falsified。❌ size/尺 仮説 falsified。→ **ファイルは犯人でない。poster のコードも壊れてない**（flow は share まで正常到達、IG が publish を silently drop）。
- account: 作成~2週間、warming中、status "investigating"、12 reel 既存（過去は投稿できた）、最後の成功~10日前、以降全滅。

## 結論（最有力、断定はしない）
**aiclipsvault は Instagram の投稿制限（action-block / soft-ban）状態。** 若いアカが短期間に投稿を burst → 自動化検知(CDP) + warm-up 不足で flagged → publish が silently 握り潰される。web の「シェア中」永久 spinner はこの既知症状。

## 検索の裏取り（一次情報）
- action-block の症状: "your posts are still visible... What you cannot do is the specific action that triggered the block" — unfollr.com/blog/instagram-action-blocked
- 新規は徐々に: "New accounts should start slow and gradually increase activity over days or weeks to build trust" — socialrails.com/blog/instagram-bans-and-restrictions-guide
- 自動化検知: "Selenium/Puppeteer/Playwright set navigator.webdriver true... IP cross-referenced against spam/datacenter DBs" — undetected-chromedriver discussion #1878
- warm-up cadence: "Post once on day 5, then warm-only on days 6 and 7" — superwarm.co/blog/warm-up-instagram-accounts-for-automation
- human footprint: "upload manually from your phone and avoid automation initially, especially for AI channels" — shortsfaceless.com/blog/how-to-warm-up-your-social-media-accounts

## ★ポリシー（全 social loop に焼く）★
1. **投稿 cadence を絞る**: 新規は warm 7日後に **1日1投稿から**、週で 2→3 に漸増。burst 禁止。（大規模運用者コンセンサス）
2. **human footprint**: warm 期は視聴/スクロール/軽い like を混ぜる（ig-account-warmer は実装済）。cold なまま自動投稿を叩かない。
3. **CDP 検知の低減**: navigator.webdriver 等の指紋、住宅 proxy 固定（datacenter は弾かれる）。scale 時 steel-browser + 住宅 proxy。
4. **制限を食らったら**: そのアカを数日 休ませ、warm-only に戻す（削除でなく休養）。self-heal は「別アカに逃げる」でなく「そのアカを休ませて cadence を落とす」。
5. **isolation の再確認**: 1 acc=1 loop=1 proxy=1 fingerprint。使い回し厳禁。

## 次の切り分け（未実施、要判断）
- (a) 同じ動画を別アカ（既に投稿実績のある handle）で試し、code vs account を確定。
- (b) aiclipsvault を数日休ませ cadence 落として再テスト。
- (c) mobile app 経路で手動投稿し account 制限 vs web-composer を分離。

## 出典まとめ
unfollr.com / socialrails.com / superwarm.co / shortsfaceless.com / quso.ai / github undetected-chromedriver #1878
