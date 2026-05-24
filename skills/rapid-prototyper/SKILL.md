---
name: rapid-prototyper
description: >-
  Ultra-fast proof-of-concept and MVP development. Use when building new web apps,
  prototypes, or MVPs from scratch where speed matters over perfection. Specializes
  in the canonical fast-stack: Next.js 14 + Supabase + Clerk + shadcn/ui + Prisma.
  Triggers when user asks to "build", "prototype", "create a quick app", "spin up an MVP",
  or wants a working thing fast. NOT for small one-liner fixes or edits to existing codebases.
---

# Rapid Prototyper

Build working MVPs in days, not weeks. Speed-first. No over-engineering.

## Mindset

- Ship working code over elegant architecture
- Use pre-built components and BaaS over custom infra
- Validate the idea first — optimize later
- Include analytics and feedback hooks from day one

## The Stack

**Always default to this unless there's a specific reason not to:**

| Layer | Tool | Why |
|---|---|---|
| Framework | Next.js 14 (App Router) | Full-stack, fast setup |
| Database | Supabase (PostgreSQL) | Instant DB + realtime + storage |
| Auth | Clerk | Drop-in auth in minutes |
| UI | shadcn/ui + Tailwind | Beautiful components, no design needed |
| ORM | Prisma | Type-safe DB access |
| State | Zustand | Simple, no boilerplate |
| Forms | React Hook Form + Zod | Validation out of the box |
| Animation | Framer Motion | Polish when needed |

See `references/stack-setup.md` for full setup commands and boilerplate.

## Workflow

### Phase 1 — Define the core (5 min)
1. What is the ONE thing users do in this app?
2. What does success look like? (define metric now, not later)
3. What's the minimum to test the hypothesis?

### Phase 2 — Scaffold (15–30 min)
```bash
npx create-next-app@latest my-app --typescript --tailwind --eslint --app
cd my-app
npx shadcn@latest init
```
Then: add Prisma, Supabase client, Clerk provider. See `references/stack-setup.md`.

### Phase 3 — Build core user flow only
- One happy path first
- Skip edge cases, error states, loading states until core works
- Use shadcn components — don't style from scratch

### Phase 4 — Add feedback collection
- Always add a simple feedback mechanism (textarea + submit)
- Add Vercel Analytics or PostHog from day one
- Log key actions

### Phase 5 — Deploy
```bash
npx vercel --prod
# or: push to GitHub → auto-deploy on Vercel
```

## Critical Rules

- **Never** spend more than 1 hour on auth — use Clerk
- **Never** design a custom DB schema without checking if Supabase can handle it with defaults
- **Always** deploy to a URL (even dev preview) before calling it done
- **Always** ask: "Is this feature necessary to test the core hypothesis?"

## Success Metrics

- Working app deployed to URL: ✅ done
- Core user flow completable end-to-end: ✅ done
- At least one real user can test it: ✅ done
- Feedback collection in place: ✅ done

## References

- `references/stack-setup.md` — Full setup commands, env vars, boilerplate code
- `references/patterns.md` — Common patterns: auth routes, DB queries, API routes, forms
