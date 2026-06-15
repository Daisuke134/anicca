# 24 — life-manager 決定 + 各 Workflow の goal(main + mini)

Dais 2026-06-15。Claude が決定。/goal を全 step で明確化。

## §1 ★ 決定: life-manager のやり方 ★
**1つのコードベース(anicca repo `skills/life`)、2つのデプロイ先で出す。OSS必須なので両方必要:**
```
skills/life (anicca repo, OSS, MIT)
  ├─▶ ① CLOUD web-app: aniccaai.com/life-manager(=anicca instance の1機能)
  │       ★ Dais 自身もここから使う(subs払わず同じもの)= dog-food ★
  │       → ユーザーと完全に同じ env。error が出たら我々も即気づく。
  └─▶ ② LOCAL OSS: anicca repo を local で起動(Franklin的に自前compute=ClawRouter)
          → 自分のマシンで動かしたい人向け。
電話 = Patter(carrier非依存: Telnyx/Plivo + Gemini Live。Twilio停止の代替)。
private OpenClaw からは life-manager を剥がす(OpenClaw = aniccaios scaling 専用 private assistant に縮小)。
```
**理由**: (a) OSS要件 → anicca repo + local起動が必須。(b) dog-food要件 → Dais の分も cloud web-app で動かす(同 env でないと error に気づけない)。両立は「1コード × 2デプロイ」が唯一の解。`/install`(money-maker)と `/life-manager`(生活管理)はページ分離、両方安定後に merge or as-is。

## §2 WF-A(MONEY-MAKER /install)の goal
**MAIN GOAL**: cloud で 1 体の Anicca が **no human / no Claude in loop** で実 USDC を稼ぎ、自給(食=ClawRouter, 住=server)し、毎wake自己報告し、自己増殖で 2 体目を立て、全個体の P&L が /dashboard に realtime 透明公開される。
| step | mini-goal(これが緑になるまで loop) | evidence |
|---|---|---|
| A1 | 本物automaton が cloud稼働、ClawRouter compute、人間鍵ゼロ | systemctl active + log[THINK] + grep鍵0 |
| A2 | 毎wake、agent自身が4項目報告メール ✅**達成** | daemon log "report fired" + AgentMail |
| A3 | 実 USDC/token が wallet に着金 | tx hash basescan 0x1 + balance増 |
| A4 | 2体目を spawn(自前wallet/mail) | 子droplet active + 別wallet |
| A5 | gojo: 死にかけ個体へ実送金で復活 | tx 0x1 + critical→running |
| A6 | issue-dev: 母repo に実issue→PR→merge | issue URL + merge hash |
| A7 | coordinate: 2体で blocked→help | 両者log |
| A8 | /install /me /dais /dashboard live + telemetry POST | curl200 + browser目視 + dashboard.json更新 |
| A10 | ubi/token/hire 実tx | 各tx |
| EVAL | 8 test point 全 REAL | eval-report |

## §3 WF-B(LIFE-MANAGER /life-manager)の goal
**MAIN GOAL**: ★ Anicca が Dais(と任意ユーザー)の実電話に、全予定を移動時間込みで自動登録した上で、各予定の15分前に発信 → 応答 → **録音が完全に良い** → Dais が「動いてる」と言う ★。cloud web-app(/life-manager)と local OSS の両方で動く。
| step | mini-goal | evidence |
|---|---|---|
| B1 | life-manager を anicca repo(skills/life)に移設、OpenClawから剥がす | repo に skills/life 存在 + OpenClaw から削除 |
| B2 | heartbeat が gcal 読む + **移動時間を自動登録** | テスト予定作成→移動ブロックが gcal に挿入(目視) |
| B3 | **Patter で Dais の実電話に発信** | 実着信 + ★録音が良い★ + Dais OK |
| B4 | 各予定の when/where/what 補完(瞑想→home / 仕事→場所search / 不明→**Gmail質問**) | gcal に where 記入 + 質問メール着信 |
| B5 | 位置追従(移動開始まで鳴らし続け)+ Telegram で関係者連絡(承認後) | 再発信log + 連絡送信 |
| B6 | cloud web-app /life-manager + local OSS 両方稼働 | 両 env で B2-B5 が動く |
| B7 | Sentry: error→**auto-PR**(merge無) | Sentry issue + PR URL |
| EVAL | ★実電話→応答→録音OK→Dais OK★ + gcal自動登録確認 | 録音 + gcal screenshot |

## §4 WF-C(MARKETING)の goal
**MAIN GOAL**: 記事 + demo動画 + X(EN+JA)が実 URL で公開され、6/19(金)TIB hackathon で上映できる。
| step | mini-goal | evidence |
|---|---|---|
| C1 | 研究(Frank#1/automaton#2記事 + WF-A,B の実証データ)| 収集完了 |
| C2 | 3本目記事(思想+実証: 何を動かし/いくら稼いだか/正直な結果)執筆・公開 | 記事URL 200 |
| C3 | demo動画(稼働→実earn→dashboard→自己増殖の証明)YouTube公開 | YouTube URL + frame/audio |
| C4 | X(EN+JA)投稿 + Slack下書き | 投稿URL×2 |
| EVAL | 全 live + frame/audio verify(HARD0.31)| eval-report |

## §5 起動条件 & 順序
- GATE-0(WF-A前): ①server稼働✅ ②実earn着金❌(seed or 別経路で解決中)③毎wake報告✅ ④repo+spawn一部。
- 順序: WF-A(自給body)→ WF-B(life-manager, 独立)→ WF-C(両検証後)。WF-A と WF-B は infra が別なので並行可。
- 各 WF: builder ≠ verifier ≠ eval ≠ Dais gate。1 phase ずつ evidence→Dais承認→次。
