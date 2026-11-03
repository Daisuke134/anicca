# Editorial design and publication scope

既存Manager記事rendererのcream/ink配色、max-w-3xl、本文18px、行間、見出し間隔を再利用する。独自CMSや新しいページ体系は作らない。原稿の短い段落と断言を維持し、8点を論点の位置に各1回配置する。画像内の英文に依存せず本文・altで説明する。

一次参照:
- https://waitbutwhy.com/ — 長文を問い、短い段落、説明図で分解する構造。
- https://pudding.cool/ — 視覚で考えを説明するessay構造。図は論点の近くに置く。
- https://www.paulgraham.com/articles.html — 本文と論理を中心に置くessay構成。
- https://press.stripe.com/ — 表紙、書名、著者と文章の明確な階層。
これらをcrwlで取得して構造を確認する。成果の比較可能な数値は取得できておらず、転換率や売上の成功率は主張しない。模倣対象は構造のみ。今回の計測は4媒体の公開到達、全文末尾、画像8点、表示幅、canonical/共有画像の整合。

原本8PNG: ZIP manifestのSHA-256/bytes一致、Pillow verifyで全点PASS。追加生成・差し替えは行わない。チェスはAI生成イメージと明記する。英語のmeritocracy節の原文保持と日本語全段落の意味対応を検証する。
