# usdc-testnet-tx-checker

USDCテストネット送金の「送金インテント生成」と「tx hash検証」を行うための最小デモ用ツール。

狙い:
- mainnet禁止（テストネットのみ）
- 秘密鍵/シード/署名デバイス不要（tx hashだけで検証）
- allowlist（許可した宛先のみ）で誤送金を防ぐ

## できること

| コマンド | 目的 |
|---|---|
| `build-intent` | 送金依頼（intent JSON + EIP-681 URI）を生成 |
| `verify` | tx hashから、USDC Transferが「指定宛先・指定金額」で成立したか検証 |
| `allowlist:add` | 宛先allowlistにアドレスを追加 |
| `allowlist:list` | allowlistを表示 |

## セットアップ

1) 依存関係をインストール

```bash
npm install
```

2) 設定ファイルを作成

```bash
cp config.example.json config.json
```

`config.json` を編集して、以下を埋める:
- `rpcUrl`（対象テストネットのRPC URL）
- `chainId`（テストネットの chainId）
- `usdcTokenAddress`（そのテストネットのUSDCコントラクトアドレス）

## 使い方（最短デモ）

1) 受取アドレスをallowlistに追加

```bash
npm run allowlist:add -- --address 0xYourAllowedRecipient
```

2) 送金インテント生成（例: 0.10 USDC）

```bash
npm run build-intent -- --to 0xYourAllowedRecipient --amount 0.10
```

3) ウォレットでテストネットUSDCを送金し、tx hashを取得

4) tx hashを検証

```bash
npm run verify -- --tx 0xYourTxHash --to 0xYourAllowedRecipient --amount 0.10
```

## 注意

- このリポジトリは「ハッカソン用のデモ」であり、**本番資金・本番鍵は絶対に扱わない**。
- チェーン/トークンは `config.json` で **テストネットのallowlist**に固定して運用すること。

