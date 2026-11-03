# HQ用Reason Networkクライアント

上流は [reason-machines/reason-network](https://github.com/reason-machines/reason-network)、
`v0.12.17` / `5872711927788b0d43a8a940ea45f993bc2926bc`。
`UPSTREAM.json`は取り込んだ各ファイルの元SHA256を記録する。
MITまたはApache-2.0の条件は同梱のLICENSEとNOTICEを参照する。
コンパイルに必要なsource・lockfile・埋め込み素材を保持し、インストーラや上流E2E実行環境は取り込まない。

HQ追加分は`src/main.rs`のCLIだけである。daemon、通信型、永続dedupeは上流実装を使う。
`src/debuglog.rs`の公開redaction fixtureの1行には、実credentialではないため限定的なgitleaks注記を付ける。
既存のReasonインストール、MCP、service、profileは置き換えない。

追加CLIの契約:

- `inbox --as hq-codex [--wait 0] [--peek] [--json]`は常にpeekし、JSONで`session_key`・`address`・`messages`・`text`を返す。既読化しない。
- `ack --as hq-codex --json ID...`は同じ箱をpeekし、全IDがその未読一覧に属する場合だけ既読化する。空ID一覧・未知ID・他箱との混在を拒否する。成功JSONは`session_key`・`address`・`acked`。
- 両コマンドの`--as`は必須。専用sessionは`cli:hq-codex`。返るaddressのsession名が一致しない場合は、別名へ接続せず失敗する。
- `send --from hq-codex --reply-to ID --idempotency-key KEY --json TO -`はstdinを既存の送信経路へ渡す。同一session/keyのdedupeはdaemonの既存storeが担う。成功JSONは既存の`ids`・`recipients`。
- Inbox・Ack・`--json`付きSendは既存daemonへの接続のみを使い、state移行やdaemon起動を行わない。失敗JSONは既存の`{"error":"..."}`形式、exit codeは非0。

ビルドと試験は明示した出力先を使う。production用binaryはmain統合後のimmutable sourceから作る。

```sh
bin/build-hq-reason-client --output /absolute/path/hq-reason-client
python3 vendor/reason-network-hq/tests/test_hq_cli.py --binary /absolute/path/hq-reason-client
```

試験はprivateな一時socketとfixtureだけを使う。実チームへのregister・受信・ack・送信の証明ではない。
