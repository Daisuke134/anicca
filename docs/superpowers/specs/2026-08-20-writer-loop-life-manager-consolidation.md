# Writer Loop を Life Manager に統合する仕様

状態: 実装順序を固定。公開成功を宣言する仕様ではない。

## 目的

WriterのコードをLife Managerリポジトリへ集約し、1つのcreator、1つのsame-run
resume、1つの収益台帳、1つのTelegram報告面で、需要カードから記事公開・実読戻し・
入金receiptまでを継続する。コードはリポジトリに置くが、credentialとmutable stateは
リポジトリ外のowner専用storeに置く。

## 現在の実測

- `daily-2026-08-20` はJA/EN原稿を生成し、active-fourの公開は0/4。
- Noteは安定した下書きキー `ne6da5b602b4a`、Substack日英は下書きID
  `211988979` / `211988987` を再照合できた。これは下書き・intentの証拠であり、公開URLではない。
- X日本語は編集URL `https://x.com/compose/articles/edit/2090392988765605888` を
  intentとして保持し、変更・公開していない。
- 最後の再開tickは4件のintentを揃えて終了したが、deterministicな公開tickはまだ実行されていない。
- `launchctl bootstrap`/`kickstart` は `141: Reentrancy avoided`。plistがあることは稼働証拠ではない。
- 実行releaseは `/Users/anicca/profitable-claude-releases/writer/e9ab21ea/writer-agent`、
  stateは `/Users/anicca/profitable-claude/skills/writer-agent/state`。Life Manager checkoutは
  `/Users/anicca/Projects/life-manager-main` だが、Writer runtime treeは未移行。
- Telegramには状態報告を送信済み（最新の初期化報告 message ID `26065`）。旧経路には技術列挙の報告が残るため、今後はdeterministic rendererだけが自然文を送る。実受取receiptは未確認。

## 目標構成

```mermaid
flowchart LR
  D[Demand cards] --> C[Life Manager Writer creator]
  C --> A[Immutable JA/EN artifacts]
  A --> P[Publisher adapters]
  P --> R[Publisher-native readback]
  R --> M[Money receipt join]
  M --> T[Neutral Telegram renderer]
  T --> S[Durable state and same-run resume]
  S --> C
```

```text
life-manager-main/
  skills/writer-agent/             # 唯一のWriter codeとadapter
    runtime/                       # model boundary、prompt、judge broker
    demand/                        # claim loop、demand cards
    publishers/                    # note、Substack JA/EN、X、free distribution
    receipts/                      # public readback、payment/publisher receipt
    reports/                       # natural-language Telegram renderer
    launchd/                       # creator/resume plist templatesとmanifest
  config/writer/                   # platform/account role registry（secret参照のみ）
  docs/superpowers/specs/          # この統合仕様と実測証拠

~/.local/state/life-manager/writer/ # run state、ledger、outbox、receipt、log
~/.config/life-manager/accounts/    # owner-approved credential references
```

唯一のcreatorは新しいrunを作り、resume ownerは同じrunの未完destinationだけを再開する。両者は
リポジトリの場所に依存しない共有fence（`~/.local/state/life-manager/writer/owner-fence`）を
先に取得し、ownerの絶対path、PID、起動時刻、state schema、run IDを記録する。旧rootと新rootの
同時稼働を許さず、cutoverでは全workerをdrainしてowner不在を確認してからstate/ledger/outboxを
原子的に移す。
platformは `revenue`（Note、Substack）と `discovery`（Dev.to、Zenn、X等）を分離する。
同じ全文を別言語・別publicationへ無差別複製しない。`substack/ja`と`substack/en`は
publication identity、読者、payout、ledgerを分ける。

## 完了条件

1. Life Managerのmanifestがsource SHA、実行release、state schema、全worker pathを固定し、
   missing pathが0になる。
2. 1回の実scheduler wakeでrun/artifact hash、creator PID、終了receiptを取得する。
3. 同一runのNote JA、Substack JA、Substack EN、X Article JAがpublisher-native URLを返し、
   URL本文・owner・artifact hash・media hashをreadbackする。
4. paymentまたはpublisherの実受取receiptをartifactへjoinする。未確認額は0に変換しない。
5. Telegram本文は自然文で、実際に起きたこと、外部理由、確認済みの公開URLまたは未確認、
   次の自動行動を説明する。`Codex:::`、`Claude:::`、生enum、stack traceは主文に出さない。
6. 14日間、重複外部作用0、同一run resume、日次/週次報告、revenue ledger整合を観測する。
7. 上記のparity receiptとrollback archiveが揃うまで、Writer専用releaseを含む旧実行rootを
   削除しない。`~/.openclaw`は認証・ブラウザ・gatewayの不可侵runtimeであり、永久に削除対象外。
   `/Users/anicca/profitable-claude`全体もWriter以外の稼働loopを含むため削除対象外とし、最後に
   可能なのは参照census・復元試験・shared fence確認を通ったWriter専用releaseのアーカイブだけである。

## Atomic TODO（この順番以外を先に進めない）

| # | 作業 | 完了証拠 | 状態 |
|---:|---|---|---|
| 1 | launchd実行コンテキストを復旧し、creator/resumeを一度だけ起動 | `launchctl print`と終了receipt | 未完了 |
| 2 | DNSまたは承認済みnetwork transportを復旧 | Note/SubstackのHTTP到達証拠 | 未完了 |
| 3 | Writer runtimeを`skills/writer-agent`へ移しmanifestを生成 | SHA付きpath census | 未着手 |
| 4 | demand→artifact→publisher adapterを同じstate schemaへ接続 | run/artifact parity | 未着手 |
| 5 | Note/Substack/Xの実公開とreadbackを同一runで完了 | 4件のlive receipt | 未着手 |
| 6 | payment/publisher receipt collectorとmoney ledgerを接続 | artifact-level receipt | 未着手 |
| 7 | neutral Telegram rendererを日次・失敗・完了へ接続 | message ID + semantic hash | 一部実装 |
| 8 | adversarial verifierで重複公開・誤金額・偽URL・secret漏洩を反証 | review receipt | 未着手 |
| 9 | Life Manager ownerをloadし、19個のWriter関連LaunchAgent（creator、resume、retry、money、report、health、learning、opportunityを含む）のpath/state/lockをmanifest化。shared fenceで旧ownerをdrain後にdisable | owner manifest + old/new parity + bounded wake | 未着手 |
| 10 | rollback archiveと復元試験を検証し、Writer専用releaseだけをアーカイブ。`.openclaw`と`profitable-claude`全体は削除しない | archive hash + restore receipt + deletion-scope receipt | 未着手 |

削除は最後の一件であり、現在は実行しない。
