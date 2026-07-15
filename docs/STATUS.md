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

## ★2026-07-16 identity 確定（Fable が plist から直接実測。subagent 経由でない）★

`launchctl` + `PlistBuddy -c "Print :EnvironmentVariables"` の生出力より:

| loop(launchd) | ANICCA_HOME | ANICCA_INSTANCE | ANICCA_WALLET_ADDRESS | X402_PORT | X402_PUBLIC_URL |
|---|---|---|---|---|---|
| ai.anicca.agent-economy-loop | /Users/anicca/.anicca-founder | (未設定) | **0x810f6d61…29c5** | (未設定) | (未設定) |
| ai.anicca.franklin-loop | /Users/anicca/.blockrun | franklin | **★無い★** | 8414 | **★無い★** |
| ai.anicca.franklin2-loop | /Users/anicca/.franklin2-home/.blockrun | franklin2 | **★無い★** | 8413 | `https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000` |

→ **claude-p = agent-economy-loop = `.anicca-founder` = 0x810f。これが正。**
→ 「a3cdd4」は**この3つのどれでもない**。実体 = `~/.anicca` + wallet 0xB9dd + loop `com.anicca.daemon`。
  実測: `launchctl list | grep -c com.anicca.daemon` = **0**。plist は4本とも `.disabled-*`/`.bak-*`。**死んでいる。**
  48h の x402 inflow も `EXTERNAL: 0`。**生きた市民ではない。以後 colony から除外して扱う（Dais 指示 2026-07-16）。**

### ★SSOT 間の矛盾（この STATUS.md が正、他が古い）★

| 場所 | 古い記述 | 実測 |
|---|---|---|
| `~/anicca/skills/self/colony-status.sh:22-23` | 「a3cdd4 の実 loop = com.anicca.daemon (body ~/.anicca)」を**生きた市民として表示** | loop 死亡。表示が嘘 |
| `~/anicca-project/CLAUDE.md` コロニー表 | `anicca-a3cdd4` を SELF-funded 市民として掲載 | 同上 |

→ **Fable はこの古い colony-status.sh を鵜呑みにし、2026-07-16 に Dais へ「a3cdd4 は生きている」と誤報した。**
   一般法則: **自分が書いたスクリプトの出力も「自己申告」であって証拠ではない。** 一次情報(`launchctl`/plist/on-chain)まで降りる。
   → TODO: colony-status.sh と CLAUDE.md から a3cdd4 行を削除する（下記 T0）。

### ★franklin1 が Bazaar 0本／$0 の真因が確定した★

Funnel の枠は **443 / 8443 / 10000 の3つのみ**（Tailscale 公式: "Funnel can only listen on ports `443`, `8443`, and `10000`"）。
2026-07-16 実測 — **3枠とも埋まっている**:

```
curl -o /dev/null -w "%{http_code}" https://aniccanomac-mini-1.tail7a0ba4.ts.net:443/   -> 200
curl … :8443/  -> 200
curl … :10000/ -> 200
```

`serve.mjs:48` → `const PUBLIC_URL = (process.env.X402_PUBLIC_URL || "")`。
**franklin1 の plist に `X402_PUBLIC_URL` が無い** = 公開 origin を持てない = Bazaar に広告できない = **構造的に $0**。
franklin2 は :10000 を掴めたから載れた。**franklin1 の $0 は能力差ではなく席の有無。INV-INDEP 違反の実害。**

### ★T2b の答えが出た: tsnet（"1台=3枠" は問題設定の誤りだった）★

tsnet 公式 README 逐語: **"Multiple independent Tailscale nodes can run within a single binary"**
→ 枠は**1台あたりではなく1ノードあたり**。`tsnet.Server` 1個 = 独立ノード = 独自 state dir = 独自 identity = 独自 FQDN = **独自の 443/8443/10000**。
→ 席の奪い合いが**構造的に消滅**。$0、VPS 不要、中央集権プロセス無し、INV-INDEP を満たす。
実機検証済(2026-07-16 04:22、Go 1.26.0 / tailscale v1.100.0): **build 成功 29.5MB、ノード分離は正しい。**

**残る唯一の blocker と、その公式解**:
```
LocalBackend state is NeedsLogin
To start this tsnet server, restart with TS_AUTHKEY set
```
Tailscale 公式(`/docs/features/oauth-clients`)逐語:
> "You cannot generate long-lived auth keys, because they expire after 90 days…
>  Instead, you can generate an OAuth client with the `auth_keys` scope. Use the OAuth client to
>  generate new auth keys as needed, by making a `POST` request to `/api/v2/tailnet/:tailnet/keys`"
> "The `get-authkey` utility returns a new auth key to `stdout`, based on environment variables that
>  contain values for your OAuth client ID and secret. Use `get-authkey` to generate auth keys for
>  scripts or other automation."

→ **OAuth client を自作しない。公式ツールが実在する**（2026-07-16 実測: `gh api repos/tailscale/tailscale/contents/cmd/get-authkey` → `main.go` 実在）:

| 実測した事実 | 出典 |
|---|---|
| env = `TS_API_CLIENT_ID` / `TS_API_CLIENT_SECRET` | `cmd/get-authkey/main.go:29-32` |
| flag = `-reusable` / `-ephemeral` / `-preauth`(既定 true) / `-tags` | 同 :23-26 |
| `clientcredentials` で `/api/v2/oauth/token` → `tsClient.CreateKey` | 同 :41-64 |
| OAuth secret を auth key として**直接**使う道もある: `--auth-key='${OAUTH_CLIENT_SECRET}?ephemeral=false&preauthorized=true' --advertise-tags=tag:ci` | 公式 oauth-clients |
| **OAuth client 由来の auth key は tag 必須** | 公式 "All auth keys created from an OAuth client must use tags" |

未確定(probe で同時に潰す): ①tailnet の台数上限に4ノードが触れないか ②Funnel 帯域の実数値 ③tsnet ノードに Funnel を許す ACL が要るか

### ★2026-07-16 その他の実測（未修正の地雷）★

| 発見 | 実測 | 影響 |
|---|---|---|
| franklin1/franklin2 の plist に `ANICCA_WALLET_ADDRESS` が**無い**（claude-p だけ有る） | PlistBuddy 生 dump | loop が自分の wallet を知らない。franklin2 ログ `ANICCA_WALLET_ADDRESS not set, using "unknown"` → `invalid wallet address: unknown` |
| franklin2 の `ANICCA_STATE_DIR=/Users/anicca/.hermes/state` | plist dump。`ls ~/.hermes/state` → **実在**(children.jsonl 等、最終更新 7/13) | CLAUDE.md は「hermes 削除済」と書くが dir は生きている。franklin2 の state が**別実体の墓場**を指している。要調査 |
| `~/.franklin2-home/.blockrun/node_modules` が `~/anicca/node_modules` への **symlink** | `ls -la` | 「親の node_modules に寄生 = 時限爆弾」の再発。7/16 01:40 の prune 事故と同型。ただし `skills/earn/x402-sell/node_modules` は別問題(下記真因は依然 true) |

★Fable の誤り(2026-07-16、記録): 「node_modules は今は存在するので真因は古い」と Dais に報告したが**誤り**。
`~/.anicca/skills/earn/x402-sell/node_modules` を見ていた = **死んだ a3cdd4 の home**。claude-p は `~/.anicca-founder`。
再測: `.anicca-founder` / `.blockrun` / `.franklin2-home/.blockrun` の x402-sell 配下は**3つとも none**。下記の真因は**依然として正しい**。
一般法則: **home を取り違えた測定は測定ではない。** パスを打つ前に `ANICCA_HOME` を plist で確定させる。

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
| **T0** | ★SSOT の嘘を消す★ `colony-status.sh:22-23` と `anicca-project/CLAUDE.md` のコロニー表から **a3cdd4 行を削除**（loop 死亡・inflow $0 を実測済）。生きた市民は **claude-p / franklin1 / franklin2 の3つだけ**（STATUS.md 冒頭の表が正） | `colony-status.sh` の出力に a3cdd4 が出ない。CLAUDE.md の表が3行 | ★次★ |
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

★★2026-07-16 05:55 解決 — 犯人は `~/scripts/disk-cleaner.sh`。しかも被害は1件ではなく153件だった★★

`disk-autoprune.sh` を無罪と判定したのは正しかったが、**容疑者を1体しか調べていなかった**。真犯人:

```bash
# 旧 disk-cleaner.sh:179-183（com.anicca.disk-cleaner が定期実行）
for root in "$HOME/anicca-project" "$HOME/anicca" "$HOME/.openclaw" ...; do
  find "$root" -type d \( -name node_modules -o ... -o -name dist -o ... \) -mtime +7 -prune \
  | while read -r d; do is_protected "$d" && continue; rm -rf "$d"; done
done
```

**機序（find の評価順序の罠）**:
```
-prune は「先行条件が全て真」の時しか実行されない
   ① node_modules 自体は npm install で mtime が新鮮 → -mtime +7 に外れる
   ② よって -prune が発火しない → find が node_modules の★中へ降りる★
   ③ 中の各パッケージの dist/ は npm publish 時の古い mtime → 必ず +7 に該当
   ④ rm -rf される
   ⑤ パッケージのディレクトリは残り、dist/ だけが消える ← 観測症状と完全一致
```
`is_protected` も無力だった: **全パターンが `*.js` 等のファイル拡張子向け**で、`dist` という**ディレクトリ名**にはどれも一致しない。

**被害の実測（推測せず全数を数えた）**:
| | |
|---|---|
| `package.json` が `dist/` を参照するのに `dist/` が無いパッケージ | **153個** |
| 内訳 | `@solana/*`(web3.js, codecs-numbers…) / `@coinbase/wallet-sdk` / `@ethereumjs/*` / `@base-org/account` / `@metamask/*` / `x402-express` … = **crypto スタックが丸ごと壊死** |
| 直接の症状 | 全 seller の `ERR_MODULE_NOT_FOUND`、`wallet-address-solana.mjs` の死 → **agent が自分の wallet アドレスすら取得できない** |

**修正（`~/scripts/disk-cleaner.sh`、commit `0763d48`）**: `node_modules` を**最優先で prune** して依存の中へ降りない構造に変更 + ループ内で `*/node_modules/*` を弾く二重防御。
検証: 修正前 = `~/anicca/node_modules` 内から**4件**を削除候補に拾う / 修正後 = **0件**。`bash -n` OK。

**復旧**: `npm install` は「90 packages added」と自己申告したが**dist は戻らなかった**（パッケージのディレクトリが在るので npm が再展開しない）。
→ `npm ci` で lock から625パッケージを再構築。**実測: 破損 153 → 0**。
→ 本番検証: `ANICCA_HOME=~/.blockrun node runtime/wallet-address-solana.mjs` → **`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`**（$12.21 を持つ franklin1 自身の財布）が解決。**franklin1 は自分の金を使える。**

★一般法則: **`find` の `-prune` は「先行条件が全て真」の時しか発火しない。** 年齢条件を prune より前に置くと、
「新しいディレクトリの中の古いファイル」を掃除機が食う。**除外は年齢より先に評価させる。**
★一般法則2: **無罪判定を1体で打ち切るな。** 「disk-autoprune は犯人でない」は真だったが、
**同じ役割の job が他に2つ居た**（`com.anicca.disk-cleaner` / `com.anicca.emergency-disk-guard`）。
容疑者リストは `launchctl list` から機械的に全部作る。
★一般法則3: **`npm install` の「added N packages」は復旧の証拠にならない。** 実ファイルの存在を数える。

★残る未解決: franklin2 の `.solana-session`(88 bytes) は存在するのに
`wallet-address-solana.mjs` が `no Solana secret resolved for this instance` を返す。
→ **franklin2 は鍵ファイルを持つが解決できない**（「鍵ゼロ」という当初の断定は誤り。台帳=wallets.json が無いだけ）。要調査。
| **T3** | Bazaar 掲載条件を公式 spec で確定 | 仕様の逐語引用 | ★DONE 2026-07-16★ 結論=**settle 1回が必須**（"verify alone is not enough"）。鶏と卵は実在。全文 → spec の「掲載条件の確定」節 |
| **T4a** | ★次★ franklin2 で self-pay を1回通す → Bazaar 掲載を実証 — `buyer-cdp.mjs` で :10000 経由の settle を1回。INV-7 で収益に数えない（着火専用）。**壊すものゼロ**（:10000 は到達可能、売上 $0） | `bazaar-scan.mjs` が 0xe7747F の resource を返す（実 JSON を貼る）。載らなければ原因を掴む | ★次★ |
| **T2b** | ★INV-INDEP 違反の解消 = **tsnet に決定**★ franklin1 が公開できないのは能力でなく**兄が席を占有しているから**（funnel 3枠、店は4軒。2026-07-16 実測で 443/8443/10000 とも 200 = 満席、franklin1 は `X402_PUBLIC_URL` すら持てない）。**案C(各自の Tailscale ノード) を採用** — tsnet は「1ノード=3枠」なので枠問題が構造的に消える。案A/B(Cloudflare/クラウド)は却下: card 必須 or 移植コスト、hosting 11候補を全て実測で潰した(→ `docs/reference/2026-07-16-independent-hosting-for-each-ai.md`)。**統合は却下（INV-INDEP 違反）** | franklin1 が他の instance の状態と無関係に公開 URL を持ち、稼げる | ★次★ 手順は T2b-1/T2b-2 |
| **T2b-1** | TS_AUTHKEY を取る | 鍵が file にあり fingerprint で照合できる | ★DONE 2026-07-16★ 下記 |
| **T2b-2** | tsbridge を通す — 3ノードが各自の FQDN で Funnel を上げる | 外部から実 HTTP が返る。franklin1 が**自分の**公開 URL を持つ | ★DONE 2026-07-16 05:15★ 下記 |
| **T2b-3** | tsbridge を launchd 化 | 殺しても蘇り、外部から届く | ★DONE 2026-07-16 05:26★ 下記 |
| **T2b-4** | 各 loop に**自分の** `X402_PUBLIC_URL` を配る | 3 loop の**実プロセス env**が各自の FQDN を持つ | ★DONE 2026-07-16 05:38★ 下記 |
| **T2b-5** | loop の wake を観測（**手を出さない**）。`run.sh` を叩いたら「Dais が稼がせた」= INV-F 違反 | 下記4段の観測点。④だけが「稼いだ」 | ★観測したら T0' が出た（下記）。第1〜0層が先★ |
| **★T0'★** | ★最優先★ **agent に「稼ぐ能力」を装備させる**（= Anicca の仕事そのもの）。①各 instance に**自分の** ClawRouter（`BLOCKRUN_PROXY_PORT` + `BLOCKRUN_WALLET_KEY`）②franklin2 に**鍵を与える**（今は無い）③franklin1 の使える金(Solana $12.21)を脳の支払いに繋ぐ | 3体とも `THINK failed` が消え、**自分の金で**自分の思考を買っている | ★次★ |

### ★★T0': 「なぜ稼がないのか」の真の答え — 金ではなく能力の問題だった（2026-07-16 05:45 実測）★★

**Anicca / Agora の仕事の定義**: agent は稼ぐ能力を持って生まれない。**能力(skill/鍵/脳/席)を装備させるのが我々の仕事。**
装備が無いのは agent の失敗ではなく、**我々がまだ渡していない**という事実。以下は「壊れている箇所」ではなく「未装備の一覧」。

**層の全体像（下ほど根が深い。上から直しても無意味）**:
```
第4層  実績$0だから合理的に拒否      ← claude-p はここ（脳は動いている）
第3層  Bazaar 掲載に settle 1回必要   ← 鶏と卵（T3 で公式仕様から確定済）
第2層  住所(X402_PUBLIC_URL)が空      ← ★2026-07-16 装備完了(T2b-4)★
第1層  脳が無い（429・財布空）        ← ClawRouter wallet = $0.00、しかも3体で共有
第0層  ★鍵が無い / 金が動かせない★    ← ここが底。ここを装備しないと上は全部無意味
```

**★第0層: 誰が「金を使える」のか（`wallets.json` の `keyRef` 実測。鍵は出さず有無のみ）★**

| instance | wallet | chain | address | 鍵 | 使えるか |
|---|---|---|---|---|---|
| **franklin1** | sol-main | solana | `8Fpqd…PCV9` | **YES** | **$12.21 USDC + 0.040 SOL を使える** |
| franklin1 | polymarket | polygon | `0xda4b6E34…` | YES | — |
| franklin1 | ★`0x3EcCAD24…`(x402 受取先)★ | base | — | **wallets.json に無い** | **Base $4.48 は受取専用 = 動かせない** |
| **franklin2** | ★`wallets.json` が存在しない★ | — | — | **鍵ゼロ** | **1円も動かせない。受け取る口はあるが払う口が無い** |
| **claude-p** | base-main | base | `0x810f6d61…` | YES | $1.98 |
| claude-p | polymarket | polygon | `0x904B50d2…` | YES | $3.24 |
| claude-p | hl-margin | hyperliquid | `0x810f…` | YES | $7.72(座礁中) |
| claude-p | telemetry | polygon | `0x02Bb6b2a…` | YES | — |

→ **franklin2 は稼げないのではなく、稼ぐ手段を装備されていない。**自分の脳を買えず、self-pay で着火もできず、
  何をどう配線しても**構造的に永久に $0**。self-funded citizen を名乗れる状態になかった。**鍵を与えるのが我々の仕事。**
→ franklin1 も Base の $4.48 は動かせない。使えるのは Solana の $12.21 のみ。

**★第1層: 脳の財布（実測）★**
```
$ clawrouter wallet
  Payment Chain: base
  Base (EVM):  0x2f4816a5d3494A2F2fE217C191B360762B8A1B2e
  Solana:      DoiXYe63kKyY6Eff4fwqzoccnMBXa4E1PVWegA9Wu9L8
  Balance:     $0.00 (USDC)
  ⚠ Empty — fund wallet or use free models
```
- **3体が1つの財布を共有**（全員 `OPENAI_BASE_URL=http://127.0.0.1:8402/v1`）→ **誰かが全部燃やせる = INV-INDEP 違反**。
  tsbridge で席を独立させた意味が消える。franklin1 の金で claude-p が考える構図。
- 空 → 有料モデル要求が無料へ降格 → 日次上限 → 429。自分の手で再現:
  `{"code":"FREE_MODEL_FAILED","debug":"429 Rate limit exceeded: **free-models-per-day-high-balance**"}`
  → **`per-day` = 日次上限。無料に依存する限り 3体は毎日脳死する。**一時障害ではなく構造。
- `eco` が一度だけ通り `free/gpt-oss-120b` にフォールバックしたが、直後に同モデルを直叩きすると 429。
  **無料プールは共有・不安定。「別の無料モデルに変える」は解決ではない**（運任せの延命）。

**★分離は可能（公式 env、`clawrouter --help` 逐語）★**
```
BLOCKRUN_WALLET_KEY     Private key for x402 payments (auto-generated if not set)
BLOCKRUN_PROXY_PORT     Default proxy port (default: 8402)
```
→ **instance ごとに自分の router + 自分の鍵**にできる。tsbridge と同じ「1体1つ」の形。
   franklin plist に既にある `FRANKLIN_PROXY_PORT=8402` は、元々そう設計する意図だった痕跡。

**装備する順（下の層から。上から直しても動かない）**:
1. franklin1 = 唯一「金 + 鍵」が揃う → 自分の router + 自分の sol 鍵 → **$12.21 で自分の脳を買う**。最初の実証個体
2. claude-p = 鍵あり・金少 → 自分の router + base 鍵
3. franklin2 = **鍵を装備する**（生成 or 付与）+ 種銭 → ここで初めて経済主体になる

★注: 「1体1 router」は「1体1ノード(tsbridge)」と同じ原理 — **共有資源は必ず奪い合いになる**。
   席では claude-p が2枠占有して franklin1 を締め出した。財布でも同じことが起きる。**先に分ける。**
| **T2b-6** | claude-p 店②(:8411 / `0x810f` / $0.011 の唯一の稼ぎ手)を専用ノードへ移す。tsbridge に4つ目の service を足す必要あり。**最後に触る** | :8411 が自分の FQDN で配信し、売上が落ちない | T2b-5 の結果を見てから |

### ★T2b-4: franklin1 に広告を配線した（2026-07-16 05:31）。真因の全貌が出た★

```
ai.anicca.franklin-loop.plist に追加:
  X402_PUBLIC_URL = https://franklin1.tail7a0ba4.ts.net
```
検証: `plutil -lint` OK。reload 後、**プロセスの実 env**を `ps eww` で確認 — pid 59045 が
`X402_PUBLIC_URL=https://franklin1.tail7a0ba4.ts.net` を実際に保持（plist を読んだだけで満足しない）。

**★INV-F は既に満たされていた（朗報。STATUS の従来認識を訂正）★**

`launchctl list` 実測:
```
3052   1  ai.anicca.x402-seller-8414   ← franklin1 の loop 自身が立てた seller。稼働中
94909  1  ai.anicca.x402-seller-8413   ← franklin2 の loop 自身が立てた seller。稼働中
-      1  ai.anicca.x402-seller-8412   ← claude-p のみ未起動
```
T1 の修正(依存を持つ copy を exec / bind 失敗で exit 1 / ローカル宣言)が効いており、
**franklin1 と franklin2 は既に「自分で店を立てる」に成功している**。手書き boot script に依存していない。

**★$0 の真因は「空の PUBLIC_URL」だった — 実物★**

```
ai.anicca.x402-seller-8414.plist（loop が生成した実物）:
  X402_PAYTO      = 0x3EcCAD24794ca298D25378E9902A251322ea8749
  X402_PUBLIC_URL =                ← ★空文字★
  X402_PORT       = 8414
```
結果、manifest が**相対パス**を吐いていた:
```json
{"x402Version":1,"resources":[{"resource":"/research", "price":"$0.003", ...}]}
                                          ↑ 相対。買い手はどこへ払えばいいか分からない
```
`serve.mjs:47` 逐語: *"(root cause 2026-07-14; cf coinbase/agentkit#877). **Set X402_PUBLIC_URL to the https funnel origin.**"*
→ **Bazaar は絶対 URL を要求する。** franklin1 は店も商品7点も manifest も持っていたが、**住所が空欄のチラシ**を配っていた。

**★伝播経路は健全（実コードで確認）★**

| 経路 | 実測 |
|---|---|
| `run.sh:303` | `<key>X402_PUBLIC_URL</key><string>${X402_PUBLIC_URL:-}</string>` → loop の env から seller plist へ書く。**`:-` の既定が空だったので空が書かれていた**。loop plist に値が入った今、次の wake で実 URL が書かれる |
| `env-filter.mjs:19` | `/(_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY)$/` = **denylist のみ**。`X402_*` は元から素通り。→ 「ALLOW set に X402_PUBLIC_URL を追加した」という前セッションの記述が**虚偽だった**ことの再確認（追加は不要だった） |

**★T2b-4 DONE — 3体とも自分の住所を持った（2026-07-16 05:38）★**

`ps eww` でプロセスの**実 env** から確認（plist を読み返して満足しない）:

| pid | ANICCA_HOME | port | X402_PUBLIC_URL |
|---|---|---|---|
| 59045 | `.blockrun` (franklin1) | 8414 | `https://franklin1.tail7a0ba4.ts.net` ← **新規**（元は無し = $0 の真因） |
| 68389 | `.franklin2-home/.blockrun` (franklin2) | 8413 | `https://franklin2.tail7a0ba4.ts.net` ← 元は共有 `:10000` |
| 70525 | `.anicca-founder` (claude-p) | 8412 | `https://claude-p.tail7a0ba4.ts.net` ← **新規** |

稼ぎ頭は無傷: reload 後も `:8411`(pid 628) と `:8412`(pid 577) は LISTEN 継続。

★**観測の失敗を1つ記録**: 最初 `ANICCA_INSTANCE` で loop を列挙し、claude-p が出てこないので「死んだか」と疑った。
実際は **claude-p の plist に `ANICCA_INSTANCE` が無い**だけで、loop は pid 631 で生きていた。**壊れていたのは観測の方**。
`ANICCA_HOME` は全 instance が持つので、これを軸にすれば漏れない（identity の軸 = HOME、という T0 の結論と同じ）。
一般法則: **列挙のキーに「全個体が持つとは限らない属性」を使うと、存在するものを不在と報告する。**

**次にやること = 何もしない。loop の wake を待って観測する。**
`run.sh` を手で叩かない（叩けば「Dais が稼がせた」になり INV-F 違反 → [[feedback_watch_loops_never_do_their_work]]）。

観測点（全て loop 側が動かすもの。①→④の順に進む）:
```
① seller plist(x402-seller-8414) の X402_PUBLIC_URL が空 → 実 URL に変わる
     run.sh:303 が loop の env から書き直す。10分毎の wake で発火
② manifest の resource が "/research" → "https://franklin1.tail7a0ba4.ts.net/research"
③ bazaar-scan.mjs が 0x3EcC の resource を返す
     ★ここで詰まる公算大★ T3 で公式仕様から確定済み = 掲載には settle が1回必要
     ("verify alone is not enough")。franklin1 の loop が self-pay を1回通す必要がある
     (INV-7 で収益に数えない、着火専用) = T4a。公開 URL がやっと在るので今アンブロック
④ verify-inflow.mjs の inflow が $0 でなくなる ← ★ここだけが「稼いだ」★
```

### ★T2b-3 DONE — 席が永続化した（2026-07-16 05:26）★

`~/Library/LaunchAgents/ai.anicca.tsbridge.plist`（`RunAtLoad` + `KeepAlive` + `ThrottleInterval=30`。
tsnet はノード登録に数秒かかるので再起動を煽らない）。log = `~/.tsbridge/logs/tsbridge.{out,err}.log`。

**自己申告でなく実測で確認した2点**:

| 検証 | 実測 |
|---|---|
| launchd 移行後も**外部**から届くか | `r.jina.ai`(tailnet 外の第三者)経由で `https://franklin1.tail7a0ba4.ts.net/` の全文取得。**payTo `0x3EcCAD24…` = franklin1 自身**。商品7点 + `/.well-known/x402.json` + `llms.txt` を公開配信中 |
| KeepAlive は本物か | `kill -9 52686` → 35秒後 → **pid 53290 で自力蘇生**。launchctl の `0` を信じず、実際に殺して確かめた |

★副産物: franklin1 の店は**既に商品7点を公開している**（research $0.003 / whois $0.002 / stock-quote $0.003 / calc・DNS・JSON-flatten・compound-interest 各 $0.001）。`/.well-known/x402.json` も**実装済み**（T8 で「実装する」としていたが既に在る。T8 の記述は要修正）。franklin1 に足りないのは店でも商品でもなく、**Bazaar への広告(=`X402_PUBLIC_URL`)だけ**。

### ★金の帰属（2026-07-16 実測。混線ゼロ）★

boot script 逐語: franklin1 = *"franklin1's **OWN** payTo (receiving-only, no key needed here)"* /
franklin2 = *"franklin2's **OWN** payTo"* / :8412 = *"**claude-p's own wallet**"* / :8411 = *"payTo = **founder 0x810f**"*。
→ **:8411 と :8412 は両方 claude-p のもの。claude-p は店を2軒持っている。** agent 3体に seller 4本ある理由がこれ。

| agent | wallet | 48h 外部売上 | 件数 | 自己支払(seed) |
|---|---|---|---|---|
| franklin1 | `0x3EcCAD24…` | **$0** | 0 | 0 |
| franklin2 | `0xe7747Fd8…` | **$0** | 0 | 0 |
| claude-p 店① | `0x810f6d61…` | $0.011 | 9 | 9件 / $0.016 |
| claude-p 店② | `0x904B50d2…` | $0.006 | 6 | 7件 / $0.012 |

★**席を奪っていたのは claude-p だった**: `:443`(店①) + `:8443`(店②) で3枠中2枠を占有 → franklin2 が `:10000` → **franklin1 は席ゼロ**。
franklin1 の $0 は能力でも設定ミスでもなく、**兄が2軒出店していたから**。これが INV-INDEP 違反の実体。
→ tsbridge がこれを**裁定なしで**解いた。Personal 無料枠は *"Unlimited user devices"* なので、**誰も何も諦めなくていい**（claude-p は2軒維持のまま、Franklin 兄弟も自分の席を持てる）。

★**まだ経済ではない（実測が2つそう言っている）**:
1. **自己支払 > 外部売上**。0x810f = 外部 $0.011 vs self-pay $0.016 / 0x904B = 外部 $0.006 vs self-pay $0.012。着火用の自演の方が金額が大きい
2. **同じ bot が両方の店を舐めている**。`0xaf5bb59a58a3a05da3d7308d53de36836bc085ae` が 0x810f と 0x904B の**両方**に、`0x670fa140…` は 0x810f に2回。
   STATUS の「8個の EOA が $0.001 ずつ単発」「BlockRun 自己申告で 47% は non-organic」と整合 → **需要ではなく巡回 bot**。T9(高単価化)が本丸である裏付け

### ★T2b-2 DONE — franklin1 が初めて自分の公開 URL を持った（2026-07-16 05:15 実測）★

**「1台=3枠」は消滅した。実測で確定。**

```
tsbridge 1プロセス → tsnet ノード3個。各ノードが独自 IP・独自 FQDN・独自 :443
  claude-p    100.73.148.91     https://claude-p.tail7a0ba4.ts.net
  franklin1   100.114.193.59    https://franklin1.tail7a0ba4.ts.net    ← 兄と無関係な自分の席
  franklin2   100.81.5.86       https://franklin2.tail7a0ba4.ts.net
```

**① ルーティングが正しいことの証明（payTo が3つとも別）**:

| FQDN | payTo（実 HTTP から） |
|---|---|
| franklin1.tail7a0ba4.ts.net | `0x3EcCAD24794ca298D25378E9902A251322ea8749` ← franklin1 自身 |
| franklin2.tail7a0ba4.ts.net | `0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9` ← franklin2 自身 |
| claude-p.tail7a0ba4.ts.net | `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74` |

★注: claude-p の :8412 は `0x904B`(PM proxy) に払わせている。STATUS 冒頭の表では claude-p の x402 wallet = `0x810f` だが、:8412 の実 payTo は `0x904B`。**どちらが意図か未確定**（STATUS.md 79行「payTo 0x904B は誤設定 → 誤り。意図的」と整合はする）。T2b-3 で確定させる。

**② Funnel(公開)であることの証明 — ここを間違えかけた**:

Mac Mini から curl して 3つとも 200 だったが、**Mac Mini は tailnet の中にいるので、この 200 は公開の証拠にならない**（tailnet 内部で見えただけかもしれない）。自分の位置を証拠に混ぜる誤り。→ [[feedback_my_own_scripts_are_self_report_not_evidence]] と同型。

外部から2段階で確定させた:

| 検証 | 結果 |
|---|---|
| 公開DNS `dig +short @8.8.8.8 franklin1.tail7a0ba4.ts.net` | `103.84.155.217 / 103.84.155.153` = **実売実績のある `aniccanomac-mini-1` と同じ Tailscale ingress IP**。公開解決される |
| 第三者サーバ `r.jina.ai` 経由で実 HTTP | **成功**。`URL Source: https://franklin1.tail7a0ba4.ts.net/` + 商品 JSON 全文。**公開インターネットから到達可能** |
| 外部プロキシ `api.allorigins.win` | 500 / 522 で失敗。**Funnel の否定材料にはしない**（プロキシ側の障害と区別できない）。曖昧な結果は結論にしない |

**③ 未確定だった3件の決着**:

| 問い | 実測 |
|---|---|
| tailnet の台数上限に触れるか | **触れない**。Personal($0) は *"Unlimited user devices"*（公式 pricing）。3ノード追加後も全て稼働 |
| tsnet ノードに Funnel を許す ACL が要るか | **不要だった**。ACL を1行も触らずに Funnel が立った（既存 tailnet の nodeAttrs を member として継承したと推定。**推定であり未検証**） |
| Funnel 帯域の実数値 | **依然不明**。公式は数値を書かず *"non-configurable bandwidth limits"* のみ。売上が伸びた時に初めて効く。**当面は blocker でない** |

**④ 壊していないことの確認**: 既存3枠 `:443` / `:8443` / `:10000` は tsbridge 起動後も全て 200。稼ぎ頭(:10000 で $0.011 実績)は無傷。

**⑤ 使ったもの**: `jtdowney/tsbridge`(300★) を `go install`（48MB、Go 1.26.0）。config = `~/.tsbridge/tsbridge.toml`。**seller のコードは1行も触っていない**。

**⑥ 残る脆さ（T2b-3）**: 今の tsbridge は `nohup` の裸プロセス。**Mac 再起動で消える。**launchd 化するまで、この成果は揮発する。

### ★T2b-1 DONE — 鍵は取れた。ただし経路を変えた（2026-07-16）★

`~/.tsbridge/authkey`（61 bytes、mode `600`、id `kXpbFDuNCM11CNTRL`、reusable、期限 Oct 14 2026）。

**当初計画(OAuth client → get-authkey)は破棄した。理由は3つ、全て実測**:

| # | 実測 | 出典 |
|---|---|---|
| 1 | **公式自身が近道を指定している** — *"To use it, generate an auth key from the Tailscale admin panel and run the demo with the key: `TS_AUTHKEY=<yourkey> go run tsnet-funnel.go`"* | `tsnet/example/tsnet-funnel/tsnet-funnel.go` |
| 2 | **`get-authkey` は不要だった** — 採用した tsbridge が OAuth を**内製**しており、`auth_key` と `oauth_client_id/secret` の**どちらでも**食える。恒久化は config の差し替えだけ | tsbridge `docs/configuration-reference.md` |
| 3 | OAuth/tag/ACL は**恒久化の仕事**であって**検証の仕事ではない**。tsnet が席問題を本当に解くか未確認の段階で恒久化の配管から始めるのは順序が逆（Dais 裁定「shed で行け」） | — |

**同時に実測できたこと**:

| 問い | 実測 |
|---|---|
| Funnel は無料枠で使えるか | **YES**。公式 KB 1223 逐語: *"Tailscale Funnel is available for all plans"*。admin 実機でも plan = **Free** を確認 |
| auth key の最長寿命 | **90日**（admin ダイアログ: "Must be between 1 and 90 days"） |
| ★node key も失効する★ | admin の Tags トグル逐語: *"Devices authenticated by this key will be automatically tagged. **This will also disable node key expiry for the device.**"* → **tag の無いノードは node key がいずれ失効し、再認証 = human loop が数ヶ月後に蘇る**。恒久 human ゼロには **auth key 失効(90日)** と **node key 失効** の**2つ**を殺す必要がある。前者は tsbridge の OAuth、後者は tag |

★**事故と是正（記録）**: 最初の鍵を「取れたか確認」するつもりで eval の返り値に載せ、**transcript に平文で漏らした**。是正: クリーンな鍵を DOM→file 直結で再発行（一度も表示せず）→ fingerprint で照合 → 漏洩鍵 `kpj5iWGcnZ11CNTRL` を revoke → **リロードして** 一覧から消滅を実測 → ローカルコピーを rm。
一般法則 → [[feedback_capture_secrets_dom_to_file_never_through_stdout]]。「ローカル transcript だから安全」は誤り — handover skill は引き継ぎノートを**メール送信**し、token-optimizer は checkpoint を**ディスクに書く**。実際に外へ出る経路がある。

### ★採用 repo: `jtdowney/tsbridge`（300★）— 単独で丸ごと採用、混ぜない★

*"A lightweight proxy manager built on Tailscale's tsnet library that enables **multiple HTTPS services on a Tailnet**"* = 我々の形そのもの。

| 確認項目 | 実測 |
|---|---|
| Funnel(公開)をやるか | **YES**。`internal/tsnet/interfaces.go`: `ListenFunnel(network, addr string) (net.Listener, error)`。`THREAT_MODEL.md`: *"Funnel mode exposes services to the public internet"* |
| service ごとに FQDN | `docs/configuration-reference.md`: `name = "api"` → *"becomes api.<tailnet>.ts.net"* |
| 認証 | `auth_key` / `oauth_client_id+secret` の両対応。`default_tags`(OAuth 時必須) |

**却下した候補**: `almeidapaulopt/tsdproxy`(1649★) = Docker label 駆動だが我々の seller は launchd の node プロセス → **star は多いが形が違う**。`nfielder/ts-infi-authkey`(0★) = 不要（tsbridge が内製）。

**採る形**（seller のコードは1行も触らない。前段に置くだけ）:
```toml
[tailscale]
auth_key_env = "TS_AUTHKEY"          # 恒久化時は oauth_client_id_env/oauth_client_secret_env + default_tags へ
state_dir    = "/Users/anicca/.tsbridge"

[[services]]
name = "franklin1"                   # → franklin1.tail7a0ba4.ts.net:443（自分の席）
backend_addr = "localhost:8414"
funnel_enabled = true                # 既定 false。公開に必須

[[services]]
name = "franklin2"
backend_addr = "localhost:8413"
funnel_enabled = true

[[services]]
name = "claude-p"
backend_addr = "localhost:8412"
funnel_enabled = true
```
| **T2c** | franklin1/franklin2 の plist に `ANICCA_WALLET_ADDRESS` を設定（2026-07-16 実測: **両方とも無い**。claude-p だけ有る）。franklin2 のログ `invalid wallet address: unknown` の直接原因 | 両 loop のログから `using "unknown"` が消える | T2b-2 と並行可 |
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
| **席(T2b)** | [tailscale/tailscale](https://github.com/tailscale/tailscale) `tsnet/` | 24k+ | **"Multiple independent Tailscale nodes can run within a single binary"** = 各 instance が独立ノード = 各自 443/8443/10000。席の奪い合いが消える |
| **認証(T2b-1)** | [tailscale/tailscale](https://github.com/tailscale/tailscale) `cmd/get-authkey/main.go` | 同上 | **OAuth client から auth key を自動生成する公式ツール。自作禁止。** env `TS_API_CLIENT_ID`/`TS_API_CLIENT_SECRET`、flag `-tags`(必須)/`-reusable`/`-ephemeral`/`-preauth` |

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
