# なぜ openclaw-skills/ をローカルで編集してから VPS にコピーするか

## 結論

**正本は repo の `openclaw-skills/`。VPS は「実行用コピー」なので、ローカルで編集 → scp/rsync で反映、という流れにしている。**

## 理由（なぜ直接 VPS に書かないか）

| 理由 | 説明 |
|------|------|
| **バージョン管理** | Git で変更履歴・差分・ロールバックができる。VPS だけだと履歴が残らない。 |
| **レビュー・CI** | PR で diff を見てレビューできる。VPS 直接編集は「何が変わったか」の追跡が難しい。 |
| **正本の一元化** | 「どれが正？」が repo に集約される。VPS が複数（本番/検証）あっても、repo 1 本から配る。 |
| **障害復旧** | VPS が吹っ飛んでも、repo から同じ jobs.json / SKILL を再度 scp すれば復元できる。 |
| **エディタ・ツール** | ローカルは Cursor/VSCode で編集できる。VPS は SSH 先で vi などになりがち。 |

## 直接 VPS に書く場合のデメリット

- VPS 上で編集した内容を repo に戻すのを忘れると、**repo と VPS が乖離**する。
- いまの diff（repo は改行なし JSON、VPS は runtime で `state` 追加）のように、**どちらを正とするか**が曖昧になる。

## Mac Mini に移したらどうなるか

**Mac Mini 上で OpenClaw を動かす場合:**

- **同じ repo を Mac Mini に clone し、`~/.openclaw/` を Mac Mini のホームに置く**なら、**編集はその Mac Mini のローカル（= repo の作業コピー）で行い、`openclaw-skills/` を編集してから `~/.openclaw/skills/` や `~/.openclaw/cron/` にコピー**する流れにできる。
- 「直接書く」をやるなら、**編集対象を `~/.openclaw/skills/` と `~/.openclaw/cron/jobs.json` にし、変更後に必ず repo の `openclaw-skills/` に手動で戻す**運用にする必要がある。戻し忘れがなければ、どちらでもよい。
- **より楽になる点:** Mac Mini は同じマシンなので、**rsync やスクリプトで `openclaw-skills/` → `~/.openclaw/skills/` を一発で反映**するのが簡単。SSH 不要で `cp` や `rsync` で済む。

## おすすめ

- **正本は repo の `openclaw-skills/` に置く。**
- 反映は「ローカルで編集 → スクリプトで VPS（または Mac Mini の ~/.openclaw）にコピー」。
- Mac Mini 移行後は、そのスクリプトのコピー先を `localhost` の `~/.openclaw/` に変えれば、**より直接的に**（SSH なしで）反映できる。
