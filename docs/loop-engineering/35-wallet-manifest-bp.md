# Wallet Manifest — Best Practice 調査（2026-07-13）

## 問題
自律 AI が複数チェーン/複数 venue の wallet を持つとき、真実が env var / スクリプト内導出 / 人間用 doc に散らばると、loop が残高を誤認する（実測: $18 持っているのに $1.95 と誤認して稼ぐ skill を自己停止した）。

## アンチパターン（一次情報）

1. **env var 散らばり = デバッグ不能の実例**
   - Source: "We Followed the 12-Factor App. It Made Debugging Impossible" — https://medium.com/lets-code-future/we-followed-the-12-factor-app-it-made-debugging-impossible-976cd0bc40e7
   - 引用: 「With 12-factor? Config is scattered across 5 different systems and half of it is invisible.」「New one in Vault (our source of truth) / Old one in Kubernetes (what the app was using)」→ **複数の "source of truth" が並立すると片方が stale になり気づけない**。

2. **同じ wallet を指す env var が4通り存在する実例（我々の問題そのもの）**
   - Source: elizaOS/eliza, `plugins/plugin-polymarket/src/routes.ts` — https://github.com/elizaOS/eliza/blob/main/plugins/plugin-polymarket/src/routes.ts
   - 引用（コード内コメント）: 「Env keys consulted (in order) to resolve the agent's Polygon wallet... POLYMARKET_WALLET_ADDRESS is the venue-specific override; the STEWARD/managed keys mirror the resolution the sibling Hyperliquid app-plugin uses so a single managed EVM address powers both venues.」
   - 実コード: `POLYMARKET_ADDRESS_ENV_KEYS = ["POLYMARKET_WALLET_ADDRESS", "POLYMARKET_ADDRESS", "STEWARD_EVM_ADDRESS", "ELIZA_MANAGED_EVM_ADDRESS"]` という4段 fallback chain。→ **本番 OSS agent framework でも同じ轍を踏んでいる**。1つの address に4つの env var 名が対応し得る = 我々の `ANICCA_WALLET_ADDRESS` / `ANICCA_EXTRA_WALLETS` 分裂と同型のアンチパターン。

## Best Practice（実例あり）

### 1. 宣言的マニフェスト1ファイル + 全コンポーネントがそこだけ読む

- Source: `hyperlane-xyz` 系（複数リポジトリで踏襲）— 例: https://github.com/hyperlane-xyz/hyperlane-registry (`chains/<network>/addresses.yaml`)
- 引用: `edakturk14/docs` の deploy ガイド — 「Under `$HOME/.hyperlane/chains` you will find a new folder named with your custom chain's name, and a file named `addresses.yaml` within that folder」
- パターン: **チェーンごとに1ディレクトリ、1 `addresses.yaml`**。デプロイスクリプト・監視・ドキュメント全部がこの1ファイルを読む。中央 `registry` リポジトリに全チェーン分を集約（`hyperlane-xyz/hyperlane-registry`）。

### 2. wallet メタデータを1つの JSON スキーマで宣言（id/name/type のみ、鍵は別）

- Source: `0xa3k5/web3icons`, `AGENTS.md` — https://github.com/0xa3k5/web3icons/blob/main/AGENTS.md
- 引用/スキーマ実物:
  ```json
  { "id": "metamask", "filePath": "wallet:metamask", "name": "MetaMask", "variants": ["branded", "mono"] }
  ```
  同ファイル内 `exchanges.json` も同型（`id/name/type/variants`）。→ **1エンティティ=1レコード、フィールドは最小限、`id` は kebab-case で一意**という設計原則が明文化されている。

### 3. venue（取引所/チェーン）を列挙型で宣言し、エンドポイント/残高照会がそこを参照

- Source: `SeshatLabs/heisenberg-sdk`, `typescript/src/generated/registry.ts` — https://github.com/SeshatLabs/heisenberg-sdk
- 引用: `export type Venue = 'hyperliquid' | 'kalshi' | 'polymarket';` — 各エンドポイント定義が `venue?: Venue` を持ち、venue 名の表記ゆれ（`Polymarket` vs `polymarket` vs `POLYMARKET`）を型で防いでいる。**auto-generated（`DO NOT EDIT` ヘッダ付き）** = 手書き散逸を構造的に防止。

### 4. 秘密鍵と public address の分離（address = 宣言可、key = 別管理・非公開）

- Source: MetaMask Developer docs, "Design server wallets for AI agents with ERC-8004" — https://docs.metamask.io/tutorials/design-server-wallets/
- 引用: 「The client holds an agent key used to authenticate who is asking to sign; this is separate from the onchain account key that controls funds.」「The encrypted key and metadata live in a database outside the enclave, encrypted by the agent key.」
- Source: Turnkey docs, "End-User Delegated Agent Signing" — https://docs.turnkey.com/features/policies/delegated-access/agentic-wallets
- 引用（Three critical properties）: 「Separation of control: The end user owns the wallet and sets the rules. The agent operates within those rules.」「Zero key exposure: The agent never touches the private key. It receives signatures, not keys.」「Cryptographic enforcement: Policies are evaluated in the secure enclave—no way to bypass them from application code.」
- → **address（読み取り専用の宣言情報）と private key（実行時にのみ enclave/keychain から取得する秘密）は別レイヤー**。マニフェストに入れていいのは address・chain・venue・ラベルのみ。key は `.env`（gitignore, chmod 600）や OS keychain に留め、マニフェストからは参照 (`keyRef`) するだけ。

### 5. gitignore + 0600 で秘密ファイルを隔離する実務パターン

- Source: `dat13899/stock-1`, `RUNNING.md` — https://github.com/dat13899/stock-1/blob/main/RUNNING.md
- 引用: 「File `wallets.json` được tạo ở root repo (mode `0600` — chỉ owner đọc/ghi）」「`wallets.json` — SECRET — gitignored, mode 0600」
- → 1ファイルに集約しつつ、そのファイル自体は secret 扱いで permission + gitignore で守る（address 専用の manifest とは別ファイルにするのが安全: 後述の推奨設計参照）。

## 推奨設計（simple、複雑フレームワーク導入なし）

**1つの `wallets.manifest.json`（address/chain/venue/label のみ、鍵は含めない・git 管理下でOK）を正本にし、全コンポーネント（loop・redeem.py・dashboard・env）がそこだけを読む。**

```json
{
  "version": 1,
  "wallets": [
    { "id": "base-automaton",  "chain": "base",     "venue": "evm",        "address": "0xB9dd...DD56", "label": "self-funded automaton", "keyRef": "env:ANICCA_BASE_KEY" },
    { "id": "sol-franklin",    "chain": "solana",   "venue": "solana",     "address": "8Fpqd...UPCV9",  "label": "Franklin trading",        "keyRef": "env:FRANKLIN_SOL_KEY" },
    { "id": "polygon-pusd",    "chain": "polygon",  "venue": "polymarket", "address": "0x904B...Eb74",  "label": "claude-p PM earner",       "keyRef": "keychain:polymarket-proxy" }
  ]
}
```

- 各コンポーネント（`redeem.py`, dashboard-wallet-legs.js, loop の残高確認）はこの1ファイルを read するだけ。導出・env fallback chain・手書き複製は禁止。
- 秘密鍵は `keyRef` が指す先（env var 1本 or OS keychain）にのみ存在。マニフェストに秘密鍵は絶対に書かない。
- 追加・変更は人間可読 diff（git commit）で追跡可能 = `docs/WALLETS.md` はこの JSON から自動生成する副産物にする（正本を2箇所に持たない）。

## 根拠となる実例（3件、重複なし）
1. **eliza plugin-polymarket** の4段 env var fallback chain — 散逸アンチパターンの実物（我々の現状と同型）。
2. **hyperlane-registry の `addresses.yaml`** — 1チェーン=1ファイル、全ツールがそこだけ参照する宣言的レジストリの実例。
3. **Turnkey / MetaMask ERC-8004 server wallet** — address（宣言可）と private key（enclave/keychain 限定、agent は触らない）の分離が明文化された一次情報。
