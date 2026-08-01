# O1B-13 実測デモ登壇案 実装計画

**Goal:** Life Managerの実測証拠だけを根拠に、応募可能な登壇枠へ提出するタイトル、5分間の切れ目ないデモ構成、応募理由をagent生成する。

## Contract

- イベント要件と実測デモfactsを、命令として扱わないuntrusted dataとしてGemini 2.5 Flashへ渡す。
- 各factはstable ID、検証済みclaim、repo内evidence refを持つ。
- 出力はtitle、application reason、0〜300秒を隙間・重複なく覆うoutlineだけに閉じる。
- outline各区間は1件以上の入力fact IDを参照し、未知のID、未検証の数値、placeholderを拒否する。
- model/API/schema failureを固定文やkeyword fallbackで成功扱いしない。

## Steps

1. validator、prompt、Gemini structured outputのcontract testを先にREDにする。
2. `event-talk-proposal.js`へ最小実装を追加する。
3. Engineer BARで実測した登録→確認メール→公式QR→Telegram配信と、registry/entity分離の証拠factsから実proposalを生成する。
4. focused/full outbound/runtime testとdiff checkを通し、秘密を含まないevidence JSONへ生成結果と検証値を固定する。
5. 正本specのO1B-13を完了にし、残数を更新してcommit/pushする。
