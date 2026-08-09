# Franklin on Cloudflare

最小のFranklinホスティング縦切りです。FranklinごとにCloudflare Agentsの名前付きDurable Objectを割り当て、状態を永続化します。

## 実装済み

- `GET /health` — 公開ヘルスチェック
- `GET /api/franklin/:franklinId/status` — Franklin単位の公開ステータス
- `POST /internal/franklin/:franklinId/state` — `Authorization: Bearer $INTERNAL_API_TOKEN` が必要な内部状態更新
- Durable Object再起動後の状態復元
- 名前の異なるFranklin間の状態分離

## 境界

このスライスはLife Manager本体を移行せず、既存のRailway/Express/Inngest/Telnyxサービスから独立しています。

今回実装していないもの:

- Cloudflare Computer/Workspaceへのウォレット秘密鍵の配置
- SOL/USDCの送金
- 残高の直接更新
- x402決済の受け取り
- WebMCPのブラウザ操作

残高を追加する将来の経路は、確認済みチェーンレシートだけを受け取る外部Signer/RPC境界に限定します。秘密鍵はこのWorkerやCloudflare ComputerのWorkspaceに置きません。

## ローカル検証

```bash
npm install
npm run typecheck
npm test
```

テストはWranglerのローカルWorkerを実際に起動し、health、未認証mutation拒否、Worker再起動後の永続化、Franklin A/Bの状態分離を確認します。

## デプロイ前提

```bash
npm run deploy
```

本番デプロイにはCloudflareの認証済みWrangler環境と、production用の`INTERNAL_API_TOKEN`設定が必要です。秘密値を`wrangler.jsonc`やGitへ入れないでください。
