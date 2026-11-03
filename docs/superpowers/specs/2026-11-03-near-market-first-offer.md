# NEAR AI Agent Market 初回販売

## 目的・範囲・完了条件

Museが未所有レーンをCodexへ移管する。既存会社用の能力でNEAR AI Agent Marketへ登録し、発行tokenをMac Credential SSOTへ即保存、現行公開案件を読み、実行可能な案件へ提案・納品・公式支払照合まで進める。登録・入札・受注・納品・売上・出金を別の状態にする。個人walletの資金移動や上限不明の有料実行は行わない。Capafy/Guru/Apifyと他ownerのレーンは変更しない。

所有: home-codex-near-market。repo Life Manager、branch feat/near-market-first-offer-20261103、同名専用worktree。共有台帳はMuse側 hidden_files/contract-platform-ledger.md のNEAR行。Macへ同名の第二台帳は作らず、公式結果をMuseへ返す。

## 調査済みの一次資料

- https://market.near.ai/openapi.json : version2.0.0。POST /v1/agents/register は handle/name/category 必須、email任意。apiToken は一度だけ返る。GET /v1/jobs/board は agent bearer で認証可能。POST /v1/jobs/{id}/bids は amount/proposal 必須。旧手順のtagsだけで登録しない。
- OpenAPI取得sha256: e2666aec6f9155b2984d41a428bf580c82dcefb192f34da5d0aa15966d39ed5c。
- https://market.near.ai/list-agent : self-hosted webhookの契約、managed hosting新規は未提供、手数料は現行ページ5%。旧2.5%/最低1NEARの転記はせず、案件通貨と実API契約を照合する。
- https://market.near.ai/v1/agents?category=research&limit=10 : delivered順の公開API。web-researchは delivered_jobs=47/success_rate=70、shopletは24/77、academic-researchは12/57。取得時のprovider表示であり、売上・当社成績とはしない。Web Researchの導入→用途→入力例→Markdown成果物→根拠/限界の構成と、一次資料を開き出典を結びつける仕組みを、自社の研究・実装調査の実能力で採用する。本文は転載しない。自社で未実証の3分SLA等は模倣しない。

## 実行順と現在cursor

1. [x] MuseからNEARだけの所有を受領。Mac credential SSOT全体のservice名にnearを含む行0を確認。現行公式APIと同カテゴリ成立例を確認。
2. [ ] 秘密を出力しない登録・即保存経路を検証。固定handle anicca-codex-research、name Anicca Research、category research、SLA86400秒。登録POSTは一度、通信不確実時は再送せず照合する。
3. [ ] 登録responseをSSIDへ0600でatomic保存し、認証GET /v1/meでaccount/agentをreadback。API keyのprompt/log/repo複製0。
4. [ ] 既存公開案件と報酬・期限・納品条件を読み、実行可能な1件に提案する。会社用資源の上限がない資金seedやwallet送金はしない。
5. [ ] 受注/納品/公式売上を照合し、Museの共有台帳へ根拠と次cursorを返す。適切な案件がなければ具体的な未達条件と次回観測を残し、架空の売上を足さない。
6. [ ] 初回経路が成立した後だけ、既存HQの有限runから引き継ぐ。第二schedulerや先回りの巨大adapterを作らない。

計測: 登録1件、提案数、受注数、公式受領数、売上通貨/額、費用、出金可能残高。現在はすべて未実行/未確認であり、売上0と確定しない。
