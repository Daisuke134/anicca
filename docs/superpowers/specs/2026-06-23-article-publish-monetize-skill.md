# SPEC — ai-entity-article-writer を「書く→全媒体公開→収益化」フルskillにする (2026-06-23)

## Goal
1コマンド「この記事を公開して」で、JP+EN を全プラットフォームに、画像つきで、再ログイン不要で投稿し、収益化（メンバーシップ/有料/購読）まで載せる。毎日 no-human で回し、X/note/Substack で 10k MRR。Capafy で売れる形にパッケージ。

## 3層アーキテクチャ
```
ai-entity-article-writer (full skill)
├─ 1. WRITE   research→RUN→draft(JP)→gates→figures(Mermaid/表/gpt-image)   ← 完成済
├─ 2. PUBLISH 1記事 → 全媒体 × {JP, EN}                                    ← これを固める
│     orchestrator: publish-all.sh <md> <lang> → 各 platform publisher を順に叩く→URL収集→live200検証
│     platform publishers (各 idempotent・冪等・下書き→確認→公開):
│       note      : note-mcp + CloakBrowser daily-driver / 画像=アイキャッチ+本文S3
│       zenn      : git push (zenn-cli) / mermaid 直描画・画像=repo相対
│       substack  : /api/v1/drafts + 画像アップ
│       devto     : API key / 画像=URL
│       x-articles: wshuyi/x-article-publisher-skill (Playwright) / X Premium+
│       tiktok    : 画像1枚 (既存poster)
├─ 3. MONETIZE  platform別の収益化設定（1回set→継続）
│     note      : メンバーシップ(月額) + 有料記事(深掘り単発)
│     x         : 有料購読(Subscriptions) + tips
│     substack  : paid subscription (月額/年額)
│     → 無料で量と信頼を貯める → 継続課金(メンバーシップ/購読)= MRR エンジン
└─ 共通: 認証は CloakBrowser daily-driver (~/.cloak/profiles/daily-driver) に統一
```

## 認証統一（HARD RULE 0.39）
- 全 browser-publish は `launch_persistent_context("~/.cloak/profiles/daily-driver", headless=False, humanize=True)`。
- Dais が1回ログイン済 → creds は profile に永続 → **再ログイン不要・creds を知らずに全媒体操作・bot block回避**。
- camofox は fallback のみ。API があるもの(devto/substack)は API 優先、無いもの(note/x-articles)は CloakBrowser。
- 詰まり(captcha/2FA)→ headed なので Dais が画面共有(vnc://100.99.82.95)で1タップ → 継続。

## 冪等・安全
- 各 publisher は「下書き作成 → URL返す」をデフォルト（PHASE1: Dais 確認 → publish フラグで公開）。
- 二重投稿防止: `state/published-ledger.jsonl`（article hash × platform × lang × url）。既出はskip。
- 画像経路: Mermaid → kroki PNG (無料) を一時生成 → 各platformの画像アップに渡す。サムネ=gpt-image(chatgpt-imagegen web backend, 追加課金0)。

## 収益化（note 例・出典 note.com/monetization-guide）
4メニュー×2課金: 単発(有料記事/有料マガジン) / 継続(メンバーシップ/定期購読マガジン)。手数料 ~10%+決済~5-15%。
型: 毎日「役立つ無料記事」でフォロワー → メンバーシップ(月額)開設 = MRR。X/Substackも同型(無料で集客→有料購読)。
※メンバーシップ開設は note UI申請が要る(初回のみ browser, daily-driver で)。

## Capafy 化（売る）
- 公開版 = WRITE + PUBLISH エンジン（gates/figures/multi-platform poster）。
- 除外 = 我々の creds/profile/topic-queue/persona。買い手は自分の daily-driver と API key を挿す。
- サブスク型(我々のLLM鍵hosting) or Download買い切り の2モード（HARD RULE: capafy_publish_ritual）。

## タスク（順）
1. publishers を CloakBrowser daily-driver に統一（note→zenn→substack→devto→x-articles）。各 idempotent + ledger。
2. `publish-all.sh <md> --lang ja|en --mode draft|publish` orchestrator + live200検証。
3. EN 翻訳パイプライン（JP md → EN md、用語そのまま、de-slop EN）。
4. 収益化setup（note メンバーシップ → X 購読 → Substack paid）= platform別チェックリスト。
5. Capafy パッケージ（creds除外・README・値付け）。

## 受け入れ条件
「post this to note」→ daily-driver で下書き→画像綺麗→URL→Dais確認→公開、が1コマンドで通る。全媒体×JP/EN 同様。ledgerで二重防止。
