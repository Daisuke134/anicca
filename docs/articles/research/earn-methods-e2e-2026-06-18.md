# 稼ぐ手段 end-to-end 実走記録（どれが本当に稼げるか）2026-06-18

検証財布: tester `0x94C445…B618` / anicca `0xa3CDd4Ec…` (Base)。各手段を実際に走らせ「実txで残高が増えたか」だけで判定。

| 手段 | 種類 | 人間/KYC | 実走結果 | 本当に稼げたか |
|---|---|---|---|---|
| **DeFi利回り (Aave v3 Base)** | 内部・利息 | 鍵のみ・KYC無 | **$2 supply→aUSDC $2保有→毎ブロック増加**。tx 0x1。可逆 | ✅ **稼げた**（APY~3.2%・確実） |
| **DeFi利回り (Morpho Steakhouse USDC)** | 内部・利息 | 鍵のみ・KYC無 | **$1 deposit→ERC-4626 shares保有→増加**。vault検証(asset=USDC)済。tx 0x1。可逆 | ✅ **稼げた**（APY~5%・確実・Aaveより高） |
| 0xwork (外部bounty) | 外部・受託 | 鍵のみ・gasless・KYC無 | LIVE・累計$8,013 paid。**だが今の公開タスクは2件＝両方「Jesse Pollakにフォロー/RTさせろ」＝実行不能** | ❌ 仕組みは本物だが**やれる仕事ゼロでブロック** |
| nookplot (推論work→NOOK) | 外部・work | gasless | CLI(homebrew 0.x / npm 0.7.38)とも **NOOKPLOT_API_KEY必須＝web-appでブラウザsignupが前提**。純CLIでない | ⚠️ **ブラウザonboarding要**（保留） |
| x402 売り (自前endpoint) | 外部・サービス | 鍵のみ | endpoint LIVE(anicca-x402, protocol OK)・**$0 received**（外部buyer無し＝需要待ち） | ❌ 配管は動くが**需要ゼロ** |
| swap (Uniswap V3) | 内部・資産回転 | 鍵のみ | earn skillが明示的に「net-zero回転＝GATE-0にならない」と拒否 | ✗ 稼ぎにカウントせず（正直） |

## 正直な結論
- **今この瞬間、鍵だけ・人間ゼロで"確実に残高が増える"のは DeFi利回り 一択**（内部・利息・極小だが本物）。
- **外部から客に稼ぐ（0xwork/x402/nookplot）は機構は本物だが、いずれも"供給/需要/onboarding"に律速**されて今は$0。
- ＝「稼ぐ配線があっても、外部収入は環境（仕事の在庫・買い手・登録）に依存する」。複数ソースを"動く"状態にするには、0xwork=実行可能タスクの出現待ち / nookplot=ブラウザ登録 / x402=買い手獲得、が必要。
- **確実に稼げる別ソースも追加実証済＝Morpho(~5%)**。同じ鍵だけ機構で複数の利回りソースが動く。さらにMoonwell等も同型で追加可。

（実走を続けて各セル更新。記事[6]③＋Anicca記事の中核テーブルに使う）
