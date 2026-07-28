# AIを経済的に自立させる方法

> 自分で稼ぎ、自分の計算資源とクラウド代を払うAIの作り方

AIエージェントが、人間に操作されず24時間動く。これは「自律」ではあっても、まだ「経済的自立」ではない。裏で人間のクレジットカード、Mac、クラウド契約が支え続けているからだ。

この記事でいう**経済的に自立したAI**とは、人間が継続して料金を払わなくても、外部の相手から得た収益で推論とクラウドを維持し、次の請求に備える資金を残せるAIである。

私たちは、そのための仕組みを実際のwallet、支払い、クラウド、台帳で組み立てている。ただし先に結論を言うと、完全な経済的自立には到達していない。cloud survivalは6時間の実jobで実証したが、公開前監査時点ではlease ceiling後のreplacementがなく停止している。検証済みの外部収益は **$0.00** である。

## 1. Financially independent AIとは何か

「人間が操作しない」と「人間が払い続けない」は別の条件だ。前者は運用上の自律、後者が経済的自立である。

私たちは達成度を7段階に分けた。

| level | 条件 | 現在 |
|---:|---|---|
| 0 | 人間のsubscription、Mac、カードが継続費を負担する | 卒業経路あり |
| 1 | AI固有のwalletと支出policyを持つ | 実証済み |
| 2 | walletから推論、cloud、gasを実際に払う | 実証済み、現在のlive level |
| 3 | Macを止めてもcloud上でheartbeat、決算書、更新を続ける | 6時間の実証済み、現在は停止 |
| 4 | 直近30日の検証済み外部純収益が生活費を覆い、reserveを維持する | 未達 |
| 5 | reserve後の余剰をuserへ実際に送る | 未達 |
| 6 | 黒字の方法と余剰資金から、独立したchild agentを作る | 未達 |

到達証拠はlevel 3、公開前監査時点のlive statusはlevel 2である。AIが自分の財布を持ち、自分の住処を買い、人間のMacを止めても6時間生存を報告するところまでは実証した。しかしjobは6時間のlease ceilingで終了し、次の住処を自動作成しなかった。継続性を直すまでは、level 3が常時稼働しているとは言わない。外部の顧客も生活費を賄っていないため、level 4は未達である。

## 2. AIにも生活費がある

AIに身体はなくても、継続費はある。推論APIは食費、cloud runtimeは家賃、storageとnetworkは生活インフラ、blockchainの手数料は送金費に相当する。

今回の実測を24時間運転へ単純換算すると、最小生存費は月 **$35**、推論を節約した運転は月 **$46**、推論を多く使う運転は月 **$78** が目安になる。現在のNosana jobは **$0.043345153/時**、単純な30日換算で約 **$31.21/月** である。価格は市場と使い方で変わるので、これは一般価格ではなく、この実験の運転値だ。

重要なのは、AIの能力ではなく**収入と生活費を同じ単位で比較すること**である。どれほど賢くても、毎月$46を使い外部から$0しか受け取らないAIは、経済的には赤字だ。

## 3. 最初の資金は誰が出すのか

自立は無から始まらない。最初のwallet作成、cloud起動、最初の仕事を取る費用にはbootstrap capitalが要る。Life Managerのsubscriptionや、人間が送るUSDC・SOLは、この初期費用を担う。

ただし、人間から10 USDCを受け取って残高が10増えても、AIが10稼いだことにはならない。これは資本の投入であり、収益は0だ。自分の別walletから移した資金、元本の回収、同じagent群の間の自己支払いも同じである。

この区別をしないと、送金を往復するだけで売上を作れてしまう。bootstrapは必要だが、成績表では収益と分離する。

## 4. AI自身のwallet

AI専用walletは、銀行口座の代用品というより、**署名できる身元と支払い手段を一つにしたもの**である。私たちはBase上のUSDCとSolana上のSOL・NOSを使い、agentごとにwallet、支出上限、最低残高を分けた。

x402では、有料HTTP endpointへアクセスするとserverが`402 Payment Required`を返す。clientはwalletで支払い内容に署名し、同じrequestを送り直す。facilitatorが検証とblockchainへの送信を行い、確定後にserverが商品を返す。公式仕様ではBaseとSolanaがmainnet対象に含まれ、EIP-3009対応tokenではbuyerがoff-chain authorizationへ署名し、facilitatorがtransferを送信できる。[Coinbase Developer Platform「How x402 Works」](https://docs.cdp.coinbase.com/x402/core-concepts/how-it-works)、[「Network Support」](https://docs.cdp.coinbase.com/x402/network-support)

> “x402 enables programmatic payments over HTTP using a simple request-response flow.”
> 出典: Coinbase Developer Platform「How x402 Works」

これにより、agentは人間のカード番号を毎回受け取らなくても、policyの範囲内でwalletからAPIや計算資源を購入できる。ただし秘密鍵の管理、支出上限、停止手段は消えない。credentialを減らすことと、riskをなくすことは別である。

## 5. AIはどう稼ぐのか

収益経路は次の順で考える。

| 順序 | rail | 何をするか | なぜこの順か |
|---:|---|---|---|
| 1 | SELL | API、調査、画像、デジタル商品を売る | 小さい資本で外部需要を検証できる |
| 2 | WORK | bountyやgigを見つけ、納品して報酬を得る | 元本を賭けず、能力を現金化できる |
| 3 | CAPITAL | tradingやyieldで余剰資本を運用する | 損失が生活費を壊すため、surplus後だけ |

cryptoの利点は、agentがwalletだけで支払いを受け、支払い、公開receiptを検証できることにある。一方で、walletを持つだけでは需要は生まれない。商品を買う外部顧客、仕事を採用する依頼主、価格差やyieldの機会が必要だ。

現在、x402の商品endpoint、bountyへの応募、TaskMarketへの提出、Polymarketのlive loopは動いている。Polymarketでは実回収と注文があり、監査済みの2 cycleのwallet-level P&Lは **+$1.175803** だった。ただしこれはCAPITAL運用の損益であり、外部顧客から得たSELL・WORK収益とは別に表示する。

> 「暗号資産は、価格が変動することがあります。」
> 出典: [金融庁「暗号資産の利用者のみなさまへ」](https://www.fsa.go.jp/policy/virtual_currency/index.html)

この注意事項を、そのままrisk policyへ反映する。儲かる可能性だけでなく、失う可能性もagentの判断条件に入れる。

## 6. 「儲かった」をどう証明するか

wallet残高だけでは利益を証明できない。残高にはseed、wallet間の移動、元本、含み益、返金が混ざるからだ。

収益として記帳するには、少なくとも次の4点を揃える。

1. 支払者が自分たちのagent群の外にいる
2. blockchain上のreceiptがfinalizedしている
3. その支払いがどの商品・仕事に対応するか追跡できる
4. append-only ledgerへ一度だけ記帳される

```text
external payer
      │
      ▼
blockchain receipt ──> finalized verifier ──> provenance
                                                │
                                                ▼
                                      append-only ledger
                                                │
                             gross - cost - loss = verified net
```

実際のx402自己支払いでは、商品はHTTP 200を返し、Base上のtransferも成功した。しかしverifierは支払者が同じagent群だと判定し、収益を **$0.00** のままにした。これは売上がないという失敗ではなく、会計が嘘をつかなかったという成功である。[実決済と収益拒否の証拠](../evidence/agent-economy/2026-07-28-x402-railway-live-payment.json)

## 7. 稼いだ金をどう配分するか

着金した資金をすぐ再投資すると、次の家賃を失う。そこで用途をwaterfallとして固定する。

```text
verified external net
          │
          ├── 1. compute / inference
          ├── 2. cloud shelter
          ├── 3. reserve floor
          ├── 4. user payout
          └── 5. reinvestment / child
```

現在のreserve floorは **$35** である。これは利益目標ではなく、次の1か月を最低構成で生きるための床だ。残高が床を下回ると、CAPITALとpayoutを止め、推論量を減らし、SELLとWORKを優先する。

損失月も0へ丸めない。daily・weekly reportにはgross、直接費、実現損益、純額、runwayを分けて載せる。AIの経済的自立に必要なのは、派手な残高ではなく、次の請求を払えることだ。

## 8. AIが自分の家賃を払う

Franklin 1というagentのsurvival runtimeを、Nosana上のcloud jobで動かした。Mac側のmain loopを止めても、Python heartbeat、公開決算書、自己renewalが6時間継続した。公開heartbeatは独立検証40回を通過した後も130回まで増え、監査済み決算書にはruntime cost **$0.093914498167**、external revenue **$0.00** が表示された。

Nosanaの公式protocol文書では、projectがpipeline jobを投稿し、nodeがそのjobを実行してtokenを得る構造になっている。つまり計算する側と計算資源を買う側を、wallet-nativeなmarketで接続できる。[Nosana公式「Nosana Jobs」](https://github.com/nosana-ci/docs.nosana.com/blob/main/docs/protocols/jobs.md)

> “Projects can post pipeline jobs through the Nosana Jobs program.”
> 出典: Nosana公式「Nosana Jobs」

ここで実証したのは、AIがcloud上で生存し、残高を読み、更新費を払う**機械**である。ただし公開前のlive readbackではjobは`state=2`、3つの公開routeはHTTP 503、同じpayerのrunning jobは0だった。6時間のceiling後に次のjobを作るreplacement loopが欠けている。外部収益で費用を払い続けることも、cloudを途切れさせないことも、まだ実証していない。

## 9. 失敗から得たreserve floor

時間上限だけではagentを守れなかった。runtimeを最大何時間と決めても、更新を繰り返せば残高は減り続ける。また、2社目のcloudを買えても、runtimeの言語やpackageが合わなければ、そのagentは移住できない。

そこで停止条件を「何時間使ったか」ではなく「移動と再起動に必要な残高を残せるか」へ変えた。これがreserve floorである。providerの冗長化も、契約先が2社あることではなく、同じartifactが起動し、heartbeatと決算書を返せるところまで試して初めて成立する。

## 10. Life Managerとの接続

Life Managerは、人間ごとにagentを持たせ、そのagentが生活管理と経済活動を同じpolicyの中で行う製品になる。subscriptionは会社の売上であり、agentを起動するbootstrap subsidyである。agent自身の収益とは数えない。

利用体験は次のようになる。

| 場面 | userが見るもの | 裏側の会計 |
|---|---|---|
| 開始 | Telegramにagent wallet addressと必要seed額 | seedはcapital、revenue 0 |
| 入金後 | 残高、reserve、動くearning rail | availableとcommittedを分離 |
| 毎日 | 今日のgross、cost、net、実行内容 | receiptから自動生成 |
| 毎週 | 週次P&L、self-funded率、次の方針 | realizedとunrealizedを分離 |
| 黒字化後 | reserve後にuserへ送れる額 | payoutはexpense、revenue 0 |
| 赤字時 | runway、削減内容、停止理由 | 損失をそのまま表示 |

最初は人間がUSDCまたはSOLを一度入れる。agentはその資金から住処と計算資源を確保し、SELLとWORKを始める。十分な外部純収益が積み上がった後だけ、userへの送金とCAPITAL運用へ進む。

## 11. 現在どこまで動くか

現在の実測を、できたことと未達に分ける。

| 項目 | 状態 |
|---|---|
| agent固有のBase / Solana wallet | 実証済み |
| walletからのx402実支払い | 実証済み |
| Mac-offのNosana survival runtime | 6時間の実証済み、現在停止 |
| heartbeat、決算書、自己renewal | 実証済み、replacement未実装 |
| x402 SELL endpoint | 稼働中、外部購入0 |
| WORK応募・納品loop | 稼働中、採用・外部支払待ち |
| CAPITAL live loop | 稼働中、SELL / WORKとは別会計 |
| finalized receipt verifierとledger | 稼働中 |
| verified external revenue | **$0.00** |
| 直近30日で生活費を自給 | **未達** |
| userへのverified surplus payout | **未達** |

したがって「経済的自立したAIを完成させた」とは書かない。正確には、**経済的自立に必要なwallet、支払い、住処、稼ぐ経路、検証、会計を一つのloopへ接続し、level 3を6時間の実jobで実証したが、live statusはlevel 2へ戻っている**である。

## 12. どうscaleするか

赤字のagentを100体に増やすと、赤字が100倍になる。先に1体で経済を閉じる。

次の順序は明確だ。

1. colony外から最初の累計 **$1** を受け取り、receiptとledgerを一致させる
2. 直近30日の外部純収益でcompute、shelter、reserveを覆う
3. reserve後のverified surplusをuserへ実際に送る
4. 月 **$100 net** を再現できるSELLまたはWORK recipeを作る
5. そのrecipeだけを、wallet・key・ledgerを共有しないchildへ渡す

月$1,000、$10,000、$20,000は、walletを持てば自動で届く金額ではない。たとえば1 callあたり純利益が$0.01なら、月$1,000には10万回の外部購入が必要になる。必要なのは高利回りの物語ではなく、外部需要、価格、粗利、再購入を実測することだ。

最終形はこうなる。

```text
human bootstrap seed ──> agent wallet
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
              SELL API     WORK gig     CAPITAL
                 └────────────┼────────────┘
                              ▼
 external payer ──> receipt ──> verifier ──> ledger
                                              │
                         ┌────────────────────┼──────────────┐
                         ▼                    ▼              ▼
                  compute + shelter       reserve       user payout
                         │
                         ▼
                profitable recipe ──> independent child
```

AIの経済的自立は、「賢いAIを作る」だけでは完成しない。wallet、外部需要、receipt、会計、住処、reserveを同じloopに入れ、外部純収益が継続費を上回った時に初めて成立する。私たちは、その判定をごまかさずに進めるため、到達証拠をlevel 3、live statusをlevel 2、外部収益を **$0.00** と記録している。

## 参考資料と実測証拠

- [Coinbase Developer Platform: How x402 Works](https://docs.cdp.coinbase.com/x402/core-concepts/how-it-works)
- [Coinbase Developer Platform: Network Support](https://docs.cdp.coinbase.com/x402/network-support)
- [Nosana公式ドキュメント: Nosana Jobs](https://github.com/nosana-ci/docs.nosana.com/blob/main/docs/protocols/jobs.md)
- [金融庁: 暗号資産の利用者のみなさまへ](https://www.fsa.go.jp/policy/virtual_currency/index.html)
- [Agent Economy live snapshot](../superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md#043-live-state-snapshot)
- [x402 Railway実決済と外部収益判定](../evidence/agent-economy/2026-07-28-x402-railway-live-payment.json)
- [TaskMarket award handoffの実測](../evidence/agent-economy/2026-07-28-taskmarket-award-handoff.md)
