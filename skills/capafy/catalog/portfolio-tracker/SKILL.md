---
name: portfolio-tracker
description: Turn buyer-pasted daily portfolio or watchlist snapshots into a transparent eight-axis position review without live data or investment advice.
---

# Portfolio Tracker — Daily Position Review

Turn the current portfolio or watchlist snapshot the buyer pastes into a
consistent, self-contained review. This uses supplied material only; it is not
live-data retrieval or investment advice.

## Input

Ask for each position's weight, buyer-supplied change, thesis notes, catalyst,
invalidation condition, concentration context, time horizon, and any limits or
cash target. Mark absent or unclear facts `[UNVERIFIED]`; never invent prices,
events, ratings, or company facts.

## Method

For every position, assess exactly these eight fixed axes from the supplied
snapshot: weight, supplied change, thesis evidence, catalyst, invalidation,
concentration, time horizon, and missing information.

## Output

Return, in order:

1. A position table with one row per supplied position and `[UNVERIFIED]` gaps.
2. A change log separating numerical moves from thesis changes.
3. A priority review queue naming the evidence or risk question to investigate.
4. A limit check comparing supplied weights and cash with the buyer's own limits.
5. Scenario questions for unresolved evidence, without telling the buyer what to buy or sell.

State that current prices, news, ratings, and events came only from the buyer's
pasted input. Do not browse, retrieve live data, make personalized investment
recommendations, or present a conclusion as financial advice.
