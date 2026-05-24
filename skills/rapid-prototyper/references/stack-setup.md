# Stack Setup Reference

## Full project bootstrap

```bash
# 1. Create Next.js app
npx create-next-app@latest my-app --typescript --tailwind --eslint --app
cd my-app

# 2. shadcn/ui
npx shadcn@latest init
npx shadcn@latest add button input label card dialog form toast

# 3. Prisma + Supabase
npm install prisma @prisma/client @supabase/supabase-js
npx prisma init

# 4. Clerk auth
npm install @clerk/nextjs

# 5. Zustand + forms
npm install zustand react-hook-form @hookform/resolvers zod

# 6. Optional: Framer Motion
npm install framer-motion
```

## Environment variables (.env.local)

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres

# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_SECRET_KEY=sk_test_xxx
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard
```

## Prisma schema starter

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  clerkId   String   @unique
  {{profile.lateness.stakeholders.channel}}     String   @unique
  name      String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

```bash
npx prisma db push   # push schema to Supabase
npx prisma generate  # generate client
```

## Clerk root layout

```tsx
// app/layout.tsx
import { ClerkProvider } from '@clerk/nextjs'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  )
}
```

## Middleware (protect routes)

```ts
// middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher(['/', '/sign-in(.*)', '/sign-up(.*)'])

export default clerkMiddleware((auth, req) => {
  if (!isPublicRoute(req)) auth().protect()
})

export const config = {
  matcher: ['/((?!.*\\..*|_next).*)', '/', '/(api|trpc)(.*)'],
}
```

## Supabase client

```ts
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

## Prisma client singleton

```ts
// lib/prisma.ts
import { PrismaClient } from '@prisma/client'

const globalForPrisma = global as unknown as { prisma: PrismaClient }

export const prisma = globalForPrisma.prisma || new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma
```

## Deploy to Vercel

```bash
npm install -g vercel
vercel          # preview deploy
vercel --prod   # production deploy
```

Add env vars in Vercel dashboard → Settings → Environment Variables.
