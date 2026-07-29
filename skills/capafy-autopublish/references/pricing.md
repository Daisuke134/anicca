# Pricing rule (BP §4 v2 — SSOT)

外部有料API依存で mode を決める:
- 外部有料API無し(base LLMのみ)        → Run Online subscription（closed・recurring）★既定★
- 画像生成API(openai等)1-2回            → subscription、価格に+$2-3/週でAPI代回収
- 電話/動画大量レンダ/長時間Live(重API) → ①message cap付きsubscriptionで上限を切る ②それでも赤字 or 外部費用制御不能なら Download/BYOK(最終手段・稼げない前提)

価格:
- B2B生産性(deck/research/resume/data/SEO/金融) → $19.99-24.99/月
- コンテンツ量産(台本/SNS/poster/画像)          → $1.99-7.99/日 or 週
- Free Trial を必ず front door に付ける（trial quota 3程度）

黒字条件(実数): 週$5.99 × cap8/週 → 手残り $5.99×0.8=$4.79 vs 総コスト(API $0.12/回×8=$0.96 + sandbox $0.07/日×7=$0.49 = $1.45) ＝ **約3.3:1**。`(API/回×cap)+(sandbox$0.07×日数) ≤ cyclePrice×0.8/2` を満たすこと。cap40は赤字。
手数料: Capafy 20% / 初回$0.99認証 / Sandbox Fee $0.07/日(subscriptionのみ)。

mode/price は本ルールで推奨を出し、**人が最終承認**してから publish する。
