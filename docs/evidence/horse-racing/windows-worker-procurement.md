# HRA-2R1 Windows worker procurement evidence

**観測日:** 2026-08-09 (Asia/Tokyo)　**購入状態:** `NOT_EXECUTED_AWAITING_ACTION_TIME_CONFIRMATION`

## 選定（1台のみ）

**Dospara中古 HP Pro Mini 400 G9**（商品コード `357458`）
<https://www.dospara.co.jp/SBR1391/IC636996.html>

販売ページの実測は、Bランク、在庫1、5日以内出荷、表示価格 **¥73,000（税込）**。同社規約は「特に記載無い場合税込金額を表示」、中古PC本土送料は **¥2,200（税込）**（<https://www.dospara.co.jp/5info/cts_sc_law.html>）。従って任意の延長保証・追加品を付けない最大注文小計は **¥75,200（税込）**（送料込み、沖縄・離島を除く）。

| 項目 | 実測 |
|---|---|
| OS / CPU | Windows 11 Pro / Intel Core i3-14100T |
| CPU幅 | Intel公式は `Intel 64: Yes`、`Instruction Set: 64-bit`（<https://www.intel.com/content/www/us/en/products/sku/236775/intel-core-i3-processor-14100t-12m-cache-up-to-4-40-ghz/specifications.html>） |
| RAM / SSD | 16GB DDR5 / 512GB SSD |
| 接続 / 付属品 | 有線LAN・無線LANあり、AC・キーボード・マウス等 |
| 保証 | 3ヶ月（Bランク） |

Dosparaは「正規OS搭載」「正規ライセンスOSをセットアップし、厳しいチェックをクリアして販売」と明記する。JRA-VAN公式JV-Link要件はWindows 10/11日本語版、64ビットCPU、1GHz以上（<https://jra-van.jp/dlb/>）。商品ページに日本語版の明記はないため、購入前にそのSKUの日本語版・ライセンス認証を画面で確認するまでゲートは未通過とする。

JRA公式掲載アプリの実例は5年/10年DB、ディスク38GB・空き30GB以上（<https://jra-van.jp/dlb/sft/lib/jv2ai.html>）。DataLab全履歴の総容量は公式未記載であり、512GBは余裕を見た推論で保証値ではない。

## Mac運用と受入条件

Mac miniは制御・表示クライアント、上記を物理Windows workerとする。Microsoft公式は「リモートPCはWindows Pro必須」「接続元は別のオペレーティング システムでも可」としている（<https://support.microsoft.com/ja-jp/windows/experience/connectivity-networking/how-to-use-remote-desktop>）。Mac内蔵ストレージへWindows/DBを置かず、RDP後にJV-Linkを実データで検証する。

受入は次の全てを満たす時だけとする。

- SKU `357458` の在庫がまだ1以上で、最終合計が税込¥75,200以下（延長保証・追加品なし）。
- Windows 11 Pro日本語版、64-bit、正規認証、LAN接続を現物/初回起動で確認する。
- 保存済み配送先・決済情報は、ユーザーの明示確認後にのみ使用する。

現時点でカート、アカウント、決済、購入、JRA契約、provider probeは未実行。これは調達証拠であり、`REAL_PROVIDER_RECORD`ではない。HRA-2R1はWindows上で公式probeがexit 0かつ実JRA record 1件以上になるまで `BLOCKED` とする。在庫消失時は代替購入をせず、調査を再開する。

**E2E判定:** UIは存在せずMaestro対象外。次の検証はWindows worker上の公式probeのみ。
