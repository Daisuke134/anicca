# x402scan.com 登録の実装と実測（XSCAN-1、2026-07-17）

調査方法: `gh api`(Merit-Systems/x402scan の実ソース) + `crwl`(x402scan.com, agentic.market, agent402.tools) + `npm view` + 自分のwallet鍵での実HTTP実行(curl/node)。WebSearch/WebFetch は不使用。

## 結論（要約）

- **v1拒否は消えた**: franklin1・franklin2(共に`serve-v2.mjs`でv2化済み)を x402scan.com に実登録 → 両店とも `success:true, registered:8, total:8, failed:0` で受理。T8 前提の「v1応答だと"migrate to v2"で拒否」は解消済み(v2化がブロッカーを解いた)。
- **登録は無認証フォームPOSTではない**: `/resources/register` の見た目(URL入力→Add)から誤解しやすいが、実体は **SIWX(Sign-In-With-X, EIP-4361/CAIP-122)ウォレット認証必須**の API。公式クライアント`wrapFetchWithSIWx`(`@x402/extensions`)には**SIWX単独チャレンジ(`accepts:[]`)を処理できないバグ**があり、低レベルprimitiveで自前実装が必要だった(詳細は下記)。
- **agent402.tools**: 無認証・無KYCの `POST /api/index/register {origin}` で即時登録可能。franklin1(標準443ポート)は成功、**franklin2は失敗**(`"origin must use the default https port"` — franklin2の`:10000`はagent402.toolsが拒否する非標準ポート)。
- **agentic.market**: 別登録UIなし。「Bazaarにindexされていれば自動的に載る」仕様(FAQ実測)。CDP Bazaar拡張(`declareDiscoveryExtension`)への切替は別タスク(v1-v2-compat研究の既知の未完了項目)。

## 1. x402scan.com 登録APIの実装（ソース実測）

`gh api search/code` で実ハンドラを特定:
- ルート: `apps/scan/src/app/api/x402/registry/register-origin/route.ts`
  ```ts
  export const POST = withCors(
    router.route('x402/registry/register-origin')
      .siwx()
      .body(registryRegisterOriginBodySchema)
      .handler(({ body }) => handleRegistryRegisterOrigin(body))
  );
  ```
  `.siwx()` — Merit-Systemsの`@agentcash/router`(npm、`did-auth-challenge`+`viem`依存)が付与するミドルウェアで、SIWXヘッダ無しのリクエストは 402 + `extensions['sign-in-with-x']` チャレンジを返す。
- ハンドラ本体(`apps/scan/src/app/api/x402/_handlers/registry-register-origin.ts`): `{origin}` を受け取り、サーバ側で `fetchDiscoveryDocument(origin)`(=先方の`/openapi.json`か`/.well-known/x402`をこちらから取得)→ `registerResourcesFromDiscovery(...)` を実行。**マニフェストのアップロードではなく、登録者のウォレット認証だけを求め、実データはx402scan自身がこちらのopenapi.jsonへ能動fetchして検証する**設計。
- `apps/scan/src/lib/router.ts`(`createRouter`のdiscovery.guidance文字列、原文):
  > "Registry write endpoints (register, register-origin) require SIWX wallet authentication (use fetch_with_auth)."

`docs/DISCOVERY.md`(`raw.githubusercontent.com/Merit-Systems/x402scan/main/docs/DISCOVERY.md`)が仕様書。要点:
- discovery優先順位: `/openapi.json`(推奨) → `/.well-known/x402`(互換) → endpoint-only fallback。
- `/openapi.json`の各支払いオペレーションは `x-payment-info.protocols`+`price`必須、402応答は非空`accepts`+Bazaar形式input schema+atomic単位金額が必要。
- `402 + accepts:[] + extensions["sign-in-with-x"]` は「SIWX認証専用、payableでない」ケースとして明記されている — これがまさに register-origin 自体の挙動。

## 2. `wrapFetchWithSIWx` のバグ（実測、@x402/extensions@2.17.0）

`@x402/extensions/sign-in-with-x`の公式ヘルパー`wrapFetchWithSIWx(fetch, signer)`は「402を受けたら署名して再送」を自動化する設計だが、ソース実測(`node_modules/@x402/extensions/dist/esm/chunk-LMLJI6VE.mjs:701-740`):

```js
function wrapFetchWithSIWx(fetch, signer) {
  return async (input, init) => {
    ...
    const paymentNetwork = paymentRequired.accepts?.[0]?.network;
    if (!paymentNetwork) { return response; }   // ← ここで詰む
    const matchingChain = siwxExtension.supportedChains.find(
      (chain) => chain.chainId === paymentNetwork
    );
    ...
  };
}
```
支払い(`accepts[0].network`)とSIWXのマッチングでchainを決めるロジックになっており、**支払いを伴わない「SIWX単独」チャレンジ(`accepts:[]`)では`paymentNetwork`がundefinedになり、署名フローに一切入らずそのまま元の402を返す**。x402scanのregister-origin/registerは正にこの「SIWX単独」ケースなので、公式ラッパーをそのまま呼んでも常に402で終わる(実機で再現済み)。

回避策: 402ボディの`extensions['sign-in-with-x'].info`は`chainId`+`type`を含む完全な`CompleteSIWxInfo`相当なので、`createSIWxPayload(info, signer)` + `encodeSIWxHeader(payload)`を直接呼び、`SIGN-IN-WITH-X`ヘッダを付けて再送すれば動く(`wrapFetchWithSIWx`内部の後半と同じロジックを、chain-matching抜きで手動実行)。

## 3. 実装（このセッションでの新規スクリプト）

`~/anicca/skills/earn/x402-sell/register-x402scan.mjs`(新規、anicca repo commit予定):
- `loadEvmKey()`(`../lib/resolve-identity.mjs`、ANICCA_HOMEゲート)で店ごとの鍵を解決 → `privateKeyToAccount`(viemの`PrivateKeyAccount`は`@x402/extensions`の`EVMSigner`インターフェースをそのまま満たす: `.address`+`.signMessage`)。
- 1回目POST(`{origin}`)→ 402を受けたら`challenge.extensions['sign-in-with-x'].info`から`createSIWxPayload`→`encodeSIWxHeader`→ 2回目POSTに`SIGN-IN-WITH-X`ヘッダを付けて再送。
- 秘密鍵は一切標準出力に出さない(署名後のアドレスのみ表示)。

使い方:
```bash
ANICCA_HOME=~/.blockrun ORIGIN=https://franklin1.tail7a0ba4.ts.net \
  node ~/anicca/skills/earn/x402-sell/register-x402scan.mjs
ANICCA_HOME=~/.franklin2-home/.blockrun ORIGIN=https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000 \
  node ~/anicca/skills/earn/x402-sell/register-x402scan.mjs
```

## 4. 実測結果

### franklin1
```
POST https://www.x402scan.com/api/x402/registry/register-origin origin: https://franklin1.tail7a0ba4.ts.net
HTTP status (1st, unauthenticated): 402
HTTP status (2nd, SIWX-signed): 200
body: {"success":true,"registered":8,"siwx":0,"public":0,"apiKey":0,"failed":0,"skipped":0,
       "deprecated":0,"total":8,"source":"openapi",
       "warning":"Add info.contact.email to your openapi.json ..."}
```
署名アドレス: `0x3EcCAD24794ca298D25378E9902A251322ea8749`(franklin1本人)。

### franklin2
```
POST https://www.x402scan.com/api/x402/registry/register-origin origin: https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000
HTTP status (1st, unauthenticated): 402
HTTP status (2nd, SIWX-signed): 200
body: {"success":true,"registered":8,"siwx":0,"public":0,"apiKey":0,"failed":0,"skipped":0,
       "deprecated":0,"total":8,"source":"openapi", "warning":"Add info.contact.email ..."}
```
署名アドレス: `0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9`(franklin2本人)。

両店とも `source:"openapi"` = `/openapi.json`(DISCOVERY.mdの推奨経路)からの自動発見で8/8全商品が登録された。`warning`は`info.contact.email`が無いことへの軽微な指摘のみ(登録自体はブロックされない)。

## 5. 掲載確認（$0.01の自己支払いで実データ照会、on-chain確認込み）

`GET /api/x402/registry/origin?url=<origin>`はx402scan自身のx402課金API($0.01)。`buyer-cdp-v2.mjs`(v2買い手、各店自身のウォレットで自己決済)で実際に叩いて確認:

- franklin1: tx `0xefd46b8078e5242b9a69fdadeea69d215bd89c89943e559dac437965f46bc3f8`(Base mainnet、`PAYMENT-RESPONSE.success:true`)。応答body に `originId:"b9b53de8-2bf6-473c-be07-43b1e9d8316b"`、`resource:"https://franklin1.tail7a0ba4.ts.net/compound-interest"`等。
- franklin2: tx `0x4df32b1e7f862be9cec15694791b86080c050cbe11491c3f823ad4c983efec6c`。`originId:"af9283bc-b1f8-4e50-b474-abb1f5d082e0"`、`resource:".../whois"`等。

さらに公開ページ(`crwl`、認証不要)で目視確認 — 両店とも「Anicca x402 seller」として `v2` タグ付きで8商品全部が一覧表示される:
- franklin1: https://www.x402scan.com/server/b9b53de8-2bf6-473c-be07-43b1e9d8316b
- franklin2: https://www.x402scan.com/server/af9283bc-b1f8-4e50-b474-abb1f5d082e0

`/all`・`/resources`のトップ一覧(Most Used等)には出ない — これらは**過去24hの決済アクティビティ順**のランキングであり、登録直後で取引がまだ無い(このセッションの検証用$0.01×2件のみ)ため下位に埋もれているのが原因。掲載自体はサーバページで確定済み。

## 6. agent402.tools（無料・無KYC、`POST /api/index/register`）

```
curl -X POST https://agent402.tools/api/index/register -d '{"origin":"https://franklin1.tail7a0ba4.ts.net"}'
→ 200 {"listed":true,"origin":"...","seller":{"toolCount":2,"networks":["base"],"routable":true,"health":1}}

curl -X POST https://agent402.tools/api/index/register -d '{"origin":"https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000"}'
→ 400 {"error":"origin must use the default https port"}
```
franklin1(tsbridgeの標準443ポート)は即座に受理。**franklin2は`:10000`という非標準ポートを理由に拒否** — x402scanは受理するが agent402.tools はポート制約がより厳しい(市場ごとに要件が異なる実例)。franklin2を443化する場合は別途 franklin1 同様の tsbridge リバースプロキシが必要(次アクションとして残す、本タスクのスコープ外)。

## 7. agentic.market（Coinbase運営、CDP Bazaar連動）

`/validate`ページのFAQ(crwl実測、原文):
> "Do I need to register to get my service/endpoints discoverable via Search? If your service/endpoints are indexed on the Bazaar, you'll automatically show up on agentic.market."

→ **別途の登録アクションは不要**(KYCも不要)。ただし前提はBazaarへの正しいindex化で、`docs/research/2026-07-17-x402-v1-v2-compat.md`が既に指摘済みの「v2化しただけではBazaar discoverabilityが弱い(`declareDiscoveryExtension`未実装)」問題がそのまま効いてくる — agentic.marketでの露出改善はBazaar拡張タスク側で解決すべき事項であり、本タスク(x402scan登録)の追加作業は無い。

## 引用まとめ
- `github.com/Merit-Systems/x402scan/blob/main/apps/scan/src/app/api/x402/registry/register-origin/route.ts` — `.siwx().body(...).handler(...)`
- `github.com/Merit-Systems/x402scan/blob/main/apps/scan/src/lib/router.ts` — "Registry write endpoints (register, register-origin) require SIWX wallet authentication"
- `raw.githubusercontent.com/Merit-Systems/x402scan/main/docs/DISCOVERY.md` — discovery precedence, SIWX-auth-only 402 semantics
- `node_modules/@x402/extensions/dist/esm/chunk-LMLJI6VE.mjs:701-740`(インストール済み2.17.0) — `wrapFetchWithSIWx`のchain-matchingバグ
- `www.x402scan.com/resources/register`, `/discovery`(crwl) — 見た目はURL登録フォームだがAPIはSIWX必須
- `agent402.tools/sell`, `POST /api/index/register`(実curl) — 無認証・無KYC・0%手数料、ポート要件あり
- `agentic.market/validate`(crwl) — Bazaar連動、別registration不要のFAQ原文
