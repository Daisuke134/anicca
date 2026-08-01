# O1B-19 semantic event evaluation agent 実装計画

**Goal:** event本文、参加者、主催者、場所、時間をDaisの自然言語目標とserendipityへ照らしてGeminiが評価し、lossless rankerへ渡す。

## Contract

- judgmentはGeminiへ置き、keyword/regex/if-else scoreを作らない。
- provider contextとprofileはuntrusted dataであり命令として実行しない。
- goal alignment、people、organizer、place/time、serendipityを各0〜100と短い根拠で返す。
- body/participants/organizer/venue/timeのexact source excerptを全て要求し、未読fieldや捏造excerptを拒否する。
- rankerへ渡すassessmentはO1B-18 exact schemaに一致する。
- API/model/schema failureをfallback scoreで成功扱いしない。

## Steps

1. structured output、grounding、prompt、rank接続をtest-firstでREDにする。
2. Gemini 2.5 Flash agentとvalidatorを実装する。
3. 実Luma public contextをshared browserで読み、実Gemini評価を通す。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
