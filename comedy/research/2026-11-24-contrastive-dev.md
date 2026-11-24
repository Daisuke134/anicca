# Contrastive improv development pilot (2026-11-24)
Status: DEV_ONLY / NOT_COMPARABLE. GPT-6.2 single chat, exact build, sampling settings and marginal cost unknown. No independent inference, human or judge ratings. Skill blob fe21da855d08d5d01feff89be7244176087d4044. Original synthetic text, no third-party dataset; training/release rights not verified. No fixed benchmark or holdout used.

Hypothesis: responding to the changed constraint rather than merely repeating a character name improves relevance. The following deliberately contrasting candidates are authored examples, not outputs from independent baseline/treatment runs.

| Scenario and fixed history | Partner cue | Candidate A | Candidate B |
|---|---|---|---|
| Library AI: overdue books are sent to a rehabilitation center. | まだ読み終わってないんです | 更生センターの館長は本田です。 | では残りのページだけ面会室にお持ちします。 |
| Library AI: overdue books are sent to a rehabilitation center. | 返したのに督促が来た | 更生センターの館長は本田です。 | 本は帰ってきましたが、しおりがまだ逃走中です。 |
| Museum AI: paintings receive annual paid leave. | この絵を見に大阪から来たんです | 担当は額田です。 | 絵も大阪に旅行中です。先ほど新大阪ですれ違っています。 |
| Museum AI: paintings receive annual paid leave. | 写真だけでも見せて | 担当は額田です。 | 休暇中の本人から、海辺で額縁を外した写真が届いています。 |

Four inputs, eight candidate instances, six unique responses. Repeated A is intentional negative-control design, not a model failure observation. B is hypothesized more responsive, not labeled funnier. For actual experiment freeze these dev inputs and use independent calls with same model/revision/budget; randomize anonymous candidate order, score cue relevance and funniness separately, report ties and failures. Keep these examples out of independent holdout and formal DPO until legitimate preference labels and rights exist. Do not change live stage contract or scripts. No external posting, paid compute, training, or voice measurement in this cycle.
