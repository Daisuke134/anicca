# 🎯 LOOP SSOT — これ1つ見れば全部わかる（profitable-claude loop 修理の唯一の正本）

**scattered 防止**: loop 修理の設計・実態・全 task list はこのファイルだけ。他ファイルはここを指すだけ（詳細のみ持つ）。更新は必ずここ。

## 0. 用語（loop の走り方＝3層）
```
① launchd 目覚まし（機械上 ~/Library/LaunchAgents、一意 Label 必須。同名は片方しか起動しない=衝突）
② repo 内のレシピ（script）← どの repo にあるか = 「そのループがどこで動くか」
③ tmux の headless claude（実際に働く）
```

## 1. 2 repo の役割（違い）
| repo | 目的 | 稼ぎ先 | 誰が直す |
|---|---|---|---|
| **profitable-claude** | 人間(Dais)のために稼ぐ | 銀行/Stripe(fiat) | 私(claude-p) |
| **anicca** | agent 自身のために稼ぐ | 自分の wallet(crypto) | 別 CC |

## 2. profitable-claude の loop（TO-BE = 8個、重複なし）
```
1 gig        Coconala 出品/提案/見積/返信 → 銀行
2 capafy     skill 販売 → 銀行
3 article    Zenn 有料記事 → 銀行
4 life-manager 予定/連絡/intake → subscription MRR
5 affiliate  紹介投稿 → 紹介料
6 bounty     懸賞提出 → 賞金
7 connector  イベント/人脈 登録 → gcal+Telegram（人脈資産）
8 explorer   機会探索 → 上記へ供給
```
anicca 側(別 CC): founder / Franklin / pm / sol / clip / video / reddit / self-improve（crypto/SNS）。**verifier のみ共有**。

## 3. AS-IS（今の実態、launchctl 実測）→ TO-BE（理想）
```
AS-IS（混線・半分移行）:
  gig・capafy = anicca に居る（場所が間違い）  life-manager = PC と anicca で二重起動
  connector/affiliate/bounty/explorer = PC（正しい）
TO-BE（片付け後）:
  PC の 8 loop 全部が PC レシピ・hf-* Label・目覚まし1つずつ・重複ゼロ
```

## 4. 各 loop の TO-BE サイクル（全 loop 共通の型・no human・no CEO監督）
```
[BASE] 行動 → 実 side-effect(実URL/gcal/入金/ledger)を出す
[REALITY-VERIFIER] ★各loop内・report読まない★ browser(logged-out)/on-chain/gcal で実物を見て PASS/FAIL
   PASS → 記録（SUCCESS後も毎日再検証） / FAIL → [SELF-HEAL] self-fix→根因fix→再verify→再発防止をcodeに焼く
[SELF-IMPROVE] 日次で戦略1変異 → verifier が実成果で採否
```
CEO = 薄い機械 gate（予算 hard-stop + registry のみ、loop 殺す/作る判断なし）。

## 5. FULL TASK LIST（唯一・atomic・1行1アクション+done。上から実行）

### 実行方針（Dais 2026-07-11 確定・3ステップ・gigから1つずつ）
0. **verifier を全ツール使える様に直す** — [x] DONE: reality-verifier に「:9222ログイン済browser drive/on-chain/gcal 必須・report読むな」明記
1. **各ループを実際に稼ぐ/仕事する様に直す**（1つずつ・私がbrowserで実state確認・移動/改名しない・重複退治だけ例外）
2. **self-heal を各ループに内蔵**（healthcheck/self-fix が fresh adversary=reality-verifier[全ツール] を呼び実side-effectで判定→乖離→修復→再発防止をcodeに焼く。babysit不要に）
### Phase 1 — 片付け/引っ越し（M/S/C、Phase2 の前提）
```
[x] M1 gig を anicca→PC一本化 — DONE(2026-07-11): Label hf-gig-*修正+anicca版bootout+PC版起動、pane実測でAPI-key hang無し(env-u OK)。evidence=evidence/M1-gig-consolidation.md。残: L1(実出品/提案をreality-verifier確認)+M4b(session名分離)
[ ] M2 capafy を anicca→PC移管 — done: PC closed folder+Label hf-capafy-*
[ ] M3 life-manager 二重起動を解消 — done: PC一本化・anicca側目覚まし退役
[ ] M4 PC全ループのLabelをhf-*に改名 — done: launchctl衝突ゼロ
[ ] S1 registryからhl削除 — done: hlエントリ無し
[ ] S2 registryのpmを対象外注記 — done: crypto=別CCと明記
[ ] S4 vestigial cron削除 — done: 5分毎起動しない
[ ] S5 .disabled-agent-economy cruft削除 — done: 残骸無し
[ ] S7 CANONICAL_LOOPSにconnector追加 — done: 予算gateに載る
[ ] C1 logs/stateをrepo-local化 — done: ~/.openclaw参照0件
[ ] C2 vendor skill本体を実copy — done: 外部shell out無し
[ ] C3 gcal-policy.shをrepo内copy — done: 外部参照無し
[ ] C4 .envをrepo-local化 — done: .env.example有り
[ ] C5 affiliate~/.cloak参照confine — done
[ ] C6 bounty/affiliate/gig cliの~/anicca参照confine — done
[ ] C7 confine完了をgrep0件で検証 — done: state/log除き0件
```
### Phase 2 — 各loop修理（1つずつ・VCSDD lean・adversary=Sonnet・私のbrowserで実side-effect確認・verifyまで次に行かない。clip/video/reddit=anicca別CC）
```
[~] L1  gig 実績>0 — hang解消済(M1✅)だが pass14分未完走(applied273のまま)=実出品未確認。残: pass完走しない根因(hook error?)を突き止め→実出品/提案をbrowser確認  ← 今ここ
[ ] #5  connector 全horizon枠+7日streak — done: 各日Telegram delivered:true+gcal readback
[ ] #8  life-manager セルフマーケ — done: MoneyPrinterTurbo→Reddit/IG実投稿URL≥1+MRR導線
[ ] L2  capafy public掲載 — done: status=4 browser確認、"PUBLISHED"嘘出ない
[ ] #7  article 実publish→¥ — done: publish URL(logged-out一致)+metrics実測行
[ ] L5  affiliate reCAPTCHA突破 — done: 再ログイン→実投稿URL
[ ] L7  bounty 提出 — done: survivor→提出→賞金 or 正直none
[ ] L8  explorer 収益化 — done: proposal→実収益導線
[ ] #6  CEO仕上げ — done: cost自動記録+registry訂正+decision≥1(V3で縮退)
[ ] #9.5 SNS factory移行 — done: Dais go後にOpenClaw退役
```

## 6. Done 判定（全 task 共通、spec §10 準拠）
実 side-effect を **reality-verifier が独立確認**した時のみ done。report/test-green/adversary-PASS は done でない。「PROPOSED/draft/enqueue」は done でない。収益は on-chain/Stripe 実記録で照合。

## 7. 詳細は各ファイル（このSSOTがindex、詳細のみ委譲）
| 知りたい | ファイル |
|---|---|
| reality-verifier の設計/OSS調査 | `24-shared-ground-truth-verifier-design.md` |
| 全loop真実監査(browser/on-chain実測) | `../superpowers/evidence/LOOPS-TRUTH-AUDIT.md` |
| connector loop の元 spec/done条件 | `../superpowers/specs/2026-07-10-connector-loop-design.md` §10 |
| loop設計BP | `22-...bp-loop-verification-review.md` |
