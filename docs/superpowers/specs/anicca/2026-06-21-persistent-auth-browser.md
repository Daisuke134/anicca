# 永続認証ブラウザ基盤 — login once, agent reuses forever, no creds, no human-in-loop

Dais vision (2026-06-21): Dais が headed ブラウザで1回手動ログイン → cookie/session 永続 → Anicca が同プロファイル再利用（creds 不要・再ログイン不要・bot block 回避＝既存 cookie を使うだけ）。詰まったら Dais が画面で1タップ → Anicca 継続。これが freee/Stripe/法人口座 + **Postiz($49)置換（YouTube/IG/TikTok を browser 投稿・account作成+warmup+投稿）** を全部 no-human-loop 化する基盤。

## 核心パターン（標準・確実）
headed + 永続プロファイル(userDataDir/sessionKey) で起動 → 人間が手動ログイン（Google/Stripe/freee/social）→ 永続 → エージェントが同プロファイル再利用。**bot block は「自動ログイン」で発動するが、人間の手動ログインは通る → 以降エージェントは既存 cookie を使うだけなので block されない**。

## ツール評価（subagent a98b4d5c 最新2026検証）
| ツール | 永続 | ステルス | headed手動login | 結論 |
|---|---|---|---|---|
| camofox(Camoufox FF・:9377/:9378・既稼働) | storageState JSON(cookie+localStorage) | 最強 | `CAMOFOX_HEADLESS=false`(server.js:913) | 今日の即戦力・REST駆動・Google 1タップ handoff が標準フロー |
| **CloakBrowser**(CloakHQ・26.7k★・pip導入済 v0.3.30) | **真の永続 launch_persistent_context(user_data_dir)=完全Chromiumプロファイル(IndexedDB/SW含む)** | 最強(reCAPTCHA v3=0.9) | launch(headless=False)+**CloakBrowser-Manager(noVNC・Multilogin代替)** | **本命アップグレード** |
| agent-browser/playwright-cli | persistent context可 | 非ステルス→Google自動login弾く(実証) | 可 | 補助のみ |

runner-up: Patchright(patched Playwright). browser-use/Stagehand/Skyvern = agent orchestration層(browser を消費する上位、補完的)。

## 採用方針
- **今日**: camofox headed(:9378 daily-driver session)で Dais 手動ログイン → 永続 → Anicca 再利用。freee 即継続。
- **本命**: CloakBrowser 永続プロファイル + Manager(noVNC) を構築 → Dais が Google/Stripe/freee/YouTube/IG/TikTok を1回ログイン → 永続 → Anicca 全 no-human-loop。Postiz 解約($49/月節約)。
- belt-and-suspenders: Google OAuth は Firefox(camofox)が Chromium より通りやすい → 併用。

## freee の合成クリック問題の回避
freee React の法人形態切替が Anicca 合成クリックで永続しない（5方式失敗・各セクション保存ボタン必須＋商号未入力だと保存validation失敗で revert）。→ **headed 窓で Dais が法人形態=合同会社を実クリック（本物のonChange→正しく commit）→ Anicca が残り(商号/住所/代表/事業目的/資本金¥1)を継続**。決定値は #52 に全記録。

## 法人口座/登記の制度的時間（不可避）
登記=法務局1-2週、法人口座=登記完了後の履歴事項証明書必須。今日完成は制度上不可。並行で sunabar(個人口座 #53)が振込API実走の最速路。
