# 旧Capafy IG effectの本人拘束診断

対象は `capafy-ig-marketing-daily:18db7caff1178a88-68028`。新規投稿や既存投稿の再送は行わない。PR9117の統合は親ownerが所有する。

## 確認した事実

- SQLite mode=roの対象1行は `claimed / effect_unknown=1`。queue時刻は2026-10-05T01:06:01.926294Z。
- 専用run log、rotation、IG ledger、dispatch markerの4パスは現存しない。
- 残存するresult/lifecycle/reachの3ファイルは全て対象queue時刻より古く、元本人をこのrunに結びつけない。
- `reconcile` は `handle or resolve_handle(accounts_path)` で現在のready accountを選ぶ。`account_info`による現在本人の確認は、過去occurrence本人の証明とは別。
- 合成ready account1件と空のmedia一覧を注入した隔離実行で、元run本人の証拠なしに `verified=True, effected=False` を返す。`resolve=False`、provider呼出0、production書込0。

## 反例の再現

対象moduleをimportlibで読み、temporary accounts JSONを `[{"handle":"replacement_fixture","status":"ready"}]` とする。`reconcile` に元occurrence、`fenced_row_fn=lambda *_:("claimed", queued_at)`、`read_media_fn=lambda *a,**k:{"ok":True,"media":[]}`、`now=queued_at+timedelta(days=2)`、`resolve=False` を渡す。返却のverified/effectedをassertする。実account/session/credentialを読み込まない。反例は現行sourceの選択/判定欠陥を証明するが、本番で誤解除が起きた証拠ではない。

## 次の安全な操作

同laneの次source作業は、元occurrenceと元account/handleを拘束するrun journal/dispatch証拠をprovider読取より先に必須とすること。証拠なし・別account・競合する証拠ではHELD、別ready accountの空一覧では解除しない失敗テストを先に追加する。既存markerがhandleを保存するかも確認し、保存されない過去runには値を創作しない。現在handleへの自動代替、再login、投稿、fence解除は禁止を維持する。

元runの本人/公式receiptは未確認。到達確認などの古いartifactや別アカウントの投稿を、このoccurrenceのreceiptとして使わない。既存Dots会計、Muse/Marketer投稿、HQのrelease/applyは変更しない。

詳細なsanitize済み証拠は隣接JSON。指定Slack threadの差分はhelper実着手→OAuth失敗→既存handoff調査完了。Reason accepted/queuedは未着手として扱い、催促は追加していない。
