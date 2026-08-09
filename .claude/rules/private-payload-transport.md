# Private payload transport

- **症状:** stdin に渡した private provider payload が、処理結果とは別に tool output へ表示される。
- **誤った本能:** 対話中プロセスへ後から入力できるため `tty: true` を選ぶ。
- **正しい手:** credential・口座・医療・個人データは PTY へ送らない。echo のない pipe / inherited file descriptor / consumer 内メモリで処理し、開始前に synthetic marker で stdout 非露出を検証する。
- **一般法則:** `tty: true` と private payload の組合せは禁止。公開データだけが反例。`write_stdin` へ provider response を渡す前にこの規則を確認する。
- **実例:** Moneytree response を PTY stdin へ渡すと端末echoでraw JSONが表示された。純粋なpipeならconsumerが出したbooleanだけが表示される。
