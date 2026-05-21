import Section from '@/components/base/Section'

const items = [
  { title: 'Local‑first', text: 'Session and schedules live in ~/.anicca.' },
  { title: 'Least privilege', text: 'Public PKCE + short‑lived tokens; OAuth tokens stay server‑side.' },
  { title: 'No telemetry', text: 'No analytics collection.' },
  { title: 'No screen recording', text: 'The app does not capture or upload screenshots.' },
  { title: 'Minimal audio streaming', text: 'Audio streams to the realtime model only to enable the experience.' },
  { title: 'Local logs', text: 'Logs stay on your Mac.' },
]

export default function Privacy() {
  return (
    <Section id="privacy">
        <h2 className="text-3xl font-bold text-center">Privacy‑first by design</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {items.map((i) => (
            <div key={i.title} className="flex gap-4">
              <div className="mt-1 inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">✓</div>
              <div>
                <h3 className="font-semibold text-foreground">{i.title}</h3>
                <p className="text-muted-foreground">{i.text}</p>
              </div>
            </div>
          ))}
        </div>
        {/* lock line removed per request */}
    </Section>
  )
}


