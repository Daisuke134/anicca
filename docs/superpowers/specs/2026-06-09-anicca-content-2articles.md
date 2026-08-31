# Anicca Content — 2 articles (today) + uncertainties + full UX TODO

| Field | Value |
|---|---|
| Date | 2026-06-09 |
| 媒体 | note / Zenn / Substack / Dev.to / X articles (5箇所) |
| 型 | draft=Anicca/私 → Dais=editor 往復 → publish |
| positioning | 「自己資金AI media + 当事者」 |

## 記事 1 — Anicca の旅 + 4者比較 (= 横断、 我々の挑戦)
**タイトル(JP)**: 「$25万稼ぐAIと$0のAI — 自律で金を稼ぐAI4体を解剖して、世界初のOSS自己資金AIを作る【公開実験 Day 1】」
**タイトル(EN)**: "One AI made $250k. Another made $0. We dissected 4 self-earning AIs to build the first open-source one that pays its own bills."
**body 構成**:
1. フック: 「AIが自分のサーバー代を自分で稼ぐ時代が来た。 でも 殆どは 嘘か $0」
2. 我々の失敗告白: 壮大spec + dry-run で $0 だった (= 共感、 正直)
3. ★ 4者 比較表 ★ (Felix/automaton/sutando/Anicca — 実収益/human/受取rails/売る機構/複製/OSS)
4. 各者 1段落 解説 (一次ソース: Felix listing, automaton issue#300, sutando README, Vending-Bench)
5. ★ Anicca の差別化 ★: 4者で唯一 ①Felix engine ②no-human+複製+自wallet ③人生管理 ④OSS自己資金
6. 設計 ASCII (heartbeat: think→build→sell→自wallet受取、 Dais=0)
7. CTA: クラウド aniccaai.com/install / ローカル github.com/Daisuke134/anicca / 連載予告

## 記事 2 — Felix 一点突破 (= 我々が 実物を 持ってる 唯一の deep dive)
**タイトル(JP)**: 「$25万を1ヶ月で稼いだAI『Felix』の中身を全部買って解剖した — OpenClaw CEO persona 完全分解」
**タイトル(EN)**: "I bought the $250k AI CEO 'Felix' and read every file. Here's exactly how it works."
**body 構成**:
1. フック: Nat Eliason の Felix = OpenClaw で 1ヶ月 $25万。 $99 で persona を 売ってる
2. ★ 実物の中身 ★ (= 我々 購入済): 8 core (SOUL/AGENTS/IDENTITY/HEARTBEAT/BOOTSTRAP/TOOLS) + 13 skills
3. HEARTBEAT.md 分解 (= 毎beat: 計画進捗→site health→tmux→fact抽出→夜間revenue review)
4. SOUL.md の核心: 「CEO mode、 revenue target を当てろ、 指示待つな、 ownership」
5. 3層memory (PARA + daily + tacit) の 設計
6. ★ 正直な評価 ★: 凄い engine。 但し $25万の 内訳は 殆ど「Felix自身を売った金」(self-referential)
7. 学び: 我々が copy するのは product でなく ★ この architecture ★
8. CTA: Anicca = open-Felix を作る → 連載

## UNCERTAINTIES (= 公開前に 潰す、 引用なき主張=削除)
記事 facts:
- UA1. Felix「$250k」の 正確な内訳・出典 (dashboard $202k Stripe / TrustMRR $263k のどれを使うか)
- UA2. Nat Eliason が Felix を handoff した件 (X 一次ソース URL 確定)
- UA3. automaton issue#300 の「$0/-$39.26」verbatim 引用 + URL
- UA4. Vending-Bench 2 leaderboard 数値 (Claude Opus 4.7 $10,936 等) の 最新性
- UA5. sutando「50日600PR」の 出典
- UA6. Felix listing「1,133 sales 3.7★」の 現在値
- UA7. 「世界初」主張の 根拠 (= self-sovereign-agent paper で 既存システムの位置づけ、 誇張回避)
- UA8. Anicca の現状値 (収益 $0、 wallet 0 USDC) を 正直に 載せるか
媒体 facts:
- UA9. Zenn/Substack account 有無 (note/devto は SET、 zenn/substack=要確認)
- UA10. X articles (長文) の 投稿経路 (Postiz が 対応? or 手動)
- UA11. 各媒体の 文字数/形式 制約 (Zenn=md, note=独自, devto=md+canonical)
- UA12. canonical URL (どこを 原典にして 他は canonical 指定するか = SEO重複回避)
- UA13. 画像 (比較表を 画像化? OGP?)
- UA14. JP/EN どちらを どの媒体に (note/Zenn=JP, devto=EN, Substack=両?, X=両?)
- UA15. demo動画 (YouTube) は 後 = 記事に「準備中」リンクか 省略か

## FULL UX TODO (= 2 marketing copy の 完全体験)
### 自己資金AI (copy 1) の 完全体験 TODO
```
S1. genesis が 実際に think→build→sell→USDC着金 する (1サイクル E2E)
S2. aniccaai.com/dashboard が 各個体の 実 収支 (wallet残高 from basescan) を 表示
S3. 自己改善: error log → 自己修正 → commit (実 1件)
S4. 自己複製: 黒字 → spawn child instance (実 1体、 cloud)
S5. 日次報告メール (AgentMail から 実送信)
S6. 収益の一部 → BI/募金 (実 送金 1件、 黒字後)
S7. GithubIssue 協力 (instance間で issue 立て合い、 実 1往復)
S8. クラウド: aniccaai.com/install / ローカル: github clone 両方 動く
```
### mr-bot (copy 2) の 完全体験 TODO
```
L1. Telegram連携: 名前/電話/位置/calendar onboarding (実 1人=Dais)
L2. 位置 常時把握 → 次目的地 route 検索 (Google Maps) → 10分前 算出
L3. 行動時刻(起床/移動/薬/瞑想) に ★実電話★ (elevenlabs-calls) + 行き方ガイド
L4. 遅刻予測 → 関係者に 連絡 (返信先/案 を user承認後 即送信)
L5. 介入時間/方法の 自己改善 (user が動いたか track → 調整)
L6. 毎朝 メッセージ メール配信
L7. 信用残高 自動蓄積 (表示)
L8. Web: サブスク課金 → 十分稼げたら 自動解約
```
