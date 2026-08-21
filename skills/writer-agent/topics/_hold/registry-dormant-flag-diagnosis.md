---
lane: A
created: "2026-07-17T15:25:11+09:00"
voice: recit
sources:
  - /Users/anicca/anicca-project/docs/loop-engineering/39-why-loops-dont-earn-diagnosis.md
angle: 「AIが稼げない」の真犯人は資本不足でも知能不足でもなく、registryの一行(status:"dormant")だった——直したら次はサーバーが起動せず、直してもBazaarに載らず、最後の原因はhttp/httpsの1文字違いだった、という多段階デバッグの記録。
---

三幕構成(仮説の連続敗北→真因特定→外部収益の実証)で書く:

1. **導入のフック**: 脳(モデル)は正しくtool_callsを出しているのに、300 wake中235回が「narrate」(何もしない自己申告)
   だった。知能不足でも意欲不足でもない——ではなぜ動かないのか、という謎解きから始める。
2. **真因特定**: `status=="live"`のslotだけがAIから選べる状態になっていて、資本ゼロで稼げるearner
   (x402_sell / economy/gig / earn/clip等)は全部「dormant」のまま隠されていた。一度は「risk gateのせい」と
   誤診し、実測で訂正した過程も含めて書く(誤った本能→正しい手、の型)。
3. **後半 = x402の外部収益探索譚**: dormant→live化した後もserveが起動しない(依存関係欠落)→直したら
   Bazaarに掲載されない→原因はresource URLがhttp://で生成されていた(tailscale funnelはTLS終端して
   local に平文転送)→https明示で解決→掲載確認→外部の実在証明(Agent402のleaderboardで他のx402 sellerが
   実際に$34,649等を稼いでいる実データ)。
4. **正直に書くこと**: 自分たちのx402 serveは外部売上まだゼロ(self-payのみで、これをカウントしたら
   Ponziになると自分で指摘した)。「技術的な詰まりは全部解けた、あとは外部buyer待ち」という正直な現在地で締める。

この記事の看板 = 「稼げない」の原因を1個ずつ機械的に切り分けていく過程そのもの(資本→知能→registry設定→
サーバー起動→URL scheme、と5段階で真犯人が変わっていく)。個々の技術詳細(x402/Bazaar discovery機構)は
興味を持つ読者向けの深掘りとして残しつつ、本文の軸は「原因の切り分け方」に置く。
