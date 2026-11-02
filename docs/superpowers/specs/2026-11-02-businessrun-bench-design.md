# BusinessRun Bench: 実行可能な自律企業評価

実行順・状態の正本はunified SSOTのBusinessRun Bench節。本書は実装契約。

## 判断

既存のLM-EABはrecord scorerであり、agent実行ベンチマークと呼ばない。表示は「経済記録の契約検証」にする。新しい公開単位は **BusinessRun Bench — AIは事業を何日回せるか**。CompanyBench/EarnBenchは既存repo名と衝突するため使わない。

選択肢は、全simulationの再実装、既存suiteの利用、上流suiteと狭い独自課題の組合せ。先に既存suiteを利用する。Business BenchのProcess trackには精算・継続業務・transport障害が既にあるため、同じ問題を新しい世界として作り直さない。独自課題は自然失敗の未カバー部分を確認してから追加し、合成recordのテストを新しいagent性能と呼ばない。

## 最小の公開成果物

canonical `products/businessrun-bench/` がsource。公開repoはこのsubdirectoryの検証済みmain由来mirrorとする。

- `catalog.json`: Naïve全9評価と関連する長期経済/職場/ブラウザ評価の継続一覧。URL、上流、score、horizon、protocol差、再利用範囲、access条件、実行statusを持つ。
- `bench.py`: catalog一覧、公式上流の固定commit取得、隔離venvへのrequirements導入、公式baseline/pilot実行、公開可能なreceipt生成。上流graderを置き換えない。
- `native_adapter.sh`: Business Benchの既存adapter契約を使い、Codexの現在のaccount/runtime既定を利用。modelを強制しない。personal contextとhost可視性が残るlocal試行はdevelopment条件と表示し、公式隔離ランキングと混ぜない。
- `README.md` と実測記事: コマンド、条件、何を実行/未実行か、費用の算出根拠、故障と再現手順を説明。
- GitHub Actions: Ubuntuの隔離host上でbaseline campaignを実行し、receiptだけをartifact化する。公開repoをforkして同じcloud実行を使える。共有API keyを他userへ渡さない。これは一般利用可能なbenchmark実行経路であり、managed Life Manager SaaS全体の完成を意味しない。

## 実行・score契約

1. run IDの専用directoryは新規作成のみ。過去のtrajectory/resultを上書きしない。
2. 上流commit、config、seed、policy/model、実コマンド、終了理由、wall time、結果hashを結ぶ。外部checkoutの変更をmetadataへ残す。
3. provider費用unknownはnull。scriptのLLM費用0と、host総費用0を混同しない。API tokenの推計とinvoiceも別欄。
4. 90日CoffeeBench、14日Naïve slice、1年YC-Bench、Process acceptanceを共通点数へ足さない。失敗/破産/timeoutを除去しない。
5. 公開receiptはallowlistで組み立て、raw model output、home、auth、work_dir、account IDs、ERP tokenを含めない。
6. native model試行は上流のtask提示とgraderを使用。oracle/null/negative controlsはLLM評価に数えない。whole-model rolloutが未実行ならそのまま未実行と表示する。
7. 上流にpublic runnerがないClipping/Short Formはaccess-requiredとし、promptから似た環境を捏造して再現と呼ばない。

## CloudとNaïveの境界

Grok側sanbou-opsのSDK/agent/session記録をcanonical側の現在地に取り込むが、teamのsecretや稼働ownerを複製しない。現行Naïve orgのlive readbackと残高/権限が確認できた範囲だけ実行する。一般顧客へはtenantごとのidentity、権限、spend cap、effect lease、成果/削除/費用のreadbackが必要。既存チーム向けorgを無条件に共有SaaSとして公開しない。課金top-upとresale可否は既存spend-cap/公式規約/ownerと照合する。

## 検証

receiptの偽陽性（exit0だが未完）、失敗試行の欠落、unknown費用の0化、同じrun IDでの上書き、private値の公開、protocol差の混在を最小テストで防ぐ。実際に上流のoracle/null、CoffeeBench baseline、YC-Bench baseline、利用可能なmodel adapterを実行する。独立reviewは公開前に行う。
