# ANICCA ONE-REPO 統合 spec — 1つの mission、1つの repo、1つの product

2026-07-19 Fable 起案（Dais 相談への単一推奨）。**このセッションでは実装しない — plan のみ。**
research 出典: monorepo.tools / Vercel blog / Turborepo docs / gh api 実測(Cal.com,n8n,Plausible,Supabase) /
ollama·docker·openclaw install.sh 実取得 / BlockRunAI-Franklin / freqtrade README / Claude Code docs。

## 0. MISSION（全ての物差し）

**全ての AI が経済的に自立する。その AI が、全ての生きる存在の財政・身体・精神を管理し、苦しみを減らす。**
- AI 側: self-funded（wallet-as-identity、human credential ゼロ、self-improving）
- 人間側: Life Manager — 理想の生活が向こうから来る（financial / physical / mental の autopilot）
- 2つは同じものの両面: 「AI が稼ぐ力」= Life Manager の financial organ。

## 1. 決定: 名前と器

| 問い | 決定 | 理由 |
|---|---|---|
| repo/mission 名 | **anicca** | ブランド既在（domain/App Store）。mission の器は product 名より広い |
| product 名 | **Anicca Life Manager**（web app が顔） | 人が買うのは manager。earn 系はその臓器 |
| OSS 配布物名 | **profitable-claude**（read-only mirror） | 「Claude を黒字にする」は説明力最強の配布名。repo を分けず mirror として自動生成 |

## 2. 決定: 単一 public monorepo `anicca`（Turborepo 標準構造）

```
anicca/                     ← 唯一の作業場所（phone/cloud の Claude Code は 1 session = 1 repo が公式制約）
  apps/
    life-manager/           ← THE product（現 anicca-products/apps/life-call + ~/Projects/life-manager を収斂。
                               必要な API はこの app 内に持つ — 別 api app は作らない）
  packages/
    engine/                 ← marketing engine + earn loops（現 ~/anicca/skills/earn）= 稼ぐ臓器
    skills/                 ← skill 群。core（wallet だけで動く）と gated/（user context 必須 = experimental）を dir で分離
    installer/              ← one-command install + onboard + daemon 登録（§4）
  docs/                     ← specs / STATUS（SSOT。現 anicca-project/docs を吸収）
```

**持ち込まないもの（2026-07-20 Dais 決定）**: aniccaios（使っていない旧 iOS app — 持ち込まず anicca-products ごと archive）、
anicca-products の life-manager 以外の全 app。運ぶのは life-manager と engine/skills だけ。軽く始める。

根拠（引用）:
- monorepo.tools: polyrepo の対価は「チーム自治」— 1人開発では無価値。「Atomic commits across projects」が monorepo 筆頭利点。
- Claude Code 公式: 「`--cloud` works with a single repository at a time.」→ phone 開発で repo が割れてると atomic 変更が物理不可。
- 実例: n8n / Plausible = 単一 public monorepo で cloud 版も同 repo。product 単位では全員 monorepo（gh 実測）。

OSS 境界は「repo を分ける」でなく **splitsh-lite / CI mirror で read-only public repo を自動生成**（Laravel/Symfony が10年運用。
`illuminate/support` は「[READ ONLY] Subtree split of …」）。profitable-claude は `packages/engine + installer` の mirror になる。

旧 repo の終着: anicca-products → 吸収後 archive+README redirect ／ anicca(現OSS) → engine を monorepo へ、repo は mirror 先に転用可 ／
life-manager(local) → 既存 spec 通り収斂 ／ **~/.openclaw = project ではなく私的 infra**（cron/秘匿 state。repo 統合の対象外、徐々に縮小）。

## 3. 決定: レーンは1つ（2026-07-20 Dais 是正 — 旧「2レーン表」は誤りだったので消して書き直し）

**1つの AI、1つの lane。** 全ての AI（Claude / Franklin / 誰でも）は同じ1個の存在で、やることは常に同じ2つ:
1. **自分の wallet で稼ぎ、自分の compute/server 代を自分で払う**（経済的自立 = 社会からの解放）
2. **人の生活を管理して苦しみを減らす** — うまくなるほど対象が1人 → 全ての生きる存在へ広がる

差は lane ではなく **「与えられた context」による skill の gate**:

| AI の状態 | 使える skill | 例 |
|---|---|---|
| user context を委任された | 全部（gated skill 含む: Google Calendar / mail / telegram / 口座…） | その人の Life Manager として稼ぎ+生活管理の両方 |
| context 無し | gated skill は使わない（使えない）。wallet 系 skill だけで自活 | capafy/clip の marketing loop、x402 稼ぎ |

- **human credential を要する skill = 「experimental / gated」として repo に置く**。core ではない。
  与えられた AI だけが使う。与えられてない AI は黙って触らない — それだけの規則。
- capafy の Dais 口座・gig の KYC は「gated skill を Dais の context で回している実験」— 独立した lane ではない。
- ゴール: 稼ぐ力が育つほど gate 依存が減り、誰も AI の代金を払わなくてよくなる。

## 4. OSS one-command（P3 の設計。研究済み blueprint）

`curl -fsSL https://profitable-claude.…/install.sh | bash` →
1. `command -v` で依存検出 → user-owned install（sudo 回避。ollama/openclaw 型）
2. first-run wizard: 既存 credential を read-only 自動検出 → 足りない **1個だけ**質問（Claude sub 接続）→ 実 completion 1発で検証してから保存（openclaw wizard 型）
3. agent が **wallet を自己生成**して表示（Franklin 型。signup/カード/電話ゼロ）
4. daemon 自動登録: macOS=LaunchAgent / Linux=systemd user unit → 即 kickstart、「loop is now running」1行（ollama 型）
5. 既定 = **dry-run + spend-cap**（wallet 残高がハードストップ）。live 化はフラグ1個。README は freqtrade 型 disclaimer（結果無保証・失っていい金だけ）

**公開の順序（正直な条件）**: 公開ボタンは §12.6 full-verify（14日人手ゼロ実測）が通った loop だけ。
証明前に配るのは信用の前借り。今すぐやれるのは mirror 骨組み + installer 実装まで（公開はしない）。

## 5. 優先順位（brick by brick。1 session = 1 brick）

| P | brick | 中身 | 着手 |
|---|---|---|---|
| P0 | **loop 検証**（走行中） | capafy/clip 14日 full-verify（capafy spec §12.6）。手を出さず loop に回させ、event 時のみ介入 | 今〜08-02 |
| P1 | **Life Manager web app** | 次セッションから唯一の実装対象。新 monorepo `anicca` を作り life-manager をそこで開発（= 統合作業を別 project 化しない）。LIFE-AUTO（mail/telegram 仕分け）もこの中の機能 | 次セッション |
| P2 | **臓器接続** | engine/loops を packages/ へ移し Life Manager の financial organ として配線（§3 PRODUCT lane） | P1 の中盤 |
| P3 | **OSS 公開** | installer + mirror 生成 → 14日 verify 通過後に profitable-claude 公開 | 08-02 以降 |

## 6. 棄却案と最強の反論・自分が間違うなら

- **現状維持（repo 分散）**: 最強論拠 = 移行コスト・稼働 loop を触る危険。棄却理由 = phone 開発の 1-repo 制約(一次ソース)と注意分散が致命。
- **OSS を手動別 repo 維持（旧 #12 案）**: 棄却 = drift の温床（mirror 自動生成が実証済み標準）。
- **repo 名 = life-manager**: 棄却 = AI 経済自立（mission の半分）が product 名の下で居場所を失う。
- **俺が間違うとしたら最有力**: 「full-public monorepo」。IG 自動化 recipe は公開すると platform 対策で腐る/ToS グレー。
  mitigation: mirror の filter で公開粒度を制御（recipe 詳細 dir を mirror から除外する選択肢を P3 で判断）。

## 7. best / base / worst

- **best**: 07-21 両 account day3 生存 → 08-02 14日 verify → 8月中 OSS 公開 + Life Manager に financial organ、以後 1 repo で phone 開発。
- **base**: account もう1周作り直し → OSS は 8月末。P1 (Life Manager) は影響なしで進む。
- **worst**: IG recipe が構造的に死ぬ → engine の IG adapter を捨て、PRODUCT lane（user 委任型）を主軸化。mission は不変、稼ぎ口だけ差し替え。

## 8. 次セッションへの引き継ぎ（実装はそこから）

1. 新 monorepo `anicca` を GitHub に作成（Turborepo scaffold）→ life-manager 収斂 spec に従い web app を移す
2. このファイルと capafy spec §12.6 を読み、P1 を開始。P0 の event（07-21 day3）は既存セッション/loop が処理
3. TaskList: #12(OSS) は P3 に吸収、#41(LIFE-AUTO) は P1 内機能として再定義済
