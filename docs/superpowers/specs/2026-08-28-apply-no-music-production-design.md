# Apply Music-Production Prohibition Design

## Goal

Coconala Apply does not submit proposals for work whose required buyer-visible deliverable is music or an audio recording produced or edited through prompting or generative tools.

## Scope

- Change only the shared marketplace feasibility policy and Coconala application planner prompt.
- Treat composition, arrangement, performance, singing, BGM, mixing, mastering, and production or editing of music/audio as hard-prohibited when the audio itself is required.
- Keep adjacent asynchronous work eligible when it does not require producing or editing audio, such as writing about music or building music software.
- Do not add category, keyword, or regular-expression routing. The model judges the whole listing and cites exact listing evidence.
- Do not change Paid, Reply, Storefront, browser, submission, or existing application history.

## Design

Add one semantic prohibition class to `HARD_PROHIBITION_CLASSES` and one direct rule to `common_marketplace_feasibility_policy()`. The existing planner contract already requires a model-selected class plus an exact evidence excerpt, so no execution or schema change is needed.

The prompt describes the buyer-visible outcome rather than enumerating marketplace categories. Two canonical examples fix both sides of the boundary: an original BGM deliverable is prohibited, while music-service software remains eligible.

## Verification

- A focused prompt-contract test fails before the policy change and passes afterward.
- Existing planner focus tests remain green.
- A real model evaluation classifies the two canonical examples correctly without submitting anything.
- Production deployment requires a pushed main commit, immutable release, exact loaded-argv readback, and a natural Apply pass. No test application is sent solely to exercise this prohibition.

## Sources

- Coconala, `https://mag.coconala.com/articles/knowhow-rules-about-selling`: “合理的な根拠がなく実証されていない内容の表示” is prohibited.
- Anthropic, `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`: prompts should use the smallest high-signal instruction set at the right altitude and canonical examples instead of brittle edge-case lists.
- Anthropic, `https://www.anthropic.com/engineering/building-effective-agents`: start with simple prompts and improve them through comprehensive evaluation.
