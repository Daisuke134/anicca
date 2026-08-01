# Connector O1B-19 grounded goal / serendipity 実装plan

1. Luma JSON-LDからdescription、organizer、attendee、住所を安全に正規化するtestを追加する。
2. semantic sourceをO1B-17 date inventoryへ伝播する。
3. verified O1B-18 rankingと全sourceを要求するO1B-19 decision testを先に書く。
4. Gemini strict JSON、5 factor exactness、excerpt grounding、全候補保持を実装する。
5. events packへgrounded ranking操作を接続する。
6. 実Gemini evalと実Luma read-only source readbackを実行する。
7. `test:outbound`、evidence、master specを更新し、commit/pushする。

