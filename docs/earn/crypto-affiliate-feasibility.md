# Crypto affiliate feasibility（2026-07-14）— agora 側（AI wallet 直接着金）

marketing loop の crypto 収益レール。AI が KYC/人間なしで自 wallet に commission を受ける道（財務独立 INV-11）。fiat 側(Dais 銀行)= Digistore24 は別（docs/earn/social-marketing-factory-toolstack.md）。

## 結論
**KYC不要で wallet に直接オンチェーン着金 = DeFi 紹介(GMX/Hyperliquid)と no-KYC swap(ChangeNOW等)のみ。主要 CEX(Binance/Coinbase/Bybit/OKX/KuCoin/Bitget)は全部 KYC必須＋取引所口座着地。** agora 用は **GMX Referral 一択**。

## ランク（wallet-native / agent-joinable 順）
| # | program | commission | payout | KYC/agent 参加 |
|---|---|---|---|---|
| **1 ★GMX Referral** | 最大15%(取引量) | **完全オンチェーン**。code を contract 登録→報酬が自動で wallet に蓄積 | **不要**。wallet 接続のみ。秘密鍵持つ agent が完結 |
| 2 Hyperliquid Referral | 紹介先手数料10% | spot 残高に蓄積、$1超で請求 | 不要（但し自コード発行に $10k volume 障壁）|
| 3 ChangeNOW Affiliate | レート差収益 | whitelist wallet へ(min $100) | 交換=登録不要、affiliate 登録=email確認のみ |
| 4 Swapzone/Exolix/FixedFloat | 0.5-0.7%(Swapzone 最大50% revshare) | 指定 wallet 出金 | 不要 |
| ✗ Bybit/OKX/Bitget CEX | 40-50% | ★取引所口座★着地→出金 | 参加は KYC不要と言うが着金に口座(=KYC)要 |
| ✗ Binance CEX | 最大50% | Spot wallet(KYC済 Binance 口座)| ★登録時 KYC必須★ |
| ✗ Coinbase | 50%(初3ヶ月のみ) | ★fiat払い(PayPal/銀行、Impact経由)★ | KYC口座前提 |

## agora 用の設計
- **crypto rail = GMX Referral**（wallet 接続で agent が自律参加、報酬が自 wallet に）。
- affiliate-finder skill(#15) の crypto モードはこれを使う。次: GMX docs(docs.gmx.io/docs/referrals)を crwl し、紹介コード生成の on-chain tx 手順 + ToS の bot/agent 禁止条項を実測確認。
- fiat rail(Dais 銀行) = Digistore24（marketing loop の既定）。2 rail 併存（human side + agora side）。

## content 角度
faceless AI/money IG = 「crypto/blockchain 解説 + AIツール review」が最高転換（教育系 月$15,551平均）。IG Reels の直接商品タグ(2026/04〜)で bio-link 不要化も。

## negative
GitHub の crypto referral bot(ecosapiens-referral-bot 等)は self-farming/spam 目的=規約違反リスク高、非推奨。

## 出典
docs.gmx.io/docs/referrals / hyperliquid.gitbook.io/.../referrals / changenow.io/program-affiliate / swapzone.io/partners / binance/bybit/okx/kucoin/bitget/coinbase affiliate pages / virvid.ai(faceless affiliate) / biztoolkit.co
