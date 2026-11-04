Primary Model: Claude Sonnet 5.5 · category: 分析 · tags: wnba, basketball, rotations, matchup analysis, sports writing

Demand rank: 1

## Offline selection notes

The current C6 opportunity inventory selects the uncovered Analysis shelf first at 3,230 observed sales. Its top winners are Ocup Football Analysis (3,144 sold), MLB Baseball Analysts (41), and Otata Baseball Analysis (31): sports buyers bring a named game's material and receive an analysis product. The release-owned `sales_selector.py` was evaluated offline through its pure function and returned `signal: none`; no internal winning category is claimed. The base catalog contains NBA slate, college-basketball bubble, and volleyball rotation briefs but no WNBA-specific rotation-and-assignment card. This candidate changes the league, input, output, and buyer job: supplied WNBA lineup stints and defensive assignments become a rotation stress-test card for WNBA writers, coaches, and podcast producers.

## Renewal reason

Each game brings different buyer-pasted five-player stints, assignment notes, availability context, and coverage questions. A prior card cannot answer the next game's rotation decision.

## Unit economics

At the required $0.12 per request, modeled cost is $2.40/week (20 requests), $4.80/month (40), and $57.60/year (480). Those amounts are below 60% of each plan's net after the 20% fee: $4.80, $12.00, and $72.00 respectively. The price ladder follows the documented analysis-market band used by MLB Baseball Analysts.

| cycle | price | cap | trial |
|---|---:|---:|---|
| week | $9.99 | 20 | No Free Trial |
| month | $24.99 | 40 | No Free Trial |
| year | $149.99 | 480 | No Free Trial |

## Title
WNBA Rotation Matchup Card

## shortDescription
Paste one WNBA game's rotation notes, defender assignments, and availability context for a source-bounded lineup card, coverage angles, and verification queue.

## welcomeMessage
👋 I turn your pasted WNBA rotation notes and defensive assignments into a focused matchup card. Example: "Harbor closes small with Rivera at point and Chen as its only listed interior defender; Summit puts its tallest scorer on Chen's side; Rivera initiates late-clock actions; current replacement guard is unknown."

## detailedDescription
✨ What you get
- A rotation table that separates supplied lineup stints, matchup pressure points, and unknowns.
- Two or three evidence-bound angles for a WNBA article, coaching discussion, or podcast rundown.
- Conditional availability scenarios and a verification queue for the next update.

⚙️ How it works
1. Paste your WNBA game notes (new each time — the five-player stints, assignments, and status notes change).
2. I organize and analyze only the material you provide into a rotation matchup card.
3. You get a ready-to-use rotation table, supported coverage angles, and facts to confirm.

💡 Example
Input: "Harbor closes small with Rivera at point and Chen as its only listed interior defender. Summit puts its tallest scorer on Chen's side. Rivera initiates late-clock actions. The replacement guard is unknown."
Output: "The supplied closing group concentrates late-clock initiation with Rivera while Chen carries the only listed interior-defender role. The supported question is whether Summit's stated size assignment tests that interior workload; the replacement guard remains [UNVERIFIED]."

👤 Who it's for
WNBA beat writers, coaches, podcast producers, and serious fans who bring their own rotation notes and want a disciplined matchup read.

Honesty: This is text analysis from your pasted material and model knowledge. It does not browse, retrieve live scores, rosters, schedules, odds, or injury reports; it does not place wagers or guarantee a game outcome.

### What makes it different
- **Rotation-specific input:** it reads supplied five-player stints and defender assignments, rather than a whole NBA slate, a college bubble case, or a volleyball sideout pattern.
- **Editorial output:** it produces a WNBA rotation matchup card and verification queue for a writer, coach, or producer—not a score prediction.
- **Honesty:** it reasons only over buyer-pasted material and visibly labels missing current facts `[UNVERIFIED]`.
