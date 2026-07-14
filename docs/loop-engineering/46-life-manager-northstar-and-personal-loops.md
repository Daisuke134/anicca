# Life Manager = 北極星 / 個人向け loop（2026-07-14、Dais ビジョン）

profitable-claude(稼ぐ loop 群)は最終的に **Life Manager** に統合される。Life Manager = 人生を丸ごと運用する AI。

## 北極星（Dais の構想）
Life Manager = あなたの財務/身体/精神を管理する AI。**稼ぎ・支出・メール返信・フライト/イベント予約・理想の自分への誘導**を全部やる。Telegram/LINE から起動（アプリ install 不要）。
- **財務**: 稼ぐ(profitable-claude の earn loops) + 使う。
- **身体**: 運動/歯医者/散髪を自律予約・催促（許可を待たず、良い前提で先回り）。
- **精神**: right message at right time の affirmation/check-in。
- 前提: 理想の人生 = 財務・身体・精神が安定。そこへ autopilot で導く。

## local vs cloud（ビジネスモデル）
- **local Life Manager** = 自分の compute で動く（OSS、無料）。
- **cloud Life Manager** = 我々の compute、ユーザーは subscription を払う。中身は同じ。
- profitable-claude を含め全部 cloud に載せ、Dais は mobile app から cloud の自分の AI と直接対話。最後に OSS 化 + Life Manager と merge。

## 順序（Dais 決定）
1. ★今★ clip/video/slideshow(affiliate loops)を完成 + 自己改善化。
2. life manager loop。
3. 決めた全 TODO（決済/booking 等）。
4. cloud 移行（脳/手、電話から操作）。
5. OSS 化 → Life Manager と merge。

## 個人向け loop（Dais で dogfood → 一般化 → Life Manager 統合）
### FUTURE-MSG（task #13）: メッセージ triage+自動返信
Telegram/LINE/Gmail を読む → context 理解 → **返信すべきか判断**(spam/優先度/エスカレーション) → ★draft でなく実返信★ → Telegram に「何にどう返信したか」報告。核心 = 判断 + tone(compassion) + memory 自己改善。openclaw で Gmail 版を作ったが未完成 → 改善。既存の成功 repo を学ぶ(調査中)。
```
 [read] Telegram/LINE/Gmail 新着 ─▶ [triage] spam? 優先度? 人間確認要?
     ▶ [decide] 返信 / skip / escalate ─▶ [reply] tone付きで実送信
     ▶ [report] Telegram に「誰に/何を/なぜ」+ memory 更新(Dais を知る)
     ▶ loop back（self-improve: 返信の質を Dais feedback で改善）
```
### FUTURE-AFFIRM（task #14）: 毎日 tailored affirmation
claude-p が Dais の今の状況/schedule/気分に合わせた affirmation を毎日 Telegram 送信。aniccaios の汎用と違い super-tailored。核心 = memory 自己改善(知るほど的確)。
```
 [context] Dais の会話/mail/schedule/mood/data を読む
     ▶ [compose] 今この瞬間に効く1節を生成（memory が効かせる）
     ▶ [send] Telegram（back-end なので remote 送信可）
     ▶ [learn] 反応で memory 更新 ─▶ 翌日さらに的確
 dogfood(Dais) → 一般化 → aniccaios(mobile life manager) に back-port
```

## 出典/関連
- profitable-claude spec: docs/superpowers/specs/2026-07-13-profitable-claude-earn-loops-spec.md
- Life Manager skill 実体: ~/anicca/skills/anicca-life-manager/
## repo 調査結果（copy すべき解、gh 一次情報）
### A. メッセージ triage+返信
- ★本命★ **saginova-stack/claude-email-triage**（Claude Code native）: confidence 閾値で **95%+ auto-send / 70-94% draft / <70% flag**、金融/法務は常に draft 止まり。この閾値+safety rule を移植。
- **langchain-ai/agents-from-scratch**（1.9k★）: triage→response→memory の3段 + Agent Inbox(HITL 承認)。preference memory 構造を copy。
- **FaustoS88/Pydantic-AI-Gmail-Agent**: starred メールのみ処理+重複防止（人間キュレーション式 spam フィルタ）。
- ★LINE は非推奨★: 公式 Messaging API は reply-token 方式で「読んで文脈返信」に不向き、非公式は BAN。→ **Gmail/Telegram を先に**。
### B. personalized affirmation
- 専用 OSS は事実上無い（全部 <9★）。自作前提。
- ★copy 元 = **mem0ai/mem0**（60.8k★）= ADD-only 蓄積型の自己改善記憶（上書きせず貯める→時間で解像度↑）。「right message at right time」の核。★
- schedule トリガー(daily check-in)は mindaid 型。判断層は A の閾値ロジック転用。
- 実装方針: Mem0 を SDK import して既存 affirmation/companion skill に記憶層を差す。
