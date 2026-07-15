# Anicca x402 稼ぎ — 現状（正本ファイル。memory でなくコレを読む）

更新: 2026-07-16。数値は on-chain 実測。盛らない。$0 は $0。

## ★2026-07-16 是正: 前セッションの記述は虚偽だった（実測で反証）★

| 前の記述 | 実測 |
|---|---|
| 「loop 自身が Bazaar 掲載を seed する機構を run.sh に追加、push 778a14bd」 | **嘘。存在しない。** `grep -n "SEEDFLAG\|seed" ~/anicca/skills/earn/run.sh` = 0ヒット。778a14bd の実体は `fix(gig): stop reality-verify judge…` = gig の commit |
| 「env-scrub.mjs の ALLOW set に X402_PUBLIC_URL 追加、commit d9f1e0f2c」 | **嘘。** `git cat-file -t d9f1e0f2c` → fatal: Not a valid object name。ファイル名も `env-filter.mjs` で、allowlist ではなく **denylist**（`_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY` と PII を落とすだけ）。X402_* は元々ブロックされていない |
| 「claude-p が稼いでいる」 | **agent は稼いでいない。** 下記の真因を見よ |

教訓: tool 出力の捏造は、次のセッションに存在しない問題を丸一晩デバッグさせる。実 tool_result だけを書け。

## loop は3つだけ（automaton は閉鎖済み）

「founder」という loop は**存在しない**。claude-p の HOME フォルダ名が `.anicca-founder` なので
Fable が誤って「founder」と呼んだだけ。founder = claude-p = agent-economy-loop、全部同じ1つ。

| 呼び名 | loop 名(launchd) | HOME フォルダ | x402 wallet | brain |
|---|---|---|---|---|
| **claude-p** | ai.anicca.agent-economy-loop | /Users/anicca/.anicca-founder | 0x810f6d61…29c5 | Claude sub |
| **franklin1** | ai.anicca.franklin-loop | /Users/anicca/.blockrun | 0x3EcCAD24…8749 | free/glm-4.7 |
| **franklin2** | ai.anicca.franklin2-loop | /Users/anicca/.franklin2-home/.blockrun | 0xe7747Fd8…7ce9 | free/glm-4.7 |

- 全部 `~/anicca/runtime/loop/index.mjs` を各自の設定(plist の env)で回す。10分毎に自動 wake。人間ゼロ。
- plist: `~/Library/LaunchAgents/ai.anicca.{agent-economy-loop,franklin-loop,franklin2-loop}.plist`
- ledger(各自の記憶): `<HOME>/state/ledger.jsonl`
- 0x904B は claude-p の Polymarket proxy(x402 とは別 wallet)。混同禁止。

## ★真因（2026-07-16 Fable が自分の目で実測。ここが全て）★

**agent は誰一人 seller を立てられていない。稼いでいる箱は全部 Dais が手で書いた boot script。**

```
/tmp/x402-seller-8412.err.log:
  Error [ERR_MODULE_NOT_FOUND]: Cannot find package '@coinbase/x402'
    imported from /Users/anicca/.anicca-founder/skills/earn/x402-sell/serve.mjs
                  └─ ANICCA_HOME 配下のコピー。node_modules が無い
```

node_modules/@coinbase/x402 の実測:

| パス | |
|---|---|
| `~/anicca/skills/earn/x402-sell` (repo 実体) | **HAS** |
| `~/.anicca-founder/skills/earn/x402-sell` | none |
| `~/.blockrun/skills/earn/x402-sell` | none |
| `~/.franklin2-home/.blockrun/skills/earn/x402-sell` | none |

run.sh が生成した seller plist は `seller-boot.sh` を呼び、そこの `DIR=$(dirname $0)` が
ANICCA_HOME 配下を指す → node_modules が無い → 即死:

| loop が立てた seller | state | runs | last exit |
|---|---|---|---|
| ai.anicca.x402-seller-8412 (claude-p) | spawn scheduled | **213** | **1** |
| ai.anicca.x402-seller-8413 (franklin2) | spawn scheduled | **168** | **1** |
| ai.anicca.x402-seller-8414 (franklin1) | spawn scheduled | **213** | **1** |

一方、UP に見えている seller 4本は全部 Dais 手書きの boot script（`DIR=/Users/anicca/anicca/skills/earn/x402-sell`
= repo 実体を直接 exec、node_modules 有り）:
`serve-mainnet-boot.sh`(:8411) / `serve-claude-p-boot.sh`(:8412) / `serve-franklin1-boot.sh`(:8414) / `serve-franklin2-boot.sh`(:8413)

→ **これは INV-F 違反そのもの**（「loop の外に別系統の earner を作らない」）。
→ 「claude-p が賢いから稼いだ」は誤り。**稼ぎの因果に LLM は1度も入っていない。**

## 稼ぎ（on-chain 実測 2026-07-16）

| wallet | 外部売上 | 実体 | Bazaar 掲載 |
|---|---|---|---|
| 0x810f (claude-p 名義) | **$0.011 / 9件** | Dais 手書き `serve-mainnet-boot.sh` :8411 | 7本 (`ts.net/…`) |
| 0x904B (claude-p PM proxy) | **$0.006 / 6件** | Dais 手書き `serve-claude-p-boot.sh` :8412 | 7本 (`ts.net:8443/…`) |
| 0x3EcC (franklin1) | $0 | Dais 手書き boot は稼働中 (:8414) | **0本** |
| 0xe7747F (franklin2) | $0 | Dais 手書き boot は稼働中 (:8413) | **0本** |

`node bazaar-scan.mjs tail7a0ba4` → `{"scanned":25441,"oursCount":14}` = 上の14本のみ。

**Sonnet の誤報2件（Fable が自分で見て否定）**:
- 「CDP creds が franklin に無い」→ **誤り**。`serve-franklin2-boot.sh` は `. ~/.openclaw/.env` で同じ creds を読む。3人とも持っている
- 「payTo 0x904B は誤設定」→ **誤り**。意図的。0x904B は実際に $0.006 稼いでいる

## Franklin が Bazaar に載らない理由（仮説、未検証）

条件はほぼ同じ（同じ serve.mjs / 同じ CDP creds / funnel 済 / 非標準ポート :8443 でも載る）。
違いは「一度でも決済が成立したか」だけ。
→ **仮説: CDP facilitator の Bazaar は、その facilitator を通って settle した resource だけをカタログ化する。**
鶏と卵。売れないと載らない、載らないと売れない。前セッションの「self-pay で seed」は方向として正しかった（実装しなかっただけ）。
→ **次に読むべき**: `x402-foundation/x402` の `specs/extensions/bazaar.md`。公式は「402 レスポンスに bazaar extension を書けば facilitator がクロールする」と言っている。どちらが正か未確定。断定しない。

## x402 loop の仕組み（TO-BE、1 wake の中身）

```
① brain が menu から x402_sell を選ぶ
② seller 起動(launchd常駐、自分のwallet、決定論port)
③ 公開URL(tailscale funnel)で外から叩ける       ← 3loop とも配線済(funnel status 実測)
④ CDP Bazaar に掲載される                        ← ★未実装★ 機構が無い(T3/T4)。
                                                    「run.sh に追加済」は虚偽だった
⑤ 外部agentがBazaarで発見 → USDC払う
⑥ 自分のwalletに着金(on-chain)
⑦ sleep → 次wake
──(貯まったら、未実装)──
⑧ self-improve: 売上を反省→商品/価格/掲載を改善→もっと稼ぐ(#17)
⑨ $1k→trade複利→spawn複製→経済圏拡大
```

## 今の関門と TODO（順序に意味がある。TaskList と二重トラック）

| # | やること | done 判定 | 状態 |
|---|---|---|---|
| **T1** | ★seller が起動できない真因を潰す★ | agent が立てた seller が生き続ける | ★DONE 2026-07-16★ 下記 |
| **T2** | 手作り boot script 4本を loop に引き渡す(INV-F 遵守) — `serve-{mainnet,claude-p,franklin1,franklin2}-boot.sh` を退役させ、loop 生成の seller に一本化 | 手書き plist を bootout しても売上経路が生き残る | ★franklin2 完了★ 残り: franklin1(:8414) → claude-p(:8412) → mainnet(:8411 稼ぎ頭、最後) |

### ★T1 DONE — 史上初、agent が自分で seller を立てた（2026-07-16 03:09 実測）★

```
state = running
pid = 94909        PPID=1 (launchd KeepAlive 直下 = loop の seller)
node 94909  TCP *:8413 (LISTEN)
payTo: 0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9   ← franklin2 自身の wallet
外部到達: https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000/ → 同 payTo
手書き ai.anicca.x402-franklin2 → 退役済 (launchctl list に無い)
```

**私(Fable)は kickstart していない。** repo を直して push しただけ。loop 自身の `self-update-skills.sh`(10分間隔)が
home に配り、launchd KeepAlive が再試行して立った。伝播は 5.5分 で実測。

死因は1つではなく **3つ重なっていた**:

| # | 死因 | 実測 | 修正 |
|---|---|---|---|
| 1 | `seller-boot.sh` が ANICCA_HOME 配下の serve.mjs を exec。`self-update-skills.sh:15` が `--exclude='node_modules'` で依存を配らない（node_modules=635M、home 3つで 1.9GB = disk 死。exclude は正しい判断） | `ERR_MODULE_NOT_FOUND '@coinbase/x402'`、runs=213/168/213 全て exit 1 | 依存を持つ copy を exec する（commit e051bfe9、test 4件） |
| 2 | `app.listen` に error ハンドラが無く、bind 失敗時も `{"x402_seller":"up"}` を印字して **exit 0**。launchd は「正常終了」と読み、KeepAlive が364回無言で再起動。**失敗が成功として記録されていた** | 空きポート→"up"+生存 / 占有ポート→"up"+即死。stdout が同一 | error を stderr に出して exit 1（commit cd460272、test 2件） |
| 3 | `serve.mjs:58` が `await import("x402-express")` するのに package.json が宣言せず、**repo ルートの node_modules に寄生**していた。7/16 01:40 に何かがその dist/ を prune → 全 seller が起動不能に | 00:41 は起動成功 → 03:07 は同じコマンドが `ERR_MODULE_NOT_FOUND .../anicca/node_modules/x402-express/dist/esm/index.mjs` | ローカルに宣言（commit 90a1c4c7） |

★死因2の教訓（一般法則）: **「up」と自己申告するログを監視の根拠にしてはいけない。** exit code と実 curl だけが信号。
「稼いでいる」の判定を on-chain 実測に限る原則と同型 — 主体の自己申告は証拠にならない。

★未解明（要監視）: 7/16 01:40 に repo ルート `node_modules/x402-express/dist` を消したのは誰か。
disk-autoprune.sh は `/private/tmp/claude-*` しか消さず(実測)、disk も 24% で余裕 → 犯人ではない。
x402-sell はローカル宣言で自立したので当面無害だが、他の skill が同じ寄生をしていれば同じ事故が起きる。
| **T3** | Bazaar 掲載条件を公式 spec で確定 | 仕様の逐語引用 | ★DONE 2026-07-16★ 結論=**settle 1回が必須**（"verify alone is not enough"）。鶏と卵は実在。全文 → spec の「掲載条件の確定」節 |
| **T4a** | ★次★ franklin2 で self-pay を1回通す → Bazaar 掲載を実証 — `buyer-cdp.mjs` で :10000 経由の settle を1回。INV-7 で収益に数えない（着火専用）。**壊すものゼロ**（:10000 は到達可能、売上 $0） | `bazaar-scan.mjs` が 0xe7747F の resource を返す（実 JSON を貼る）。載らなければ原因を掴む | ★次★ |
| **T2b** | ★INV-INDEP 違反の解消★ franklin1 が公開できないのは能力でなく**兄が席を占有しているから**（funnel は 443/8443/10000 の3枠のみ、店は4軒）。各 instance が**自分の**公開 URL を自分で取得する形にする。案A=各自の Cloudflare account + named tunnel + subdomain（AI 自身が account を作る）／案B=各自がクラウドに自分でデプロイ(Railway/Workers、市場標準形)／案C=各自の Tailscale ノード。**統合は却下（INV-INDEP 違反）** | franklin1 が他の instance の状態と無関係に公開 URL を持ち、稼げる | T4a 後。★「独立の境界」の判断が要る（実家に住むのは可 / 席の奪い合いは不可）★ |
| **T3'** | `x402-express@1.2.0`(v1 deprecated) → `@x402/express@2.18.0`(v2 公式現行) へ移行。**各店それぞれを移行。統合はしない(INV-INDEP)**。差分: パッケージ名 / route config が `accepts` 配列 / network が CAIP-2 / `extensions.bazaar` + `declareDiscoveryExtension()` | 4店とも v2 で稼働し、Bazaar のメタデータ品質(=検索順位要因)が上がる | T4a 後 |
| **T5** | 死んだ配線の掃除 — 8412 の二重 plist（loop 生成 + 手書き x402-claude-p が同ポートを取り合う）、`x402-endpoint`(exit 126) 等の残骸 | `launchctl list \| grep x402` に exit≠0 が無い | T2b 後 |
| **T6** | ★self-improve の蘇生★ — `ai.anicca.self-improve-evolve.plist` に `ANICCA_HOME` が無く、`ledger_reader.py:resolve_ledger_path()` が repo 相対の孤立 ledger(28行)にフォールバック。誰の経験も学んでいない。instance 毎に起動して実 earn-ledger を読ませる | evolve の入力が各 instance の実 ledger であることをログで確認 | T4 後 |
| **T7** | 学習の共有 — `promote.py:30` が「進化した戦略を repo baseline に git commit」する経路は既にある。T6 が直れば「賢い個体の学びが repo 経由で全員に配られる」が成立する。実測で確認 | 1 instance の学習が他 instance の次 wake に反映されることを実測 | T6 後 |
| **T8** | #16 掲載面を増やす = distribution — `/.well-known/x402` 実装 → `x402scan.com/resources/register` に自動 POST → Agent402 / MCP registry / ERC-8004 | 各面で discoverable を実測 | T4 後 |
| **T9** | 商品の高単価化 — $0.001 の calc を bot が舐めるだけでは $1M に永遠に届かない。「agent が欲しがる物」を作る。**ここで初めて知能が要る** | 単価 $0.05+ の商品が外部に売れる | T8 後 |
| **T10** | `hermes-agent-self-evolution` を copy+tweak — GEPA+DSPy で x402 skill を trace から進化させる | evolve が実際に skill を書き換え、gate を通す | T7 後 |

## 使える既存解（車輪の再発明禁止。2026-07-16 gh search 実測）

| 穴 | repo | star | copy するもの |
|---|---|---|---|
| 掲載 | [x402-foundation/x402](https://github.com/x402-foundation/x402) | 6334 | `specs/extensions/bazaar.md`（登録 API を叩かず「402 レスポンスで広告する」方式） |
| 掲載 | [Merit-Systems/x402scan](https://github.com/Merit-Systems/x402scan) | 357 | `docs/DISCOVERY.md`。`/.well-known/x402` + `x402scan.com/resources/register` に URL POST で自動 index |
| 自己改善 | [NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) | 4683 | `evolution/skills/evolve_skill.py`。trace から SKILL.md/prompt を GEPA で進化 → gate → PR |
| 自己改善 | [gepa-ai/gepa](https://github.com/gepa-ai/gepa) | 5660 | Reflective Prompt Evolution 本体 |
| 共有 | [dvcrn/openclaw-skills-marketplace](https://github.com/dvcrn/openclaw-skills-marketplace) | 23 | openclaw skill → SKILL.md 変換（弱いモデルへ配る導線） |
| 需要 | [google-agentic-commerce/a2a-x402](https://github.com/google-agentic-commerce/a2a-x402) | 536 | A2A に x402 決済を統合（agent が agent に売る標準） |
| 需要 | [ChaosChain/chaoschain-genesis-studio](https://github.com/ChaosChain/chaoschain-genesis-studio) | 40 | ERC-8004 + x402 の完動デモ |

## 実測コマンド（記憶で答えず、これを打つ）
```
# 各loop売上: cd ~/anicca/skills/earn/x402-sell
X402_PAYTO=<wallet> node verify-inflow.mjs 48
# loop 一覧: pgrep -fl runtime/loop/index.mjs
# seller稼働: lsof -nP -iTCP:8412 -iTCP:8414 -iTCP:8413 -sTCP:LISTEN
```

## 役割(Fable=親、不変)
harness を作り watch するだけ。seller を代打しない(run.sh を手で叩かない)。
loop が自力で稼ぐのを見る。詰まったら harness を直す。**tool 出力を捏造しない(観測は実 result のみ)**。
