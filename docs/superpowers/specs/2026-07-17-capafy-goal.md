# /goal — Capafy two-loop 独立自走（2026-07-17 制定）

/goal Capafy two-loop system（Loop A=build/publish、Loop B=marketing）が親の介入ゼロで自走し MRR $10,000 へ向かう状態を作る。北極星 MRR は Capafy server API（/agent/sales/trend + payout-info）のみで評価し、local 自己申告は使わない。done は以下全部が実測 PASS:
(a) Loop A 健全化 — `ai.anicca.capafy-loop-daily` が 7日連続で BLOCKED rc=1 ゼロ（max-turns 枯渇解消、1 pass=1 agent）。rejected agent は loop 自身が re-key（正 provider 名）→ Test Run green → resubmit し、reject 理由を state/lessons に追記、次 publish の lint がその lesson を参照する（reject→resubmit→learn が閉じる）。証拠 = daily_loop.log + Capafy remote-status + lessons ファイルの diff。
(b) 会計の真実 — server sales が daily で local earn-ledger に reconcile され、報告値と server 値が一致（現行 $9.99/1件 の見落としバグ解消）。
(c) Loop B 誕生 — 新 IG account が ready（warmup 完了）になり、**launchd `ai.anicca.capafy-marketing-daily` 経由で loop 自身が**初 Reel を投稿する（人間・親セッションの手動投稿は done と認めない）。bio に Capafy link、投稿の公開 URL が marketing ledger に記録され、logged-out ブラウザで公開確認。以後 daily 1 post、metrics 計測 → 週次 reflect で勝ち post を模倣。
(d) 不死身 — 各 loop の process を kill しても次 tick で自動復帰し pass が完走する（launchd 実測）。verify-loops-audit の self-fix は result marker + backoff で単一 spawn。key-health gate（OpenRouter /credits + live probe）が FAIL 時は publish を止めて AgentMail 報告（fail-closed、無言死なし）。
制約: spec `2026-07-17-capafy-10k-mrr-two-loop-spec.md` の TODO 順序が正本。secrets を log/repo に出さない（leak_scan を pre-commit）。Dais 個人資金の外部流出なし（OpenRouter 補充は既存経路のみ）。テスト passing を弱体化して green にしない。
親プロトコル: 私は planner/parent — 各 phase を vcsdd（Luna impl / Sol review）で実装させ、自分で E2E 実測 verify → fix → 再 verify。**独立判定 = 介入ゼロ 14日間**（loop の publish・resubmit・投稿・self-heal が全て自走し、私は読むだけ）。それまで手放さない。
block: 同一 approach 3回 fail / IG 新 account が ban され代替不能 / Capafy 側仕様変更で resubmit 不能 — その時は state と最小の次アクションを spec に書いて停止。
