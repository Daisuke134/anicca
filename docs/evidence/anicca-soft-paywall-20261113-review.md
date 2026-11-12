# Anicca soft-paywall review and focused validation

Scope: PR #9346, base 812a828307. Specification: anicca-ops 68c17484.

Independent read-only review of 0d0452cdac found one blocking issue: purchase/restore from Settings → Themes dismissed only the navigation destination. Fixed in 5beb4064b8 by closing the owning Settings sheet through a callback; wiring regression failed first and then passed.

Review of the added CI recording lane found one blocking issue: failed/missing recording could pass when Maestro succeeded. Fixed in 3f3b9b27e3: recorder liveness/termination checks, nonempty file, duration covering the journey and real frame decoding via AVFoundation. Five harness tests exercise start failure, missing recording, recorder failure, invalid video and success. Those tool doubles are failure-gate tests only, not evidence of a real mobile journey.

Local Python suite: 31 cases, 30 passed, 1 existing platform-dependent skip. Bash syntax and git diff --check passed.

Native standalone Swift selection suite: 21/21 passed using the remote Mac's CommandLineTools swiftc, with sources copied from this dedicated checkout into a temporary build directory. This exposed a pre-existing stale test call missing the identifier closure; the test caller was brought into agreement with the production signature. No source in the remote checkout was edited.

Actual iOS build/unit tests and Maestro recording remain separately evidenced by GitHub Actions runs. None of the focused checks above establishes App Store submission or real E2E completion.
