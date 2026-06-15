#!/usr/bin/env bash
# Q30 — agent launches its OWN token to fundraise (Bankr Token Launch, enabled by default on agent bk_ key)
# bk_ key already provisioned via email OTP (no human). namespaces: wallet|agent|tokens
bankr tokens launch --name "Anicca" --symbol "ANICCA" --chain base   # @bankr/cli tokens namespace
# or REST: POST https://api.bankr.bot/token-launches  (x-api-key: bk_...)
bankr tokens list            # GET /token-launches (recent)
# Clanker alternative: clanker.world (Base, 1-tx permissionless launch)
