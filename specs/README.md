# `anicca-oss/specs/` — single source of truth

All architectural decisions for Anicca v3 (NHOSS) live in this folder.

| File | Status | What it is |
|---|---|---|
| [`00-MASTER.md`](./00-MASTER.md) | ★ AUTHORITATIVE | The v3 spec. Read this first. Everything else either supports it or is archived. |
| [`01-EARN-AND-UBI.md`](./01-EARN-AND-UBI.md) | active | Earning architecture — 5 spouts, 3 sinks, UBI distribution channels. |
| [`02-IMITATE-AND-COOK.md`](./02-IMITATE-AND-COOK.md) | active | The "let it cook" doctrine. Imitation-first earning instinct + 6-agent parallel bootstrap plan. How architect + operator exit the loop. |
| [`03-PUBLIC-RELEASE-PREP.md`](./03-PUBLIC-RELEASE-PREP.md) | active (operational) | The squash + leak audit + grandma E2E playbook for flipping `anicca-oss` public without leaking Dais's identity. Defers to `00-MASTER.md` on conflicts. |
| `archive/` | historical | Pre-v3 specs (`ANICCA_AUTONOMY_SPEC.md`, `ANICCA_OSS_MASTER_SPEC.md`, etc.). Kept for context; superseded where they conflict with `00-MASTER.md`. |

## Editing rules

1. **One source of truth.** If a value (model name, port, threshold) appears in
   both `00-MASTER.md` and a deep-dive file, the master wins. Deep-dives must
   say "see § N of 00-MASTER.md" rather than restate.
2. **Never silently delete a section.** If a decision is reversed, move the old
   paragraph to `archive/` with a date and a one-line reason.
3. **Date every change at the top of `00-MASTER.md`.** Bump the version field.
4. **Don't add a new top-level spec file without first asking: does this belong
   as a section in `00-MASTER.md`?** Usually it does.

## How to read this folder if you've never seen it before

1. Open `00-MASTER.md`.
2. Read § 0 (Mission), § 1 (Architecture), § 8 (Naming), § 6 (Constitution).
3. Stop. That's the whole picture. The rest is detail you pull in when you're
   touching a specific layer.
