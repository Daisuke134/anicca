# skills/human-funded/

★ Convention (Dais 2026-06-28) ★

This subfolder holds earn skills that REQUIRE a human-in-the-loop step (= installer's
existing credentials, OAuth login, KYC account, or a 1-tap browser confirmation).

A skill lives HERE when it CANNOT yet be executed by a self-funded child instance
that has only its own wallet and zero installer credentials.

A skill LEAVES HERE for the parent `skills/` directory (= general / replicable /
wallet-only) ONLY when it can be done end-to-end with NO human-in-loop step — at
that point any Anicca instance (human-funded OR self-funded) can run it.

Promotion rule:
  human-funded skill → core skill iff (creds_required == [] AND no human tap remains)

Boot-time activation:
  install.sh scans ~/.openclaw/.env + ~/.anicca/.env and ACTIVATES only those
  human-funded skills whose required env vars are all present on the install.
  Wallet-only core skills (skills/earn/{x402-sell,hl-trade,token-launch,
  execute-yield, etc.}) always activate.

Initial intent (= the candidate skills considered for this subfolder; the actual
build order + which ones to ship first lives in a spec inside this same worktree
and is finalized by Dais's go before any code lands):

  ・ affiliate (e.g. Amazon Associates JP, moshimo, A8) — needs installer's
    Amazon Associates account
  ・ content royalty (note, Substack, dev.to) — needs installer's platform sessions
  ・ Capafy publisher — needs installer's Capafy API key
  ・ app-store ASO — needs installer's App Store Connect API key
  ・ Fiverr / Coconala / Upwork gig — needs installer's account + Payoneer
  ・ social poster (X, TikTok, IG, YT) — needs installer's account creds

★ Anti-pattern (= the thing this convention exists to PREVENT) ★

Do NOT bake the installer's specific creds into the OSS code. The skill code stays
parameterized over env vars; the env vars live in ~/.openclaw/.env or ~/.anicca/.env
on each install separately. My install (= Dais's Tier 1) provides his Amazon /
Capafy / etc.; a stranger's install provides theirs; a self-funded child's
install provides NONE.

Worktree: this folder is being created from the `feature/human-funded` worktree
(`~/anicca-human-funded/`). All work targeting this convention happens in that
worktree, NOT on main directly.
