# earn/gig — four direct Coconala revenue owners

The current runtime is four independent launchd owners, not a shared tmux core:

| lane | label | entrypoint |
|---|---|---|
| Apply | `ai.anicca.hf-gig-apply-direct` | `scripts/application_direct.py` |
| Reply | `ai.anicca.hf-gig-reply-detector` | `scripts/reply_detector.py` |
| Paid | `ai.anicca.hf-gig-paid-direct` | `scripts/paid_direct.py` |
| Storefront | `ai.anicca.hf-gig-storefront-direct` | `scripts/storefront_direct.py` |

`run.sh` is a read-only aggregate status entrypoint. It never starts, restarts, or substitutes for an owner.
Hermes gateway is a separate continuing service and is not an earning-loop owner.
