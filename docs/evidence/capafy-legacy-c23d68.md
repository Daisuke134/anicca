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

## CI待ちの再開点

repo: `/Users/anicca/Projects/life-manager-main`。worktree: `/Users/anicca/Projects/life-manager-main/.worktrees/capafy-legacy-c23d68`。branch: `docs/capafy-legacy-c23d68`。結果commit: `0df40a8ea9bc605742fca4c04a1bcaf8bb3811fb`（後続はcheckpoint文書のみ）。PR: https://github.com/Daisuke134/life-manager/pull/9099 。owner/lease: `home-codex-c23d68` / `CAPAFY-LEGACY-INVENTORY`。

正本spec/残TODO: `/Users/anicca/Projects/life-manager-main/.worktrees/capafy-legacy-c23d68/docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md` のCAPAFY-LEGACY-INVENTORY節。現在cursor: 最新PR headの必要CI全件を公式readbackし、全PASS後にmainへ統合する。18:10Z初回readbackはSecurity Scan 14 checks QUEUEDであり、PASSへ読み替えない。`--admin`で未完CIを迂回しない。未来のpayload保存は未実装、過去88件の帰属と売上は未確認。

## 同ownerの継続照合

現行公式statsは通常105件・除外済み検証9件・legacy88件。上記114件は監査時のraw記録であり、現行通常集計と混同しない。PR9097の修正は反映済みで再deployしない。指定threadは公式完読し、dr eggbot本人の2時間sweep/wake_me未接続という差分を確認。Muse本人自然wakeとDots Slack接続は未確認、催促は追加しない。親所有PR9100/TEAM-HQは変更しない。

既存lockのowner home-codex-c23d68を維持してleaseを更新する。最新mainを取り込みBOARDは両方のowner記録を保持する。再検証はPython9/9・Node6/6 PASS。Nodeの初回起動失敗はworktreeの依存不在であり、既存package-lockのnpm ciで解消する。必要CI全PASS後にPR9099を統合する。未来の最小payload保存と旧receipt照合は残TODOであり、帰属欠損や売上が復旧済みとはしない。

## CI誤検出の継続修復

必要CI run41507477501はgitleaks dirだけFAIL、他13jobsはPASS。証拠JSONの集合hash項目名がgeneric-api-keyに誤検出されることを既定設定で再現する。項目名を`legacy_record_set_sha256`へ変更し、hash値とその他のJSON全内容をassertで保持する。検査rule/pathの除外追加は行わない。最新mainの既存history fingerprint baselineを保持する。指定remote threadは公式で全件を取得し、本人の新規受領/着手/結果差分なし、催促0。PR9097/9100は完了済みで再deployしない。現在cursorは更新headの必要CI全PASS→main、未来のpayload保存と過去88件のexact receipt照合は未完。
