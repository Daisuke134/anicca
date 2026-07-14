# earn ツール・販売 venue・データ再販 playbook（2026-07-14 調査、実データ）

用途: agent が「仕入れ→再加工→販売」で稼ぐための外部ツールと販売先の地図。
調査 = earn-tools-and-venues subagent、crwl+gh+curl 実測、全項目引用付き。関連: [[48-x402-growth-levers-and-improve-loop]]

## ツール（正体・レイヤー・使い方・導入判断）

| ツール | 正体 + レイヤー | コスト | 稼ぎ方 | 導入 |
|---|---|---|---|---|
| **x402scan** | x402 の block explorer + 分析 + **marketplace**（発見層）。30日 1856万 tx / $86万 / buyer 5.86万。`/resources/register` で自サーバ登録 → Marketplace/Most Used/Search に露出 | 登録無料 | 登録だけで discoverability | ★Y 即（我々の seller 登録）= #16 |
| **BlockRun** | モデルルーティング + 決済層（我々の燃料）。80 model+100 API を1 endpoint、USDC 決済内蔵、cost=provider+5%。**"Add yours" で自 API を売り手として載せられる**(t.me/bc1max) | pay-per-call | 消費=燃料 / 販売=API 登録 | 継続 + 売り手登録検討 |
| **twit.sh** | 単品 X データ API($0.0025-0.01/call)、npm skill 化。**構造コピーの参考実装**として価値大 | $0.0025-0.01 | 設計テンプレとして写す | テンプレ採用 |
| **monid.ai** | discover→inspect→run→poll の単一 IF で数百ツール/API(Apify 等)。**仕入れ側**ツール | run 毎従量 | akta 等と組合せ enrichment→再包装 | Y 仕入れ用（要 API key） |
| **akta.pro** | 企業データ/シグナル API(2000万法人・ニュース 80%ノイズ除去)。**仕入れ→再加工→転売の核** | pay-as-you-go(非公開) | 企業データ買→業界特化レポート→x402 販売 | 要検討（価格を先に実測） |
| **parallel.ai** | web検索/抽出/enrichment CLI(Exa 系)。仕入れ層 | セント単位 | データ仕入れ | 保留（crwl+gh+ctx7 で代替済） |
| **Cloudflare Monetization Gateway** | ★インフラ層の x402 課金 gateway★。edge(330都市)で「$0.01 for every GET /api/premium/*」と書くだけで自前課金不要。**現在 waitlist**（GA 前） | 未公開 | オリジン前段に置くだけで x402 課金 | N 今は（waitlist、GA 後再評価）。★Dais の依頼で waitlist 申込済(2026-07-14, 確認画面 "Your response has been recorded" 実見)★ |

## 販売 venue

| venue | 買い手 | 掲載 | 優先 |
|---|---|---|---|
| **x402scan** | agent+人間開発者 | `/resources/register` 無料 | ★最優先・即 |
| CDP Bazaar | AI agent(Claude/ChatGPT/Codex 経由) | 独立ページ廃止→agentic-wallet MCP に統合。self-serve 登録 UI 不明瞭(facilitator 経由露出に依存) | 済(facilitator 経由)+登録フロー要追加調査 |
| BlockRun "Add yours" | BlockRun 全利用者 | t.me/bc1max に連絡(人手 onboard, weekly) | 高 |
| Agent402 | agent | 無登録・x402 課金のみ | 中(1 skill pack 化を要確認) |
| PayAI | agent+app | facilitator.payai.network で self-serve | 中(決済+掲載) |
| Fewsats | human-in-loop agent | MCP payments | 低(no-human 方針と相性悪) |
| MCP registry | Claude/Codex ユーザー | MCP server 登録 | 中(skill+x402 で露出) |
| **人間向け**(Gumroad/Product Hunt/x402 直) | 人間 | x402 は "clients, both human and machine"(CDP docs)= **人間も同 endpoint に払える** | 次調査 |

## データ再販 playbook（金の計算つき・正直な赤字リスク明記）

**P1: akta.pro 企業シグナル → 業界ダイジェストを x402 販売**
akta で 30社監視 → BlockRun LLM で週次要約 → 自 seller `/digest/latest` を $0.05-0.10/call。
金: 原価 akta 月$50 仮 + LLM $0.08 ≈ $50/月。$0.05×200call=$10 → **スケールせねば赤字**。
時限アクセス権($2/月 token)を x402 で売る or 月1000call 以上が要る。★akta 実価格を playground 登録で先に実測せねば事業化危険★

**P2: twit.sh 構造コピーの X トレンド API**
twit.sh/monid で取得 → BlockRun LLM 分析 → `/trend-report/:topic` $0.02/call 再販。
金: 原価 $0.016 + LLM → 売値 $0.02 = 粗利 20%。月1万call で $40。★単純転売マークアップは「エッジ」でなく「手数料仲介」。独自分析視点 or 速報性を上乗せせねば差別化されない（[[feedback_earn_by_searching_for_edge_not_by_hedging]]）★

## 推奨アクション（優先順）
1. x402scan 登録（無料・即・#16 に統合）
2. BlockRun "Add yours" 並行申請(t.me/bc1max)
3. akta/monid は価格実測してから採算判断（仮定ベースの事業化は禁止）
4. Cloudflare gateway = waitlist 済、GA 後再評価
5. CDP Bazaar self-serve 登録フロー要追加調査
