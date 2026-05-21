import Section from '@/components/base/Section'
import { Card } from '@/components/ui/card'
import FadeIn from '@/components/base/FadeIn'
import { Target, Mic, Repeat, MessageSquare, Shield, Code } from 'lucide-react'

const features = [
  { Icon: Target, title: 'Leads, not waits', text: 'Anicca moves first at the right moment.' },
  { Icon: Mic, title: 'Voice‑only, tray‑only', text: 'No UI to manage—works for anyone.' },
  { Icon: Repeat, title: 'Habit engine', text: 'Schedules that run themselves' },
  { Icon: MessageSquare, title: 'Slack follow‑through', text: 'Drafts ready at your set times' },
  { Icon: Shield, title: 'Privacy‑first', text: 'Local‑first, least privilege, no telemetry.' },
  { Icon: Code, title: 'Open Source', text: 'Transparent by default.' },
]

export default function KeyFeatures() {
  return (
    <Section id="features">
        <h2 className="text-3xl font-bold text-center">Key Features</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {features.map((f) => (
            <FadeIn key={f.title}>
            <Card className="p-6 hover:shadow-md transition">
              <div className="mb-3"><f.Icon className="h-6 w-6 text-foreground" /></div>
              <h3 className="text-lg font-semibold text-foreground">{f.title}</h3>
              <p className="mt-2 text-muted-foreground">{f.text}</p>
            </Card>
            </FadeIn>
          ))}
        </div>
    </Section>
  )
}


