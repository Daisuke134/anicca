# Writer global money handover

- Spec/TODO SSOT: `/Users/anicca/Projects/life-manager-main/docs/ARTICLE-LAUNCH-TODO.md` の `Current Writer money order`。設計補足は `/Users/anicca/Projects/life-manager-main/docs/superpowers/specs/2026-08-20-writer-loop-life-manager-consolidation.md` の `24/7とglobal three-daily experiment`。
- Repository: `/Users/anicca/Projects/life-manager-main`。実装用worktreeは `/Users/anicca/Projects/life-manager-main/.worktrees/writer-w0-lock-recovery`。handover branchは `handover/writer-global-money-20260829`、base mainは `b2c0f94cfd64d189d00e4b1ccace5a3f24a5c337`。共有main checkoutと他worktreeは触らない。
- Current item: W2。installed Writer releaseは `f7214aac85304eef09fb930d36418f85d6fb23c6`。`article-daily`の最新wakeは空き約7.37GBでdisk gateを通り、claim-loop `MODEL_UNAVAILABLE`でgeneration前にexit 75。
- Current run: `20260828-195017`。git hashとbaseline strategy receiptだけ。article、headline、publication state、public ledger rowは0。新規公開は0。
- Last live readback: Note JA / Substack JA / Substack ENは8月21日、X Article JAは8月20日。received writing revenueは0。
- Completed: fixed 5GiBを廃止しcapacity receipt契約へ変更。active-four canary後にJA/EN/IDの3 source articles/day、14日42本を行うspecはmainへmerge済み。
- First safe resume action: fresh fetch後にlaunchd owner不在、最新claim receipt、run/ledger/publication stateを再読する。`MODEL_UNAVAILABLE`がcurrentなら既存`writer-claim-loop`を1回だけkickstartしてwatchし、supplyが`FILLED|SUFFICIENT`になった時だけ既存`article-daily`を発火する。別executorを作らない。Macをrestartしない。
- Goal text: `.claude/handovers/2026-08-29_1822_writer-global-money_goal.txt`
- Live notes: `.claude/handovers/2026-08-29_1822_writer-global-money_execution-notes.md`
