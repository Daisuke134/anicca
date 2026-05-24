# Common Patterns

## API route with Prisma

```ts
// app/api/items/route.ts
import { auth } from '@clerk/nextjs/server'
import { prisma } from '@/lib/prisma'
import { NextResponse } from 'next/server'

export async function GET() {
  const { userId } = auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const items = await prisma.item.findMany({ where: { userId } })
  return NextResponse.json(items)
}

export async function POST(req: Request) {
  const { userId } = auth()
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json()
  const item = await prisma.item.create({ data: { ...body, userId } })
  return NextResponse.json(item, { status: 201 })
}
```

## Form with Zod validation

```tsx
'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const schema = z.object({
  title: z.string().min(1, 'Required').max(100),
  description: z.string().optional(),
})

type FormData = z.infer<typeof schema>

export function CreateItemForm({ onSuccess }: { onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    await fetch('/api/items', { method: 'POST', body: JSON.stringify(data) })
    onSuccess()
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input {...register('title')} placeholder="Title" />
      {errors.title && <p className="text-red-500 text-sm">{errors.title.message}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating...' : 'Create'}
      </Button>
    </form>
  )
}
```

## Zustand store

```ts
// stores/useAppStore.ts
import { create } from 'zustand'

interface AppState {
  items: Item[]
  setItems: (items: Item[]) => void
  addItem: (item: Item) => void
}

export const useAppStore = create<AppState>((set) => ({
  items: [],
  setItems: (items) => set({ items }),
  addItem: (item) => set((state) => ({ items: [...state.items, item] })),
}))
```

## Server component with data fetch

```tsx
// app/dashboard/page.tsx
import { auth } from '@clerk/nextjs/server'
import { redirect } from 'next/navigation'
import { prisma } from '@/lib/prisma'

export default async function DashboardPage() {
  const { userId } = auth()
  if (!userId) redirect('/sign-in')

  const items = await prisma.item.findMany({
    where: { userId },
    orderBy: { createdAt: 'desc' },
  })

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      {items.map(item => (
        <div key={item.id} className="p-4 border rounded mb-2">{item.title}</div>
      ))}
    </div>
  )
}
```

## Feedback widget (always include)

```tsx
// components/FeedbackWidget.tsx
'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export function FeedbackWidget() {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [sent, setSent] = useState(false)

  const submit = async () => {
    await fetch('/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ feedback: text, url: window.location.href }),
    })
    setSent(true)
  }

  if (!open) return (
    <button onClick={() => setOpen(true)}
      className="fixed bottom-4 right-4 bg-black text-white px-3 py-2 rounded-full text-sm">
      Feedback
    </button>
  )

  return (
    <div className="fixed bottom-4 right-4 bg-white border rounded-lg p-4 shadow-lg w-72">
      {sent ? <p className="text-green-600">Thanks! 🙏</p> : (
        <>
          <Textarea placeholder="What's on your mind?" value={text} onChange={e => setText(e.target.value)} />
          <div className="flex gap-2 mt-2">
            <Button size="sm" onClick={submit}>Send</Button>
            <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </>
      )}
    </div>
  )
}
```
