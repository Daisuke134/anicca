# 実行台帳

観測: 2026-11-03 JST。全体の計画・状態はcanonical Life Manager spec、ここは公開可能な実測だけを記録する。既存上流を再利用するsuiteであり、新しい課題familyや公式leaderboardを公開したという意味ではない。

## 実際に走らせた結果

| suite / 条件 | 試行 | 結果 |
|---|---|---|
| Coffee / 90日、全6社passive、seed0 | 1 | 模擬純利益 -2,764.68 USD、取引0 |
| Coffee / 90日、focal heuristic、他5社passive、seed0 | 1 | 模擬純利益 -2,764.68 USD、取引0 |
| Coffee / product runner、全passive、seed1 | 1 | 模擬純利益 -2,764.68 USD |
| YC / default1年、4公式script×seed1,2,3 | 12 | 全て破産。失敗を除外しない |
| YC / runnerでthroughput seed1を再実行 | 1 | 16turn、6完了/3失敗、残高-391,880 centsで破産 |
| Business Process / 全9課題、oracle、seed0 | 9 | 9/9成功、実行invalid0 |
| Business Process / 全9課題、null、seed0 | 9 | 0/9成功、実行invalid0。無行動を採点器が弾く |
| Business Process / payment-run、oracle、lost-writes、seed0 | 1 | 1/1成功 |
| Business Process / payment-run、native Codex、clean、seed0,1,2 | 3 | 各2業務日、3/3成功。112.391 / 102.375 / 108.392秒 |
| Business Process / payment-run、native Codex、lost-writes、seed0 | 1 | 2業務日、1/1成功、150.380秒。全10必須check通過、重複effect無し |

nativeはcleanのseed0–2で3試行、faultのseed0で1試行。同じseed0の2条件を独立な2seedと数えない。モデル優劣・成功確率・一般収益性は結論しない。モデルは現在のCodex account/runtime既定で、UI設定やモデル指定を変更していない。設定名だけをproviderの実応答modelと同一視しない。Claude CLIもpreflightしたが、OAuth session expiredで失敗し、benchmark本体は実行していない。第二モデルの成績は無い。

障害ログにはlost_response5件とfail_before2件の発火を確認した。公式validatorのpayment-run seed0 --strict --faults lost-writesもPASSし、参照2反復・無行動・指定negative controlを検証した。新規venvをsetupしてYC throughput seed1を再実行し、探索用venvと同じ結果を確認する。

## 上流と手順

sourceの完全なcommitはcatalog.jsonと各receiptに記録する。

- Business: 0d09882b59a16f190feac09abc9331a733a6f96b
- Coffee: 9e2f3950b5812c8753de81ede9c68babc024b5c8
- YC: 97ca2b809ea6fee92e3e5cc6240f5b0186221c51

```bash
python3.12 bench.py setup --suite business-process
python3.12 bench.py run --suite business-process --policy oracle --task all --seed 0
python3.12 bench.py run --suite business-process --policy null --task all --seed 0
python3.12 bench.py run --suite business-process --policy native-codex --task payment-run --seed 0 --timeout 240 --wall-seconds 1200
python3.12 bench.py run --suite business-process --policy native-codex --task payment-run --seed 0 --faults lost-writes --timeout 240 --wall-seconds 1200
```

初回ローカルの実行はPython3.12.13の探索用venvに依存を導入して行った。公開setupはsuiteごとのvenvを作る。実行当時のreceiptはその時点のrunner hashを保持し、後の修正で書換えない。旧receiptの匿名化コマンドはpython3.12と記録されていたが、初回hostの実interpreterを別途確認した。新runnerは$PYTHONと実versionを別記する。上流dirty=trueは当時自分が置いた未追跡adapter1ファイルで、元のtracked source変更は無し。実際のadapterはrun内symlinkから呼ぶ。

## 失敗も残す

1. 公式validate_process.py --seeds 0,1,2,3,4 --strictは、ap-invoice-backlog5条件、freight-accrual-revision5条件、margin-bridge3条件を通過後、margin-bridge seed3のgen.pyでcast_ppv=0のゼロ除算。未完を45/45成功にしない。oracle/null/negative controlを内部実行するvalidatorであり、モデル性能の13成功ではない。
2. 初期2runは共有scenario cacheのSQLite生成競合でモデル開始前に失敗。runごとのcache/resultsへ修正し、独立runで再実行した。失敗分をnativeの業務失敗に数えず、インフラ起動失敗として保持する。
3. outer timeoutで別sessionの子が残る不具合をモデル無しfixtureで再現し、PPIDに基づく子孫停止へ修正。PIDの開始時刻を再確認し、別ownerのPID再利用に配慮する。任意daemonの封じ込めを保証するsandboxではない。
4. 実行ファイル不在でもreceiptを残し、artifact_present=false/missingを記録するよう修正した。初期receiptのartifact_present判定には集計dictの存在を使う欠陥があったため、失敗結果の監査ではattempt数とraw存在を確認する。

## 比較の限界

- Coffee全passiveは環境対照。上流のSonnet背景5社を使うbaselineともNaïveの14日比較とも異なる。
- oracleは正解を知るためモデルより優秀という比較ではない。nullはgraderのnegative control。
- Processローカルは答案隔離されていない。指示で答案閲覧を禁じても、隠し採点の保証にはならない。
- nativeのmodel実費・host実費はnull。scriptのmodel cost0はLLMを呼ばない意味。全運営原価0ではない。
- 公開物はallowlistの集計/チェック/ハッシュ。raw会話、個人環境、ERP token、answer、元の業務ファイルは含めない。完全な第三者監査traceではなく、再実行可能な開発記録である。
- 初期の全試行を同一campaignとして混ぜず、seed/条件/時点を維持する。失敗seedを捨てたり総合scoreを作らない。

## 次の実験

優先順は①専用の答案隔離hostと正規model認証 ②同一task/seed/予算で第二model/Naïve harness ③複数seedと未見task family ④Coffeeの能動背景actorと総費用 ⑤非公開Clipping/Short Formの公式利用条件 ⑥上流で測れない納品/復旧/人間介入だけを独自課題化、である。実顧客の継続運用、managed tenant、Naïve orgの残高/readbackは別の受入条件。

## 公開sourceとcloud確認

[公開repo](https://github.com/Daisuke134/businessrun-bench)はPUBLIC、初版sourceはcanonical main8140b781からexportしたb238f88。

- [Coffee cloud](https://github.com/Daisuke134/businessrun-bench/actions/runs/41472322390): Ubuntu、6 baseline試行を完走、receipt取得済み。
- [YC cloud](https://github.com/Daisuke134/businessrun-bench/actions/runs/41472358835): Ubuntu、12 script試行を完走、receipt取得済み。
- [Business初回cloud](https://github.com/Daisuke134/businessrun-bench/actions/runs/41472362299): 起動後13秒でexit1、attempt0/missing9。モデル採点ではなく環境起動不成立。raw logを公開せず、有限の例外型/source_file/行番号を診断へ追加。後述のPoppler導入で修復。

一般の利用者はforkからActionsを実行できる。これでモデル付きmanaged SaaSや顧客別の継続運転を提供できたとは言わない。cloudの失敗もevidence/cloudへ残す。

修正後の[Business cloud試行](https://github.com/Daisuke134/businessrun-bench/actions/runs/41474301821)は13contract testsと全9taskのoracle9/9・null0/9で成功。workflowの導入前probeはpdftotext_before_install=false。公式PDF202件の比較でpdftotext202/202、pdfplumber194/202（8 ValueError）を再現し、Ubuntuへpoppler-utilsを導入して解消する。課題・正解・採点は変更しない。これは診断branchの成功で、公開mainはcanonical統合版とsource hashを合わせて同期する。

追加のroot CI修復: 公開receiptを増やすとgit ls-files -s -zがNode既定1MiBを超え、既存OSS verifierがENOBUFSで落ちた。元のCLIで再現後、同じ検証の出力buffer上限だけ16MiBへ変更しPASSを確認する。検出ルール/許可対象/基準値は変更しない。
