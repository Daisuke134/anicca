# services/facilitator — self-host x402 gasless-settlement facilitator

SPEC.md §3 P2.1 の実装。Anicca colony の gig マーケットプレイスが gasless に決済する
心臓部。`x402-rs/x402-rs`（Apache-2.0）の固定commitを、archive SHA-256検証後に
cacheでbuildし、自己鍵 + 公開 RPC のみで動かす — Coinbase/CDP アカウントは
一切不要（human-zero）。由来と固定値は [THIRD_PARTY.md](./THIRD_PARTY.md) が正本。

## 何をするか

EIP-3009 `transferWithAuthorization` を買い手（payer）が off-chain 署名 → この
facilitator の `/verify` + `/settle` に POST → facilitator 自身の signer 鍵が
gas を肩代わりして on-chain 提出。買い手は gas を1円も持たなくても決済できる。

## 起動

```bash
cd services/facilitator
./start.sh  # 固定archiveを検証・cache buildして起動。cache hitはnetwork不要
```

`start.sh` は以下を行う:
1. `~/.anicca-signing/x402-facilitator/.env`（gitignore、chmod 600、repo 外）から
   `FACILITATOR_PRIVATE_KEY` を読む。無ければエラーで止まる。
2. `fetch-x402-rs.sh` が固定commit archiveのSHA-256と展開treeを検証し、
   `${XDG_CACHE_HOME:-$HOME/.cache}/life-manager/x402-rs/` で
   `cargo build --package x402-facilitator --features chain-eip155,chain-solana --release --locked`
   を実行する。検証済みcacheはnetworkなしで再利用する。
3. `config.json` を渡して起動（デフォルト `127.0.0.1:8405`）。`/health` が200を返すまで待つ。

開発時に既存のsource treeを明示する場合だけ `X402_RS_ROOT=/path/to/x402-rs`
を使える。未指定時に別repoや隣接folderを探索することはない。

## 鍵（絶対に repo にコミットしない）

```
~/.anicca-signing/x402-facilitator/.env
  FACILITATOR_PRIVATE_KEY=0x...   # facilitator 自身の signer（gas 肩代わり用）
  FACILITATOR_ADDRESS=0x...
  TEST_PAYER_PRIVATE_KEY=0x...    # E2E テスト用の買い手鍵（本番では colony の各 agent が自分の鍵で払う）
  TEST_PAYER_ADDRESS=0x...
```

新しい環境で立てる場合は新規に鍵を生成する（`python3 -c "from eth_account import Account; import secrets; k='0x'+secrets.token_hex(32); print(k, Account.from_key(k).address)"` 等）。
**同じ鍵を2つの facilitator instance で使い回さない。**

## 設定ファイル（`config.json`）— 実 Rust schema

★ README（x402-rs 本体）の config 例は実装とズレている（旧記法 `"scheme":"...","chains":[...]` は動かない）★。
真実は `crates/x402-types/src/scheme/mod.rs::SchemeConfig` + `crates/x402-types/src/config.rs::Config`:

```json
{
  "port": 8405,
  "host": "127.0.0.1",
  "chains": {
    "eip155:84532": {
      "eip1559": true,
      "signers": ["$FACILITATOR_PRIVATE_KEY"],
      "rpc": [{ "http": "https://sepolia.base.org" }]
    }
  },
  "schemes": [
    { "id": "v2-eip155-exact", "chains": "eip155:84532" }
  ]
}
```

- `chains` は CAIP-2 chain id をキーにした map（配列ではない）。
- `schemes[].id` は `v{version}-{namespace}-{scheme}`（例: `v2-eip155-exact`）、`schemes[].chains` は配列でなく CAIP-2 パターン文字列（`"eip155:84532"` や `"eip155:*"`）。
- 今は **base-sepolia（testnet）専用**。mainnet に切り替える際は `84532`→`8453`、RPC を `https://mainnet.base.org` 等に変更。

## HTTP エンドポイント（x402-rs 本体提供）

| Endpoint | Method | 用途 |
|---|---|---|
| `/` | GET | greeting |
| `/health` | GET | health check |
| `/supported` | GET | サポート scheme/network/signer 一覧 |
| `/verify` | POST | 支払い payload の検証（署名・残高） |
| `/settle` | POST | on-chain 決済実行（facilitator の鍵が gas を払う） |

## 実証済み E2E（testnet, real tx — evidence 全文は anicca-project repo 側）

`node scripts/settle-test.mjs` で実際に:
1. テスト payer が EIP-3009 authorization を署名（gas不要）
2. `/verify` → `isValid:true`
3. `/settle` → `success:true`, 実 tx hash: `0x383e9369202a0ff2551253350390ef17c59213ed9a2fe127bba0ff91ec0d1e70`
4. on-chain 確認（`eth_getTransactionReceipt`）: `status:0x1`、`from` = facilitator 自身の鍵（gas 肩代わり）、USDC `Transfer` イベントで payer→facilitator に 0.001 USDC 着金。

Base Sepolia ETH（gas 資金）・testnet USDC は Coinbase/CDP を一切使わず調達:
- **gas**: `sepolia-faucet.pk910.de`（PoW mining、hCaptcha 突破）で採掘 → Base 公式 `L1StandardBridge`（`0xfd0Bf71F60660E2f608ed56e1659C450eB113120`）に `depositETH` で L1→L2 ブリッジ。
- **USDC**: `faucet.circle.com`（reCAPTCHA Enterprise、CapSolver で突破）。

## テスト

```bash
set -a; source ~/.anicca-signing/x402-facilitator/.env; set +a
node test-facilitator-contract.mjs
```

`/supported` の内容チェック + `/verify` が壊れた payload で crash せず構造化エラーを返すこと + 実署名 payload の regression guard。facilitator が起動していないと `ECONNREFUSED` で fail する（RED/GREEN 両方確認済み）。

## スクリプト（`scripts/`）

| ファイル | 用途 |
|---|---|
| `bridge-deposit-eth.mjs` | Ethereum Sepolia → Base Sepolia へ ETH を公式 bridge でブリッジ（gas 調達） |
| `settle-test.mjs` | EIP-3009 署名 → `/verify` → `/settle` の実 E2E |
| `usdc-domain.mjs` | USDC コントラクトの EIP-712 domain（name/version）を on-chain 実測 |
| `check-usdc-balance.mjs` | 任意アドレスの Base Sepolia USDC 残高確認 |

## mainnet 移行時の注意

このリポジトリは **testnet 専用設定**（base-sepolia）。mainnet で使う場合:
1. 新しい signer 鍵を生成（testnet 鍵を使い回さない）
2. `config.json` の chain id / RPC を mainnet に変更
3. 実資金が動くため、`earn>spend fail-closed` 会計（SPEC.md §4）に必ず接続してから稼働させる。
