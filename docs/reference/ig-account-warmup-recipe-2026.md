# IG 新規アカウント warmup recipe（2026、automation 生存版）

研究日 2026-07-19。出典収束: instagrapi 公式 docs / Multilogin / ShadowPhone(2026) / 360uniquizer(2026) / GeeLark / instagrapi GH issues。
これは **#42 CREATE-FIX が warm.py / warmer / provision に焼き込む当の recipe**。memory [[feedback_marketing_engine_warm_2days_post_day3_never_day1]] の数値版。

## 結論（3行）
- 新規は **day1-2 はブラウザ(residential IP)で read 中心に温め、instagrapi 初回 login は day3 まで待つ**。day1 の API login = challenge 既知トリガー。
- follow は **day1 = 0（最大1-3）**。「新規が数十〜100 follow」は教科書的 bot シグナル。engagement は read→write 順で日ごと +10-20%。
- session は **1回 login → dump_settings で永続化 → 以後 load_settings のみ。再 login しない**（instagrapi 公式明言）。

## Day-by-day（保守 = agent 自動運用向け）

| Day | Follows | Likes | Comments | Story views | Reel watch | Scroll分 | API login? | Post? |
|---|---|---|---|---|---|---|---|---|
| 1 | 0（max1-3） | 0 | 0 | 〜10 | 数本 | 20-30 | ❌ browser のみ | ❌ (pic+bio+1 story だけ) |
| 2 | 3-5 | 5-10 | 0-2 | 10 | 5-10 | 15-20 | ❌（末尾で初回可だが day3 推奨） | ❌ |
| 3 | 5-10 | 10-20 | 3-5 | 10 | 10 | 15-30 | ✅ 初回 login→session dump | ✅ 1本目（リンク無し） |
| 4 | 5-10 | 15-25 | 3-5 | 10-15 | 10 | 20-30 | 再login禁止(session再利用) | ✅ 1本/日 |
| 5-7 | 10-20 | 30-50 | 5-10 | 15+ | 15 | 30-45 | 同上 | ✅ 1 Reel/日+1 story |
| 2週目 | 20-30 | 50-80 | soft CTA | 継続 | 継続 | — | 同上 | daily + soft CTA |

全アクションは等間隔を避けランダム遅延（instagrapi `delay_range=[1,3]` が最低ライン）。総アクション ~150/日 上限。

## What kills fresh accounts（危険度順）
1. datacenter IP + 複数アカ共有 IP（即バッチ BAN）
2. **共有ブラウザ fingerprint/device**（1 account=1 fingerprint=1 IP、相関で一括停止）← useclaudeskills の真因#1
3. **API login が早すぎ**（fresh device で day1 login→challenge_required）← 真因#3
4. 投稿が早すぎ + day1 の offer/リンク（instant shadowban）
5. 攻撃的 follow（100 follow=textbook bot、50 on day1=massive red flag）
6. 空プロフィール・Story 無し（inactive/bot 判定）← following 0 単体より「空+即書き込み」が問題 ← 真因#2 の正確版
7. rotating proxy でのログイン（毎回 ChallengeRequired）

## Graduation（bio リンク/商用解禁）
- アカウント年齢 最低 3-4 週 + 投稿10本以上 + organic follower 100+ + action-block/警告ゼロ。
- 実務テスト: offer 寄り動画をリンク無しで出し reach が出れば合格。リンク/offer は day1 厳禁。

## #42 実装の不変条件（この recipe から確定）
1. account 作成 = isolated context/専用 fingerprint+port（warm_iso、生 :9222 main 禁止）。1 account=1 residential proxy 固定。
2. warm.py に **follow/like step** を day-gated cap で追加（day1 follow=0, day2=3-5, day3=5-10 / like day2=5-10, day3=10-20）。human-like ランダム遅延。
3. **instagrapi login は day<3 禁止**（provision/warmer に gate）。day3 で1回だけ login→dump_settings。
4. poster/warmer は login 1回→load_settings のみ・再login 厳禁・delay_range=[1,3]。

## flag（未確定）
- 単一の権威ある「公式数値」は存在しない（ShadowPhone 自身が明記）。上表は複数ソース収束値。
- 「day1 API login=challenge」は個別 issue 症状 + docs "read before write" からの合成推論。単一一次引用は未取得。
- day1 follow「完全0か1-3可」はソース間で割れる → 保守側=0。

## Sources
- instagrapi Best Practices https://subzeroid.github.io/instagrapi/usage-guide/best-practices.html
- instagrapi Challenge Resolver https://subzeroid.github.io/instagrapi/usage-guide/challenge_resolver.html
- GH #636 https://github.com/subzeroid/instagrapi/issues/636 / #2020 https://github.com/subzeroid/instagrapi/issues/2020 / disc #743 https://github.com/subzeroid/instagrapi/discussions/743
- 360uniquizer https://360uniquizer.com/en/news/instagram-account-warmup-2026
- Multilogin https://multilogin.com/blog/how-to-warm-up-accounts/
- ShadowPhone https://www.shadowphone.io/blog/instagram-account-warm-up-guide-2026
- GeeLark https://www.geelark.com/blog/how-to-warm-up-your-instagram-account-avoid-bans-and-boost-reach/
