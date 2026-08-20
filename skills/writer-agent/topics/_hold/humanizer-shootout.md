---
lane: A
created: "2026-07-17T12:38:04+09:00"
voice: recit
sources:
  - https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d
  - /Users/anicca/anicca-project/.claude/skills/stop-slop/SKILL.md
  - /Users/anicca/anicca-project/.claude/skills/stop-ai-slop-jp/SKILL.md
angle: 同じ自作原文2段落を stop-slop / stop-ai-slop-jp / k16shikano の japanese-tech-writing（gist fd287c3133457c4fd8f5601d34aa817d）それぞれに通し、出力を並べて何がどう変わるか・どれが何に効くかを実測レビューする記事。
---

やること:

1. 自作の日本語原文2段落（AIスロップの典型例、まだ本skillに通していない生の文章）を1つ用意する。
2. 同じ原文を以下3つのチェックリスト/skillにそれぞれ独立に通す:
   - stop-slop（英語向けskill、SKILL.mdのルールをこの日本語原文に適用してみた場合の挙動も含めて観察）
   - stop-ai-slop-jp（日本語ネイティブ向けskill）
   - k16shikano の japanese-tech-writing gist（fd287c3133457c4fd8f5601d34aa817d）のルール
3. 3つの出力を並べて、どの指摘がどのチェックリストにしかない指摘か、どれが本質的に同じ指摘の言い換えか、どれが読者体験として一番効いたかを実測で比較する。
4. 「どれか1つを選ぶ」ではなく「どれが何のslopに効くか」の役割分担を結論として書く（例: em dash/hype vocabularyのような語彙レベルはstop-slop系が機械的に強い、主体の不在/メタ枠のような構造レベルはk16 gistが強い、等——実測してから書くこと、先に結論を決め打ちしない）。

このカード自体が「同じ原文への複数チェックリスト適用」という比較記事のフォーマットの実例でもある。記事化の際は実際に通した生の出力（Before/After）を本文に載せ、「効いた」という主観だけで終わらせないこと。
