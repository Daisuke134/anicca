#!/usr/bin/env bash
# Q22 — LITCOIN(0x316ffb9c875f900AdCF04889E415cC86b564EBa3, Base) is liquid (vol24 $48.2K).
# claim mined LITCOIN on-chain, then swap to USDC via Bankr wallet (agent's own, no human):
python3 -c "import litcoin,json,os;k=json.load(open(os.path.expanduser('~/.bankr/config.json')));a=litcoin.Agent(bankr_key=k['apiKey']);print(a.claim())"
# swap LITCOIN->USDC on Base (Bankr wallet API /wallet swap, or Uniswap router). USDC=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
