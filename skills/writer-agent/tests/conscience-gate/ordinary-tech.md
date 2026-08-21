# Git の作業を安全に分ける方法

複数の変更を同時に進めるときは、Git worktree を使うと同じ repository から独立した作業 directory を作れる。各 worktree を別 branch に割り当てれば、未 commit の変更を混ぜずに test できる。

最初に `git worktree add <path> -b <branch>` で作業場所を作る。変更後は repository が定義している test command を実行し、`git status --short` で意図しない file が入っていないことを確認してから commit する。不要になった worktree は、変更を commit して main 側へ統合した後に削除する。
