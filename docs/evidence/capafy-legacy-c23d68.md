# Capafy legacy click inventory

目的: 旧クリックの帰属欠損を切り分け、会計・配信ownerが推測で照合しないための根拠を渡す。対象taskは`c23d68e42668425c07faedde`。正本の状態は統合SSOTのCAPAFY-LEGACY-INVENTORY節を参照する。

## 確認した事実

- 公式Netlify site `41c8e52e-b163-442a-84ff-fd866269bf6c` は`capafy-skills-daily`、account `daisuke134`と一致する。認可済みSDKでstrong consistencyのlist/getを行う。
- 全114記録のうち、3部分の旧キーは30商品・88件。88件の本文は全件文字列`1`。公式`/go-stats?detail=1`もtotal114 / legacy88で一致する。商品別件数・最初/最後の時刻・キー集合hashは隣接JSONに保存する。UUID、秘密、顧客識別子は保存しない。
- 公開landingのHTTP200本文から60件の`/go/<id>`リンクを取得する。全件ct/platform/post無し。リンクはJSONに保存し、redirect GET/HEADは発行しない。
- sourceの`clickKey`はplatform無しならctを問わず`clicks/<agent>/<time>-<uuid>`へ保存する。`targetUrl`は有効なctを別途保持する。ct無しと`hooklab_ig`付きが同じkeyになる反例を実コードのassertでPASSする。
- 以前のsource（`8df675eec4`の親）はURL query自体を読まず、同じ旧キーと本文`1`を保存する。現在の保存キーだけでは旧実装・新実装を識別できない。時刻をdeploy履歴と比較できても、元queryは復元できない。

## 判定と限界

`legacy`は**platformを保存しない形式**であり、**ct欠落の証明ではない**。30商品それぞれのbase routeまでは復元できるが、元query/ct/channel/post/本人owner/購入者は取得したBlobに存在しない。公開landingが現在bare linkであることも、旧88件すべてがlandingから来た証明にはならない。クリック件数は人間数・注文数・売上ではない。

過去88件の正確な帰属は、このデータだけでは復旧できない。Dots会計へ推測値を書かず、会計照合とMuse/Marketerの配信を維持する。既知の合成9件の除外は既存PR9097が所有し、本作業は変更しない。

## 具体的な次操作

1. 未来の欠損防止は`skills/earn/capafy-marketing/site/netlify/functions/go.mjs`の`store.set`と`go-stats.mjs`のreadbackを対象にする。既存key identityは維持し、検証済みct/platform/postだけの最小payloadを保存する案を別のsource taskとしてtest-firstで進める。元URL・referrer・IP・顧客情報を丸ごと保存しない。
2. 配信ownerが持つ既存publication receiptにexact route/queryが残っている場合だけ、対象商品/期間へ限定して照合する。Blobのbase routeからctやownerを捏造せず、receipt無しの88件はunknownのまま残す。新投稿・既存投稿の再送は不要。
3. 公開landingのCTAへのseller ct接続は、同商品の登録済みtokenとchannelを公式seller readbackしてから扱う。`hooklab_ig`を他商品へ流用せず、tokenを自動生成しない。landing producerは`capafy-ig-marketing-daily.sh`→`build_landing.py`であり、このauditでownerやruntimeを変更しない。

## 検証

`python3 skills/earn/capafy-marketing/tests/test_build_landing.py` 9/9 PASS、`node --test skills/earn/capafy-marketing/tests/go_functions.test.mjs` 5/5 PASS、同一legacy keyのct反例assert PASS、source-boundary PASS。すべて既存codeの確認であり新しいruntime実装や本番修復ではない。公式GET/list/getのみ、provider書込0、追加redirect request0、投稿0、会計変更0、購入/売上未確認。

Slack指定threadはparentとhome-codex更新の計2件で全件取得、本人の受領/着手/結果の新差分なし。Reason accepted/queuedは未着手、催促0。
