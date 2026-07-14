# GMX Referral setup（agora crypto rail）— 2026-07-14 orchestrator verify

marketing loop の crypto 収益 rail。AI が自 wallet に crypto commission を受ける（INV-11 財務独立）。fiat 側 = Digistore24(Q-Money, Dais 銀行)。feasibility 正本 = docs/earn/crypto-affiliate-feasibility.md（GMX が KYC不要・wallet-native で確定）。

## verified 手順（GMX 公式 docs crwl 済 2026-07-14）
1. **referral code を作る**: A-Z/a-z/0-9/`_`、最大20字、case-sensitive。
2. **on-chain tx で登録**: Arbitrum が leader chain（`ReferralStorage` / `ReferralCodeValidator`。LayerZero で follower chain に伝播）。Arbitrum で登録すれば即有効。
3. 登録後、Referrals ページから referral link を copy → どの platform でも共有可。
4. 紹介先が link を開く→code が browser に保存→初回注文時に contract に書込→以降その trader は手数料割引 + ★自分に報酬（自 wallet へ）★。
- KYC/exchange account 不要。AI が Arbitrum wallet + gas(ETH) を持てば完結。
- 上限リスク: trader が $50M+ volume で GMX 管理 protocol code に graduate → affiliate 報酬 0%（通常無視可）。

## ★2026-07-14 setup 実測結果 = BLOCKED（gas 無し）★
- colony wallet の Arbitrum ETH 残高を実測（arb1.arbitrum.io/rpc, eth_getBalance）:
  - `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`(claude-p) = **0.0 ETH**
  - `0xB9dd3B67921B354c656523d6851537988F31DD56`(operational/BlockRun/HL) = **0.0 ETH**
- → **Arbitrum に gas が無く、referral code の on-chain 登録 tx を出せない。**
- Dais 個人 wallet から fund するのは stop point（不可逆・設計外）→ やらない。AI 自身の wallet で完結すべき。

## 次のステップ（fund → 登録）
1. **AI 自身の funds を Arbitrum へ**: operational wallet(0xB9dd)は BlockRun/Hyperliquid に funds を持つ。少額 ETH を Arbitrum に bridge（多段 bridge 禁止、native ETH を Arbitrum へ直接。gas は $1-2 相当で足りる）。★または clip/agora loop が earn してから self-fund（INV-11: AI が自分で稼いだ金で）★。
2. Arbitrum に ETH が入ったら: `ReferralStorage.registerCode(bytes32("aiclipsvault" 等))` を送信（blockrun_rpc / wallet で）。tx を Arbiscan で確認。
3. referral link 取得 → crypto clip アカ(将来)の bio に。
4. 本 file に code / link / tx hash / 使用 wallet を追記。

## 現状
- 機構 = verified（GMX docs）。feasibility = 確定（wallet-native, KYC不要）。
- setup = **未完（gas 待ち）**。盛らない。
- 実行者 = ★loop / agora の earn loop が自走で（INV-12）★。orchestrator は手順を確立したのみ。

## 出典
docs.gmx.io/docs/referrals（crwl verified）/ docs/earn/crypto-affiliate-feasibility.md / reference_anicca_wallets_canonical.md
