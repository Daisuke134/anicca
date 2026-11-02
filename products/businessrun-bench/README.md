# BusinessRun Bench

**AIは事業を何日回せるか。** 自律企業・経済・業務評価の一覧と、公式環境を再利用する実行用ツールです。モデルが何を判断し、何を完了し、いくらかかり、どこで止まったかを分けて記録します。

現在は既存suiteを実行する研究用ツールです。新しい汎用能力の実証、managed Life Manager SaaS、Naïveの非公開ベンチマークの複製ではありません。独自課題は未実装です。旧LM-EABは経済記録の契約検証という別部品で、agent性能のランキングには使いません。

[Naïveの全9評価を読む詳細記事](ARTICLE.ja.md)も公開しています。実測と失敗の台帳は [RESULTS.md](RESULTS.md)、公開済みの集計は [evidence/](evidence/) にあります。

## 始める

Python **3.12**、Git、LinuxまたはmacOSを使います。上流sourceとvenvはrepo外へ保存します。

```bash
python3.12 bench.py catalog
python3.12 bench.py setup --suite coffee
python3.12 bench.py run --suite coffee --policy passive --seed 0
python3.12 bench.py setup --suite yc
python3.12 bench.py run --suite yc --policy throughput --seed 1
python3.12 bench.py setup --suite business-process
python3.12 bench.py run --suite business-process --policy oracle --task payment-run --seed 0
python3.12 bench.py run --suite business-process --policy null --task payment-run --seed 0
```

`--state` は結果/venv、`--sources` は上流checkoutの保存先です。既存checkoutを使う場合もcatalogの固定commitとの一致を検査します。各runは新しいdirectoryとIDを持ち、既存の結果を上書きしません。Coffee/YCは上流の固定出力名による衝突を避けるため、runごとに新しいcwdで実行します。Business Processはrunごとにcache/resultsも分離し、上流の固有labelを使います。wall timeoutでは別sessionの子孫も停止します。自らdaemon化して親子関係を失う任意コードの隔離を保証するものではありません。

## 何が実行されるか

| suite / policy | 内容 | 結果の解釈 |
|---|---|---|
| coffee / passive | 90日、6社とも待機 | 環境のnegative control。LLM比較ではない |
| coffee / heuristic | focal roasterだけ固定戦略、他5社は待機 | 背景actorを変えた開発試行。公式のSonnet背景baselineとは異なる |
| yc / greedy, random, throughput, prestige | 上流bot、defaultの1年世界 | script baseline。DBを直接使う上流botで、LLMの行動ではない |
| business-process / oracle, null | 上流ERPと参照/無行動policy | grader/環境の検証。oracleは正解を知る |
| business-process / native-codex | 上流ERPを現在のCodex CLIで処理 | local development。モデルと個人設定が異なるため歴史的campaignの再現ではない |

Naïveの9評価を含む一覧は `catalog.json`。同社のCoffee比較は14日、元のCoffeeBenchは90日です。NaïveのClipping/Short Formは公開promptがあっても実行可能なsimulatorは今回取得していません。code accessが必要なものを「実行済み」と表示しません。

## 実モデルを使う

認証済みCodex CLIがある専用の開発hostだけで実行します。現在のaccount/runtime既定を使い、`-m`やUI設定を変更しません。

```bash
python3.12 bench.py run --suite business-process --policy native-codex \
  --task payment-run --seed 0 --timeout 300 --wall-seconds 1800
```

既存のpersonal CLI環境は答案や他ファイルを読める可能性があります。Process track自体がlocal modeで、sandbox指定やActionsの一時hostも答案隔離の保証ではありません。公式ランキング向けのmodel runは、別の隔離環境と専用accountで検証する必要があります。

 native adapterは上流のmodel名補完を使いません。Business Benchが欠落modelを過去の既定値へ補完すると、別のmodelの費用に誤帰属するためです。subscription実費と実効modelが確認できない部分はunknownのまま保持します。APIを使う場合も、そのrecorded token costとprovider invoiceを区別してください。

## receiptと公開

標準保存先は `~/.local/state/businessrun-bench/runs/<run_id>/`。`receipt.json` は上流commit、runner/adapter hash、設定、seed、終了code、結果、artifact hashを結びます。stdout/stderr/trajectoryはprivateのまま保持します。公開に使うのはallowlistから作るreceiptだけです。home、auth、ERP_TOKEN、raw model outputをuploadしません。

`host_cost_usd=null` は費用未計測です。scriptの `model_cost_usd=0` はLLM APIを呼ばないという意味で、全コスト0を意味しません。モデル費用unknownも0へ変換しません。失敗・破産・timeoutは残し、成功試行だけで平均しません。Business Processでgraderがpassでもagent実行が失敗した場合は有効な成功に数えません。

## cloudで実行

公開repoのActionsから `Benchmark baselines` を選ぶか、forkでworkflowを実行します。Ubuntuの一時runnerで上流commitを取得し、選んだbaselineを実行してreceiptをartifactへ保存します。共有accountやAPI keyは不要です。モデル付きのmanaged cloud提供・継続loop・Naïve上のtenant別実行は別の未完項目です。

## 検証と貢献

```bash
python3.12 -m unittest discover -p 'test_*.py'
bash -n native_adapter.sh
```

新しいbenchmarkは元実装・ライセンス・score・horizon・実行条件をcatalogへ追加します。新しいseedは未見のtask familyとは限りません。比較ではmodel、harness、background actors、sampling、予算、timeout、task/seed、graderを固定し、一度に変える条件を明記してください。

私たちのsourceはMITです。上流はそれぞれの条件に従います。第三者sourceはvendoringせず、固定commitから別に取得します。上流コード・データ・モデルのライセンスが同一とは限りません。

上流license: Business BenchはMIT、CoffeeBenchはApache-2.0。YC-BenchはREADMEがMITと記載する一方、このpinにはLICENSE本文を確認できません。sourceは再配布しません。実行前に上流の利用条件も確認してください。
