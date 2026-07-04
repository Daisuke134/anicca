# affiliate/bounty/gig を skills/earn/ から skills/human-funded/ へ物理移動(Task #16)

## 開発環境

| 項目 | 値 |
|---|---|
| 対象repo | `~/anicca`(git管理) |
| ブランチ | `feature/human-funded-split`(`~/anicca`メインツリーで直接作成、disk 1.8Gi残のためworktree不使用) |
| 既存規約 | `~/anicca/skills/human-funded/README.md`(Dais 2026-06-28制定、既存、変更しない) |
| 状態 | spec作成、実装は subagent に委譲 |

## 0. なぜこれをやるか

2026-07-05のヘルスチェックでDaisが指摘した通り、`earn/affiliate`(Amazon Associates口座)・
`earn/bounty`(GitHub `Daisuke134`アカウント経由でのPRコメント/フォーク)・`earn/gig`
(Coconala、Daisの銀行口座 MUFG着金)の3スキルは、**Daisの個人credential/アカウントが
無いと一歩も動けない**。self-funded AI(anicca-a3cdd4、Franklin)がこれらのスキルを
自分のwalletだけで実行しようとしても、affiliateはDaisのAmazonアフィリエイトIDが無いと
リンクを貼れず、bountyはDaisのGitHubアカウントとしてコメント/PRを出す設計であり、gigは
Daisの銀行口座に着金する。つまりこの3つは「no-human-loopなself-funded AIの汎用スキル」
ではなく、「Dais専属インスタンス(claude-p)だけが使える実験」である。

既に2026-06-28にDaisがこの区別を`skills/human-funded/README.md`として制定済みだが、
実際のコード(`affiliate/`, `bounty/`, `gig/`)は今も`skills/earn/`直下に残ったままで、
物理的な分離が完了していない。本specはその物理移動(`git mv`)+全参照更新+launchd plist
更新+疎通確認を行う。

## 1. 移動対象と移動しないものの境界

### 移動する(Dais専用credential必須、self-funded AIは使えない)
```
skills/earn/affiliate/  → skills/human-funded/affiliate/
skills/earn/bounty/     → skills/human-funded/bounty/
skills/earn/gig/        → skills/human-funded/gig/
```

### 移動しない(wallet-onlyで完結、self-funded AI含む全instanceが使える)
`skills/earn/clip`, `clip-producer`, `clip-promote`, `sol-trade`, `polymarket-trade`,
`hl-trade`(README相当のregistry記述)、`finchip-publish`, `board-poller`, `token-launch`,
`x402-sell`, `video` — いずれも自分のwallet署名・自分のCloakBrowserプロファイル・自分の
AgentMailアカウントのみで完結し、Daisの個人credentialを要求しない。fresh grep確認済み
(2026-07-05): これらのrun.sh/producer.sh/measure系スクリプトに`Daisuke134`という文字列や
Dais個人口座への言及は無い。

## 2. 実際に更新が必要な参照箇所(fresh grep確認、2026-07-05)

### 2.1 スキル内部の自己参照(git mvだけでは直らない、絶対パスハードコード)
| ファイル | 現在の参照 |
|---|---|
| `skills/earn/bounty/bounty-cli.sh` | STARTUP prompt文字列内に`~/anicca/skills/earn/bounty/...`複数箇所 |
| `skills/earn/bounty/bounty-healthcheck.sh:45` | `bash "$HOME/anicca/skills/earn/bounty/bounty-cli.sh" --restart` |
| `skills/earn/bounty/tests/test_run.sh` | テスト対象スクリプトパス |
| `skills/earn/affiliate/affiliate-cli.sh` | STARTUP prompt文字列内に`~/anicca/skills/earn/affiliate/...`複数箇所 |
| `skills/earn/affiliate/affiliate-healthcheck.sh:46` | `bash "$HOME/anicca/skills/earn/affiliate/affiliate-cli.sh" --restart` |
| `skills/earn/affiliate/run.sh:27` | `measure_commission.py`への自己パス |
| `skills/earn/gig/gig-cli.sh` | STARTUP prompt文字列内の自己パス |
| `skills/earn/gig/gig-healthcheck.sh:47` | `bash "$HOME/anicca/skills/earn/gig/gig-cli.sh" --restart` |
| `skills/earn/gig/run.sh`, `SLOT_CC.md` | 自己パス言及 |

### 2.2 リポジトリ横断の外部参照
| ファイル | 参照内容 |
|---|---|
| `skills/registry.json` | `earn/gig`(dir=`skills/earn/gig`)、`earn/bounty`(dir=`skills/earn/bounty`)、`earn/affiliate`(declared、dir未設定)のslotをそれぞれ`human-funded/gig`等に更新。**slotキー名自体も`earn/gig`→`human-funded/gig`のように変更する**(README.mdの規約「human-funded skill」という区分をSSOTのregistryにも反映するため) |
| `skills/_shared/__tests__/test_g2_static.py` | gig run.sh参照 |
| `skills/_shared/__tests__/test_gig_run_shim_darwin.py` | gig run.sh参照 |
| `skills/_shared/lib/step3_recipe.py` | gig参照 |

### 2.3 launchd plist(実行中、要注意)
`launchctl list`で現在ロード中(2026-07-05確認):
- `ai.anicca.affiliate-core-healthcheck` → ProgramArguments が
  `/Users/anicca/anicca/skills/earn/affiliate/affiliate-healthcheck.sh`
- `ai.anicca.bounty-core-healthcheck` → `.../skills/earn/bounty/bounty-healthcheck.sh`
- `ai.anicca.gig-core-healthcheck` → `.../skills/earn/gig/gig-healthcheck.sh`
- `ai.anicca.gig-auditor` → `.../skills/earn/gig/auditor.sh`

**`ai.anicca.{affiliate,bounty,gig}-proactive`の3つは変更不要**: `_shared/proactive-loop.sh`
→`proactive-loop-dispatch.py`は`~/loops/<slot>/`という別の状態ディレクトリのみを使い、
`skills/earn/...`という絶対パスを一切参照しない(fresh grep確認、38 hit全て`slot_dir`経由
の`~/loops/`参照)。

## 3. 実装手順(subagentに委譲する具体的コマンド列)

1. `cd ~/anicca && git fetch && git checkout main && git pull`
2. `git checkout -b feature/human-funded-split`
3. `git mv skills/earn/affiliate skills/human-funded/affiliate`
4. `git mv skills/earn/bounty skills/human-funded/bounty`
5. `git mv skills/earn/gig skills/human-funded/gig`
6. 上記2.1の全ファイル内の`anicca/skills/earn/affiliate`→`anicca/skills/earn/affiliate`ではなく
   `anicca/skills/human-funded/affiliate`に一括置換(bounty/gig も同様)。`sed -i ''`でも手動Editでも良いが、
   置換後に`grep -rn "skills/earn/affiliate\|skills/earn/bounty\|skills/earn/gig" skills/ | grep -v "\.vcsdd/"`
   が **0件** になることを確認する(`.vcsdd/features/`配下の過去レビュー記録は移動しない、
   履歴として残してよい)。
7. 上記2.2の`registry.json`を編集(slotキー名変更含む)、`_shared/__tests__`・`_shared/lib/step3_recipe.py`のパスも更新。
8. 上記2.3の4つのplistファイル(`~/Library/LaunchAgents/ai.anicca.{affiliate,bounty}-core-healthcheck.plist`、
   `ai.anicca.gig-core-healthcheck.plist`、`ai.anicca.gig-auditor.plist`)内の`<string>`パスを
   `skills/earn/`→`skills/human-funded/`に書き換える。
9. `bash -n`で移動後の全`.sh`ファイルの構文チェック(既存テストと同水準)。
10. 既存の単体テスト(`skills/human-funded/bounty/tests/`、`skills/human-funded/affiliate/tests/`、
    `skills/_shared/__tests__/test_g2_static.py`、`test_gig_run_shim_darwin.py`)を実行し全PASSを確認。
11. 4つのplistを`launchctl bootout gui/$(id -u)/<label>` → `launchctl bootstrap gui/$(id -u) <path>`で
    再ロードし、`launchctl list | grep -i "affiliate\|bounty\|gig"`で全て復帰していることを確認する
    (unload後loadし忘れてジョブが消えたままにならないよう、必ずload実行後に`launchctl list`で確認)。
12. `skills/human-funded/README.md`の「Initial intent」節に、実際に移動が完了した旨を追記
    (既存の「候補リスト」という記述を「済」に更新)。
13. commit(1コミットでよい、`git mv`検出を活かす)→ push(`-u origin feature/human-funded-split`)。
14. mainへfast-forward merge可能か確認(disk逼迫のためworktree不使用、他エージェントの
    並行編集([main]ブランチの`skills/earn/clip/producer.sh`の未commit変更)には一切触れない
    — `git status`で自分が触った以外のファイルが無いことを移動前後で確認する)。

## 4. 検証計画(GATE 2)

- 移動後、`grep -rn "skills/earn/affiliate\|skills/earn/bounty\|skills/earn/gig" ~/anicca/skills ~/anicca/docs ~/anicca/.github 2>/dev/null | grep -v "\.vcsdd/"` が0件
- 既存の単体テスト(affiliate 6件、bounty 8+5件)が移動後のパスで全PASS
- 4 launchd plistが`launchctl list`で再ロード後に生存していること(fresh evidence、実行して確認)
- `registry.json`が有効なJSONであること(`python3 -m json.tool`でパース確認)
- Dais個人credential不要スキル(clip/clip-promote/sol-trade/polymarket-trade等)側に一切変更が
  無いこと(`git diff main --stat`でこれらのdirがゼロ変更であることを確認)

## 5. スコープ外(YAGNI)

- `skills/human-funded/README.md`が既に定義済みの「Boot-time activation」ロジック
  (`install.sh`がenv var有無で有効化)自体の実装はTask #16のスコープ外(既存READMEが
  「install.sh scans...」と書いているが、install.sh側の実装は別タスク — 本specは
  純粋な物理移動+参照更新のみ)。
- `~/anicca-human-funded`worktree(既存、`feature/human-funded`ブランチ)は本タスクとは
  無関係な別作業(profitable-article-writer sprint群)で大きく分岐しているため、一切触れない。

## 6. GATE 1(SPEC)判定について

このタスクは新規ロジックの追加ではなく機械的なファイル移動+参照更新(YAGNI原則、
すでに設計は`human-funded/README.md`でDais承認済み)であるため、VCSDD adversaryレビューは
「移動漏れ・参照漏れの検出」に絞った軽量レビュー1ラウンドとする。
