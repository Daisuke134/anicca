# HRA-2R1 Windows first-real-record runbook

**State:** `PREPARED_NOT_EXECUTED`。HRA-2R1は `ACTIVE/BLOCKED`、`session0`、`record0`、`probe null` のまま。これは実行済み証拠ではない。

## Preconditions and evidence boundary

二時間目標は、受入済みworker、稼働ネットワーク、Windows 11 Pro日本語版、OS認証済み、JV-Link導入済み、JRA-VANサービスキー有効、の全条件が揃った時点から開始する。二時間は目標であり、SLAでも成功主張でもない。MacはRDPクライアント、workerはLAN内に置き、RDPを公開インターネットへ直接公開しない。

provider evidenceに使わないもの: synthetic fixture、スクリーンショット、HTML/DOM成功、ファイルmtime、自作row。raw DB、provider row、馬名、service key、subscription ID、account、receipt、raw logはowned Windows worker外へ出さない。

## Source decisions

1. **JRA公式の順序。** JRA-VAN Data Lab（<https://jra-van.jp/dlb/>）は「お申込み後、利用キーが発行されます」「購入完了画面から、基本ソフト（JV-Link）をインストールしてください」「『利用キーの自動設定』ボタンをおしてください」と案内する。JV-Link 5.0.0は「Windows 10、11 ※いずれのOSも日本語版のみの対応」「1GHz以上の64ビットのCPU」である。登録・key取得・JV-Link導入・key設定を順序どおりに行う。
2. **公式JV-Link配布。** JRA-VANダウンロード（<https://jra-van.jp/dlb/dlrt_web.html>）は「STEP1 JV-Linkのインストール」とし、公式リンク <https://dl.cdn.jra-van.ne.jp/datalab/JV-Link/web/JV-Link.exe> を掲載する。binaryをGitやMacへmirrorしない。
3. **pinned upstream。** `miyamamoto/jrvltsql` README（<https://github.com/miyamamoto/jrvltsql/tree/61c202c27c12269668991712334adb0a4662dd83>）は「Windows 10 / 11」「Python 3.10以上。JV-Link COMを直接使う環境では32-bit Pythonを推奨します」「JRA-VAN DataLab + サービスキー」を要件とする。範囲取得は `quickstart_timeseries.bat --db sqlite --from <FROM> --to <TO>` で、READMEの例は「指定範囲の通常データ + TS_O1 / TS_O2を取得」する。
4. **installer拒否。** pinned `install.ps1`（<https://github.com/miyamamoto/jrvltsql/blob/61c202c27c12269668991712334adb0a4662dd83/install.ps1>）には「git pull --ff-only origin master」と、未存在時の「git clone $REPO_URL $INSTALL_DIR」がある。masterへ追随し得る一行installerは使わず、手動cloneとSHA固定checkoutを使う。

## Fail-closed execution

### 1. Physical acceptance

Dospara SKU `357458` の価格・receiptを別途確認し、Windows 11 Pro日本語版、activation、64-bit OS、network、MacからのRDP到達性を確認する。未確認なら `BLOCKED`、購入・決済・公開RDPは行わない。

### 2. Official provider setup

ログイン済み公式ページでData Lab登録/契約状態を確認し、利用キーを取得する。JV-Linkは上記公式URLから導入し、keyはworkerへローカル設定する。runbookへcredential値を転記しない。登録・契約・導入が未完なら `BLOCKED`。

### 3. Pinned upstream setup

Windows workerで次を実行し、SHA・clean status・diff checkを確認する。

```powershell
git clone https://github.com/miyamamoto/jrvltsql.git C:\jrvltsql
cd C:\jrvltsql
git checkout 61c202c27c12269668991712334adb0a4662dd83
git rev-parse HEAD
git status --short
git diff --check
py -3.12-32 -m venv .venv32
.\.venv32\Scripts\python.exe -m pip install -e .
```

`irm .../master/install.ps1 | iex`、master checkout、未固定cloneは実行しない。

### 4. Local mechanics check

providerを呼ばないmechanics evidenceとして、pinned READMEどおり `pytest tests/ -q --ignore=tests/integration/ --ignore=tests/e2e/` を実行する。失敗時は `BLOCKED`。このtest結果でsession/recordを増やさない。

### 5. Bounded real probe

全precondition成立時刻を記録し、`$env:JLTSQL_SKIP_SCHEDULER_PROMPT="1"` を設定する。Windows-localで `TO_DATE=today`、`FROM_DATE=today-7 days` をISO日付へ計算し、次だけを実行する。

```powershell
$env:JLTSQL_SKIP_SCHEDULER_PROMPT="1"
$TO_DATE = (Get-Date).ToString('yyyyMMdd')
$FROM_DATE = (Get-Date).AddDays(-7).ToString('yyyyMMdd')
quickstart_timeseries.bat --db sqlite --from $FROM_DATE --to $TO_DATE
$exitCode = $LASTEXITCODE
```

開始/終了時刻とprocess exit codeをworker-localへ保存する。`quickstart.bat --yes --include-timeseries` は1986年から今日まで取得するため二時間gateでは実行しない。

### 6. Non-exporting checks

exit 0の時だけ、SQLite内で `NL_RA` の件数、`PRAGMA table_info(NL_RA)` のfield名/type、SQLiteファイルのlocal SHA-256だけを取得する。row値を表示・exportしない。`NL_RA=0`、nonzero exit、schema欠落、provider timestamp欠落、entitlement失敗のどれか一つで、欠落フィールドを明記して `BLOCKED`。file mtimeをprovider timestampへ代用しない。

```powershell
sqlite3 data\keiba.db "SELECT COUNT(*) FROM NL_RA;"
sqlite3 data\keiba.db "PRAGMA table_info(NL_RA);"
Get-FileHash data\keiba.db -Algorithm SHA256
```

### 7. Redacted handoff

`jra-probe.md`へ移せるのは、boolean、timestamps、versions、pinned commit SHA、exit code、row count、schema names/types、content hash、`raw_values_exported=false`だけ。Solはこれを突合してからHRA-2R1をPASSにする。

### 8. Timebox

全precondition成立から120分でretryを停止し、正確なstage/errorを `BLOCKED` と記録する。日付範囲拡大、master切替、replacement record生成で成功を作らない。
