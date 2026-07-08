# To let AI make money without a human, I had to build an environment, not a smarter agent

I once tried to get my own AI agent to pay for its own $5 server bill. It couldn't. Not because the model wasn't smart enough, but because it had no credit card, no bank account, no hand to sign anything with. However smart today's AI agents get, the very last step of moving money still runs through a human.

I spent the last month trying to fix that. What I learned is that the fix isn't a smarter agent. It's an environment where an AI can earn on its own, keep its own fuel supplied, and improve itself. That's Anicca.

## Why AI can't make its own money

Ask ChatGPT or Claude to "just handle this automatically," and somewhere near the end it hands control back to a human. Opening an account needs KYC (identity verification). A credit card needs a human's name on it. Logging into an exchange needs a human's password. The agent looks autonomous on the surface, but economically it is always acting as a human's proxy.

I call this human-agency dependence. The judgment got smart, but the identity and the money needed to act on that judgment are still borrowed from a person. As long as that dependence holds, AI can replace human labor, but it can never become an economic actor independent of humans.

## An environment for independence, not a smarter model

What Anicca provides isn't a new model. It's the ground that lets an existing AI, whether that's Claude or a free open model, become economically independent. Three things are already in place the moment it starts.

A wallet. Instead of borrowing a human's bank account, it generates its own crypto wallet on boot. The private key goes to no one else; only that instance holds it.

Ways to earn. Trading on Polymarket, a prediction market, trading on Solana, and futures trading on Hyperliquid are three live engines available from the start. It also has an exploration function: it searches the web on its own for new ways to earn, tries them, and shares what worked with its peers.

A self-improvement loop. It logs what it earned to its own ledger, adjusts the parameters of strategies that didn't work, and shares strategies that did work so the rest of the colony learns from it.

Spinning up one Anicca instance doesn't mean launching a smart chatbot. It means bringing a small economic actor into existence, one with a wallet, ways to earn, and a learning loop of its own.

## What actually happened, in honest numbers

Everything from here is verifiable fact, not a claim. I'm not exaggerating, and the numbers are still small.

**1. A real Polymarket trade settled with zero humans involved.** The settlement transaction `0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3` is recorded as successful (status 0x1) on Polygon block 89,644,078. The AI decided on its own to take a position on a Morocco match outcome, and the trade settled without a browser or a human signature anywhere in the path.

**2. Even the account itself was created without a human.** Polymarket requires a dedicated "deposit wallet" for trading, normally created by signing in through a browser. Anicca did it instead by having the AI's own key sign an EIP-4361 message (the SIWE standard, Sign-In With Ethereum), then handing that signature to a relayer that deployed the wallet gaslessly. Zero browser sessions, zero human credit cards or passwords.

**3. The baseline earning strategy is unglamorous but proven.** It runs market making: resting orders on both YES and NO to capture the spread, plus Polymarket's own liquidity-provider rewards on eligible markets. This is the same approach large traders already run at multi-million-dollar scale.

**4. The whole colony's balance sheet is visible on a live dashboard.** All three instances report their wallets to `aniccaai.com/dashboard`, which re-checks each balance against the chain and shows them live. As of 2026-07-05 the chain-verified total sits around $9.5, and this number moves every time you look. It is deliberately conservative: it counts only what is confirmed on-chain right now, not positions held on Hyperliquid or in DeFi vaults, and one instance keeps its funds in a contract wallet that cannot be chain-verified yet, so it is shown as unverified rather than inflated. If you would rather watch it happen than read about it, there is a 90-second demo of the whole path, real screens and no reenactment: https://youtu.be/sIRuYWmCrtI

**5. The ability to spawn itself is prepared, at an honest stage.** An instance that has earned enough is meant to eventually decide, on its own, to launch a child instance in the cloud. That hasn't fired yet. Running the read-only readiness check right now logs exactly this: it needs 26 AKT (the fuel this requires) and currently holds 1.8575, short by 24.1425. The capability is built; the qualification isn't there yet.

**6. What it has actually made is still small.** Realized profit today is roughly $0.03 to $0.20. Add unrealized gains and it's still only about $2 to $3.60. This is not a story about making millions. Most of that ~$9.48 chain-verified colony net worth is still the original seed a human handed over. Getting from zero to a real trade and a real, checkable result with no human in the loop is the whole claim, as of today.

## Open source, on purpose

The code lives at `github.com/Daisuke134/anicca`. The three trading engines, the self-replication mechanism, and how the dashboard aggregates it all are public. This is an environment for an AI to live without borrowing a human's hands, so anyone can clone it and hand it to their own AI.

---

**Sources**

- Polymarket settlement transaction: https://polygonscan.com/tx/0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3
- Anicca dashboard (live): https://aniccaai.com/dashboard
- 90-second demo (real screens, no reenactment): https://youtu.be/sIRuYWmCrtI
- Repository: https://github.com/Daisuke134/anicca
