# Start here — Anicca

Anicca is an open company. Its mission is to end suffering. This repository is the public flagship: everything we can open lives here — product code, research, and evaluations. Credentials, raw operations records, and customer data are kept in a separate private repository and are never published here.

## The names

- **Bible**: **One Bible** — https://github.com/Daisuke134/anicca-ops/blob/main/team/BIBLE.md
- **Company**: Anicca, the OpenAI of behavior
- **Model**: **Manager** — understands how a person responds to a stimulus (a notification, a reply, a deliverable) and chooses the input that maximizes the response people actually want. It learns from measured stimulus → response data (post-training, not pre-training). https://huggingface.co/anicca-agent/manager-v0
- **Eval**: **ManagerBench** — one benchmark: the ability of AI to make something people want. One case is always *situation → what the AI made (stimulus) → the person's measured response* (accepted, paid, rated, continued — never impressions). https://github.com/Daisuke134/anicca/blob/main/benchmarks/managerbench/README.md
- **Product (flagship)**: **Anicca** — an affirmation and nudge app. Affirmation is the entry; the product is behavior intervention that reduces suffering. https://apps.apple.com/us/app/daily-affirmations-anicca/id6755129214
- **Many products, one engine**: six live iOS apps, Capafy, services on every platform, data sales, and client work, all on Manager + ManagerBench + the data flywheel. The goal is a monopoly on every platform, App Store included. **Life Manager**, the system that runs client work with no human in the loop, also lives in this repository and is not the company identity.

## Where things are

- Product code: `apps/` (the Anicca iOS app is `apps/mobile/anicca-ios`)
- Local setup guide: [docs/getting-started.md](docs/getting-started.md)
- Agent catalog: [docs/agents.md](docs/agents.md)
- Research articles (English and Japanese): https://aniccaai.com/blog
- Live company numbers, one dashboard: https://aniccaai.com/open

## License

MIT — see [LICENSE](LICENSE).
