# 25 — Spec Review(code-reviewer adversarial)+ 解決

2026-06-15。superpowers code-reviewer agent が consolidated design + 13/17/21/23/24/QA-RESOLVED を adversarial review。検証して**有効な指摘を受理し修正**(performative agreement禁止)。

## レビュー要旨(受理)
**Verdict: WF-A 実装開始はまだ不可**。decomposition と test-point は強いが、2つの「✅resolved/起動可」が ground truth と乖離、load-bearing interface(telemetry/spawn)が TODO のまま「done」表記。

## 矛盾 → 解決
| # | 指摘 | 解決(本spec で確定) |
|---|---|---|
| **C1** | 憲法rule#1「人間のStripe/Netlify/aniccaai禁止」vs A8(Stripe→spawn on Daisサイト) | ★憲法rule#1 修正(carve-out)★: 禁止は **agent body**(automaton/wallet/skills)が人間鍵を持つこと。**取得funnel(Stripe Checkout)+ shelter(DO/我々のConsole)+ 配布サイト(aniccaai.com/Netlify)は Dais所有infra として許可**。「no human in loop」= **runtime の agent body** に適用、build/funnel/server課金は別レイヤ。 |
| **C2** | GATE-0「earn未達→WF-A起動しない」vs QA-RESOLVED「WORKFLOW A 起動可」 | ★QA-RESOLVED の「起動可」を撤回★。**WF-A 起動の hard gate = 「1回の wake で earn が cost を上回る(net+)実 tx を1件 verify」**(= 1 profitable wake)。それまで WF-A 本実装に入らない。 |
| **C3** | 「no human in loop」headline vs 各phase Dais gate | ★区別を明記★: **build-time = human-in-loop(Dais gate, 検証のため必須)/ runtime = no-human-in-loop(agent body)**。WF-B EVAL「Daisが電話に出る」は build-time検証であり、製品の runtime保証ではない。 |
| **C4** | 「subscription は最終的に廃れる」哲学 vs 今月$1k/$10k MRR目標 | ★timeline明記★: 近期=人間subscriptionで点火($1k/$10k MRR)、長期=organic自己増殖で subscription 不要化。矛盾でなく Phase 1→3 の遷移。 |

## ギャップ → 解決(builderが実装できるよう interface 確定)
| # | 指摘 | 解決 |
|---|---|---|
| **G1** | telemetry endpoint 不在・未定義(store未選択/schema/署名なし) | ★確定★: store = **Supabase(Postgres `instances` table)1択**。endpoint = `POST aniccaai.com/api/telemetry`。schema = §下記。auth = **EIP-191 personal_sign**(instance が wallet で `{id,ts,net_worth,...}` のhashに署名)→ API が `ecrecover` で signer復元 → `id`(=wallet addr)と一致確認。ERC-8004登録は後続(MVPは wallet addr = id)。 |
| **G2** | `spawnCloudAnicca` 未定義(DO call/persistence/refund なし) | ★確定★: spawn backend = `POST /api/stripe/webhook`(constructEvent)→ `checkout.session.completed` → DO API droplet作成(Q6 cloud-init)→ Supabase `owners` に {email, droplet_id, sub_id} 保存。**cancel/期限切れ(`customer.subscription.deleted`)→ droplet destroy**(billing lifecycle)。webhook idempotency = `event.id` を処理済tableで dedupe。 |
| **G3** | 移動時間ロジック未定義(Maps key=人間鍵→C1) | Maps Directions API = **Dais所有Google key(funnel/infra扱い=C1 carve-out で許可)**。travel block 付与rule = `location ≠ home/online` の予定のみ。瞑想@home=なし。重複は後勝ち。tz = gcal の event tz。 |
| **G4** | 位置source未定義(ユーザーにapp無し) | ★MVP scope縮小★: 位置追従(機能3)は **roadmap に降格**(realtime位置入力手段が無い)。MVP = ①gcal自動登録 ②15分前電話(Patter)③不明→Gmail質問 ④遅刻時Telegram連絡。位置追従は app/Telegram-location 連携後。 |
| **G5** | UBI Treasury addr/formula 未定義(X placeholder) | ★roadmapへ★(A10 全体)。MVP不要(earn未達で余剰なし)。実装時に Treasury wallet作成 + X=余剰の20% と確定。 |
| **G6** | verifier loop に上限なし→無限loop | ★確定★: 各 verifier loop = **max 3 iteration**。3回で未PASS → **blocked として Dais にescalate**(runtime外部障害 or 要判断)。spec21 §0 に追記。 |
| **G7** | A2「✅達成」だが T6(error-sleep報告)未実装 | ★A2 を「happy-path達成」に格下げ★。T6(error-sleep経路の発火)は **未検証**。実装: index.js patch は running→sleeping edge で発火するが、5連続error→FATAL sleep も "sleeping" 遷移を通るので発火するはず → **要 verify**(故意にinference失敗させて報告が出るか実測)。緑になるまで A2 未完。 |

## Risks(受理・明記)
- **R1**: 「$5-10 seedでlitcoin黒字」は**未実証の仮説**(33K競合・取り分極小)。WF-A起動gate = 実測で1 profitable wake が出ること(C2)。出なければ litcoin以外(openclawnch等)を探索 or seed額再評価。
- **R2**: Patter は**一度も発信成功していない**。WF-B B3 = 初の connected-call evidence を取るまで未完。
- **R3**: Akash主権(=server無人化)は外部条件依存・timeline無し。それまで DO=Dais課金=human-in-loop。copy(13)に注記追加: 「現状 server代のみ人間、将来sovereignで無人化」。
- **R4**: ★dashboard mockup数字($128,400等)は全て PLACEHOLDER★。spec13 §6/§9 と /dashboard 実装で「実データのみ表示、ダミー禁止」(HARD0.24)。

## Scope 是正
- **WF-B = 別product track**(money-funding thesis を担わない port+telephony+web-app)。WF-A の launch を block しない。
- **A5(gojo)/A7(coordinate)/A10(economy)= post-earn roadmap**(2体以上の稼ぐagentが要る=earn green前提)。MVP scope外。
- **MVP scope確定**: WF-A = A1(cloud本物automaton✅)+ A2(毎wake報告, error-sleep verify)+ A3(1 profitable wake)+ A4(spawn 2体目)+ A8(/install /me /dashboard + telemetry + Stripe spawn + cancel lifecycle)。A5/A7/A10は後。

## 適用
- AMBIGUITIES-QA-RESOLVED: 「起動可」撤回 + earn gate明記(別edit)。
- 17 §2 rule1: carve-out追記(別edit)。
- 21 §0: max 3 iter + escalate(別edit)。
- 本spec が review resolution の SSOT。
