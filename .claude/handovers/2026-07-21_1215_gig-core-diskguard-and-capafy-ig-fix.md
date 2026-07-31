# Handover — gig-core disk-guard kill fix + capafy IG live-posting fix

該当する `docs/superpowers/specs/*.md` は無い(この作業はincident対応で、profitable-claude repoの`.vcsdd`側にspecがある。anicca-project側のspecsは無関係の別作業のため使わない)。

- 完了済みのspec: `/Users/anicca/profitable-claude/.vcsdd/features/gig-work-deadline-and-lock-fix/specs/behavioral-spec.md`(main merge済み、これはもう終わってる)
- **残TODOの正本はspecファイルではなくTaskList**(tool: TaskList)。該当タスクID: #14, #15(sol-gigcore-stability担当)、#16, #17, #18, #19(sol-capafy-ig-fix担当)。両subagentは名前付きで生きており `SendMessage({to:"sol-gigcore-stability"|"sol-capafy-ig-fix", ...})` で再開・継続確認できる。
  - #14/#15: `/Users/anicca/scripts/emergency-disk-guard.sh:49-52` が `pkill -9 -f "gig_pass.sh"`/`"Coconala gig"` でgig-core本体を誤爆killしている(disk空き<3GB時に毎分発火)。gig-core本体を除外しworkerのみkillする最小修正+15分以上の実測生存確認が残TODO。
  - #16/#17/#18/#19: capafy IGマーケティングloop、新アカウント`capafy.skills9582`のwarmupが今日11:20のブラウザログイン失敗(ABORT not logged in)で止まっており、`ensure_warmup_browser.py`がエラー時もrc=0を返すバグで呼び出し元が検知できない。ログイン修正+投稿ゲート修正+実投稿E2E検証が残TODO。
- 未commitの変更に関する注意点: なし(profitable-claude mainはclean、上記2件は各subagentのworktree/作業内で進行中、まだcommit前の可能性あり — 次セッションはSubagentの現在のgit statusを先に確認すること)。
