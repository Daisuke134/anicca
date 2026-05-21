#USDCHackathon ProjectSubmission Skill

Project: **usdc-testnet-tx-checker** (OpenClaw Skill / testnet-only)

## 何を作ったか
USDCテストネット送金のデモを、**秘密鍵を扱わず**に「送金依頼（intent生成）→ tx hash検証（オンチェーン確認）」まで通せる最小のOpenClaw Skillを作りました。

目的は “支払いがAPI/エージェント操作として成立する” ことを、誰でも同じ手順で再現できる形にすることです。

## 重要な安全設計
- **testnet-only**（mainnetは禁止）
- **秘密鍵/シード/署名デバイスを要求しない**（tx hashだけで検証）
- **送金先allowlist強制**（許可した宛先以外は検証不可）

## 使い方（5分デモ）
> 前提: `openclaw-skills/usdc-testnet-tx-checker/` で作業

1) 設定と依存関係
```bash
cp config.example.json config.json
# config.json に testnet の rpcUrl / chainId / usdcTokenAddress を設定
npm install
```

2) 受取アドレスをallowlistに追加
```bash
npm run allowlist:add -- --address 0xYourAllowedRecipient
```

3) 送金インテント生成（例: 0.10 USDC）
```bash
npm run build-intent -- --to 0xYourAllowedRecipient --amount 0.10
```
- 出力: intent JSON + EIP-681 URI

4) ウォレットでテストネットUSDC送金 → tx hash取得

5) tx hash検証
```bash
npm run verify -- --tx 0xYourTxHash --to 0xYourAllowedRecipient --amount 0.10
```

## リポジトリ
- [GitHub/Gitpadのリンクをここに]

## 検証ポイント（審査しやすさ）
- tx hashを渡すだけで「宛先・金額・USDCコントラクト一致」を機械的に検証できる
- 失敗理由をJSONで返す（amount mismatch / allowlist mismatch / confirmations不足など）
