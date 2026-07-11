# #8 LM Phase B（セルフマーケのみ: Reddit+IG × MoneyPrinterTurbo）— Evidence

正本: spec §8 #8（スコープ縮小 Dais 2026-07-11: セルフマーケのみ、issue-driven OFF）。Done=実投稿URL≥1 + marketing-actions.jsonl 実測行。

## ✅ 完了（profitable-claude main 7629c92 merged+pushed）
builder 実装 → merge。issue-driven dev は OFF（STEP1/2 skip）、STEP3 を「planning のみ」から**実マーケ実行 + logged-out 検証必須**に書換え。

### 実投稿 URL（Done bar）
- **Instagram（logged-out 検証済＝Done 達成）**: `https://www.instagram.com/anicca.affirms2/p/Daoa_TREugW/`。CloakBrowser daily-driver(CDP:9222)で投稿、**cookie無し camofox で公開表示を確認**（本文+author 描画、IG 標準の logged-out signup gate のみ＝blocked/removed でない）。account=anicca.affirms2（既存 warmed、専用 LM IG account が無く off-persona tradeoff を disclose）。
- **Reddit（Done bar 不達だが重要発見）**: `old.reddit.com/r/selfhosted/comments/1us4i8v/.../owsv67g/`。投稿は account に live だが、**fresh 無認証 camofox で当該コメントも過去4件も見えない＝Reddit が低karma(=1) account を shadow spam-filter**。→ **reddit-loop は過去1週間 公開インプレッションほぼゼロ**だった（成功に見えて実は不可視）。honest に `posted_but_not_publicly_visible` 記録。

### marketing-actions.jsonl 実測行
2行記録（IG: action=posted, views/clicks=none:not-yet-measured, signups=0 / Reddit: action=posted_but_not_publicly_visible, views=none:shadow-filtered）。各行に verification フィールドで検証方法を明記。

### 一次 copy
「Tired of searching travel time for every event? Life Manager fills it in automatically」（Dais 指定）。creative=lm-wedge-card（MoneyPrinterTurbo 未 install のため Pillow 静的カードで代替、cli に MPT 優先を明記）。

## 残（正直）
- **signups/売上 = 0**（正直報告。導線は出したが誘導実績はこれから）。
- views/clicks 実測は次 pass 以降（marketing metrics pass）。
- **Reddit shadow-filter は self-heal/self-improve への実 signal**（reddit-loop の north-star が実は未達だった＝§11 IMPROVE の材料）。
- MoneyPrinterTurbo 本体の stand-up は未（harry0703 fork、~/MoneyPrinterV2 は別物）。
- issue→deploy 1周は Dais scope で OFF のため対象外。
