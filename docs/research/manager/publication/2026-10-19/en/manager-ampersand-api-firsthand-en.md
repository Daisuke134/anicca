# We Actually Ran Ampersand v0.1: A Firsthand API Walkthrough and What It Does Not Prove

**Anicca / Manager Research — November 3, 2026**

Reading a model card is useful. Calling a model yourself is different. We ran a fresh, authenticated request to **humans& Ampersand v0.1** through its documented Agents API on November 3, 2026. This article explains the observable integration steps and what we learned without claiming we reproduced humans&'s training or benchmark suite.

## What we executed

**Public execution receipt:** [GitHub Actions run 41618299490](https://github.com/Daisuke134/life-manager/actions/runs/41618299490). Our earlier [October 22 research run](https://github.com/Daisuke134/life-manager/actions/runs/39710166900) independently demonstrated that the same repository can authenticate and fetch one completed model response.

We used the official OpenAI Python client `openai==3.24.0`, changed its base URL to `https://ampersand.humansand.ai/v1`, and used the model ID `ampersand-v0.1`. The GitHub Actions workflow injects an existing API key via a protected repository secret. No key is committed or copied into this article.

The code first called `GET /models` and checked that the model was accessible. Then it created one *fictional* session with `environment={"type":"none"}`, no tools, and a simple collaboration question about a teammate who had already disclosed they could not attend a proposed meeting. We consumed the event stream until the session returned to `agent.session.idle`.

The outcome was unambiguous at the **API-operation level**:

| Check | November 3, 2026 |
|---|---|
| Credential and model listing | PASS |
| Real Agents API session | Created |
| Terminal stream event | `agent.session.idle` |
| Assistant output text | 359 characters |
| Provider status / workflow | GitHub Actions success |
| External tools or real people contacted | None |
| Comparative model benchmark | Not run |
| Independent long-term human outcome | Not measured |

We observed that the response recommended raising a known meeting conflict without taking the scheduling decision away from the team. This is our **paraphrase of one fictional response**, not a reprint of the provider's output. One example is not a quantitative quality estimate, and an authenticated response is not evidence of superior social intelligence.

## A second live run: real follow-up in the same session

We subsequently ran a second, separately dispatched **two-turn** educational session via the same official service. [GitHub Actions run 41619141514](https://github.com/Daisuke134/life-manager/actions/runs/41619141514) is the exact independent execution receipt. The first fictional response completed with 546 characters. We then submitted an updated scheduling scenario to **the same session** through the officially documented `sessions.events.create` method, using an idempotency key, and streamed the follow-up turn to completion (465 characters). The provider returned **four saved conversation items and two completed turns**.

This additionally establishes real session persistence, event submission and saved-turn readback in our integration. It does not establish long-term collaboration quality, human simulation accuracy, or other experimental effects. The run was not a comparative benchmark and was never given personal customer information or external action tools. We preserved completion metadata rather than publishing the provider's entire output.

## What Ampersand is technically designed to do

The developers' official [model card](https://ampersand.humansand.ai/blog/model-card.html) describes a model trained to collaborate across extended interactions, including when it is better to ask, wait, or decline to intrude. Their companion human-simulation research, **Persimmon**, supplies simulated user interactions for aspects of training and evaluation. This is not the same as showing that the model predicts unknown real customers' purchases or that its interventions improve a real person's welfare.

The integration is also not a generic chat-completions-only interface. The [Agents API documentation](https://ampersand.humansand.ai/docs/GUIDES.html) describes sessions, events, function tools, persisted items and turns, reconnection, cancellation and billing. Notable operational details include:

- A server-side session has a lifecycle; reaching an idle event means the service has stopped working, not that your real-world goal has been achieved.
- Tools, if enabled, run in the **client's own application**. `environment={"type":"none"}` does not provide hosted browsing or access to private company services.
- Event submissions support idempotency keys; this does not make external financial or messaging effects automatically idempotent.
- A model can finish silently. Applications must not equate absence of text with a network failure.
- Session history and context compaction are different from updating a model's learned weights.

These distinctions are essential when developing a dependable agent, whether or not the reasoning model is developed in-house.

## What about Persimmon and comparative evaluation?

The public Persimmon and Ampersand research introduces a promising separation of **simulated user behavior** and an **agent policy trained to cooperate**. But we have not downloaded proprietary weights, trained Ampersand ourselves, reproduced its private Persimmon simulations, or performed an independent long-horizon comparison.

The published [terms of service](https://ampersand.humansand.ai/terms) impose restrictions on competitive benchmarking and the use of outputs for competing-model training. Our one-shot use was a normal, fictional API tutorial, not a competitive benchmark. We do not reuse the model's output as training material. We have requested clarification about permissions for separately authorized comparative research; that permission should not be assumed.

## What this teaches us about Manager

We want an auditable loop connecting response prediction, permissible decisions, execution and independently observed outcomes. The Ampersand API exercise helped clarify the **execution/session** part, not validate a general human-behavior predictor.

A rigorous follow-up would require a documented task definition, permitted access, independent human-reference evidence, matched baselines and a fixed evaluation procedure. If the tested provider's terms prohibit a use, permission must come first. Competitive model results should be presented separately from this engineering demonstration.

Our conclusion is deliberately narrow: **Ampersand v0.1 can be called from our GitHub-hosted environment using its documented Agents API, and a fictional session returned a completed answer on November 3, 2026.** The response was usable as an example of a collaboration-oriented recommendation; it was not a measurement of general intelligence, causal intervention ability or real-world welfare impact.

## Original sources

- [Ampersand model card](https://ampersand.humansand.ai/blog/model-card.html)
- [Ampersand API integration guide](https://ampersand.humansand.ai/docs/GUIDES.html)
- [Ampersand API reference](https://ampersand.humansand.ai/docs/API_REFERENCE.html)
- [Ampersand terms](https://ampersand.humansand.ai/terms)
- [Persimmon model research](https://persimmon.humansand.ai/blog/persimmon.html)
- [The exact November 3 execution record](https://github.com/Daisuke134/life-manager/actions/runs/41618299490)
