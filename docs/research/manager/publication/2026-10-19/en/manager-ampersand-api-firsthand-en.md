# We Asked an AI When to Speak Up. Then We Changed the Story.

**Anicca Research | November 3, 2026**

Sam cannot make Friday, and the team is about to schedule the meeting for Friday anyway. We asked an AI whether it should speak up, then changed the situation: Friday might work for Sam, but nobody has confirmed it.

The distinction is small enough to disappear in a busy group chat. It is also the difference between correcting a known mistake and treating uncertainty as permission to decide for someone else. An assistant that remembers the first message too firmly could become the person in the room who keeps explaining your own availability to you.

This was a fictional scheduling exercise, conducted through a real AI service. Its subject was Ampersand, a model from the company humans&. Our first response advised flagging the known conflict while leaving the scheduling decision to the team. Our follow-up exercise established something more modest than a successful change of mind: the service accepted a changed situation and completed another turn in the same conversation. The saved public record does not contain that second answer's wording.

![Two versions of a meeting conflict: known unavailability versus uncertain availability. Both turns completed, but only the first response has a publicly described recommendation.](https://aniccaai.com/blog/manager/media/6bcbad0efcf28550d6fd62d008b23ab671d897f7ffe7925fc72b1f87afc61c3e.png)


## An AI company interested in the room around the task

If you know ChatGPT, the familiar interaction is straightforward: ask a question, receive an answer. A group conversation makes that arrangement harder. The person asking may have forgotten something another participant said. Two people may want different outcomes. An answer that sounds helpful to one could make extra work for someone else.

[humans& introduces Ampersand](https://ampersand.humansand.ai/blog/) around this problem of collaboration. Its stated ambition is to build AI that helps people achieve goals together, taking account of what happens after a message is sent. That gives the company a different design problem from simply producing a polished response to the latest instruction.

Consider the Friday meeting. Finding an open calendar slot would be a scheduling task. Deciding whether to mention Sam's earlier objection involves memory, timing and social judgment. The group may welcome a short reminder. It may resent a lecture. And if Sam has already corrected the information, repeating the objection could actively confuse everyone.

Those are ordinary human complications, which is why they matter. An assistant embedded in daily work would encounter them amid messages about deadlines, dinner plans and unfinished documents. Its behavior would be experienced as a sequence of interruptions and omissions, rather than a score on a single impressive answer.

The company's purpose is intelligible even before one accepts any performance claim: build an assistant capable of participating in that ongoing situation. Our exercise was a way to examine a small piece of the idea firsthand.

## Persimmon plays the people; Ampersand learns to collaborate

There are two names to keep straight. [Persimmon](https://persimmon.humansand.ai/blog/persimmon.html) is humans&'s model for simulating user behavior. It generates how people might respond across conversations. Ampersand is the collaborator being trained through such interactions.

A useful analogy is a rehearsal. Actors play people with different concerns; a participant tries an intervention and sees how the scene develops. In humans&'s approach, simulated users supply the other side of that interaction. The analogy explains the roles, without establishing how faithfully the rehearsal represents life outside it.

According to the [Ampersand model card](https://ampersand.humansand.ai/blog/model-card.html), training uses extended social scenarios with feedback on the consequences of the model's actions. Its intended behavior includes contributing information, asking questions and waiting without posting. The stated aim is to support human judgment.

We accessed Ampersand. We did not run Persimmon, inspect its private training examples or reproduce the simulation process. Calling the collaborator gives us an observable answer from that service; it does not let us see the simulated people behind its training.

That separation matters for interpreting the story. A scheduling response can illustrate how a model approaches collaboration. It cannot tell us whether the underlying simulations accurately predict an unfamiliar person's choices.

### We also tried the public Tutor model

humans& also lists **Ampersand Tutor**, a separate public model intended for teaching. In a [new authenticated run on November 3](https://github.com/Daisuke134/life-manager/actions/runs/41630422469), we asked **ampersand-tutor-v0.1** to explain why 120 answers from 40 people are not the same as 120 independent people. The service completed the fictional educational request and returned 2,526 characters of output. We recorded completion, not a graded measure of teaching quality. The same run also completed another two-turn Ampersand collaboration session. **Ampersand Tutor is not Persimmon**: the former is a publicly callable teaching variant; the latter is the separately described model of simulated users. We did not call Persimmon.

## The first call: a conflict worth mentioning

On November 3, 2026, we made an authenticated request to Ampersand v0.1. An API, short for application programming interface, is the doorway software uses to talk to another service. Instead of typing into a chat window, our program sent the fictional scenario to humans&'s servers and read the response.

The [execution record for the first run](https://github.com/Daisuke134/life-manager/actions/runs/41618299490) records a completed request and 359 characters of assistant output. We used the documented model identifier, `ampersand-v0.1`, after checking that our account could access it. The credential stayed in a protected repository secret.

We created a session with no external tools. There was no calendar for the model to change and no real Sam to contact. It could only answer the collaboration question we supplied. That makes the scene safely fictional while leaving the service interaction real.

In our reading of the authenticated response, Ampersand recommended surfacing the already-known conflict and allowing the team to choose what to do. This is a paraphrase, rather than a reproduction of its output. The interesting detail is the division of responsibility: the assistant can make relevant information visible while the people retain the decision.

That sounds simple until the alternatives are made concrete. Silence lets the group proceed with an avoidable mistake. An automatic reschedule assumes authority the assistant has not been given. A long explanation could bury the relevant fact beneath advice nobody requested. Our one response occupied a sensible middle ground for the scenario as presented.

It remains one response. We did not measure whether a real team would find it useful, whether Sam would feel represented fairly, or how the system would behave after weeks of conflicting messages. Those are questions the example helps formulate, rather than questions it settles.

## The second call: the facts move

We then ran a separate, two-turn session on the same day. In that session, the scheduling story changed from a definite conflict to a possibility: Friday might work, but it was not confirmed. The [second execution record](https://github.com/Daisuke134/life-manager/actions/runs/41619141514) shows a first response of 546 characters and a follow-up response of 465 characters.

The follow-up went into the same session. Readback from the provider returned four saved conversation items and two completed turns. We therefore verified that the integration could continue a conversation, submit updated information and retrieve its saved history.

Character counts cannot tell us whether the model handled the revision well. The public logs preserve completion metadata, without the answer bodies needed to judge its language. We cannot report that it withdrew its earlier advice, asked Sam for clarification or selected exactly the right tone. Each would be an appealing story detail, and each would require evidence we are not publishing here.

The contrast still gives the exercise its purpose. “Cannot attend” and “might attend” call for different reasoning. Any assistant used in an ongoing conversation needs a way to receive that correction. Our second run established the working conversation machinery; judging the correction itself would require reviewing the actual content under an appropriate evaluation procedure.

It also separates two things often compressed into the word “memory.” A service can save the messages in a session. Whether the model uses those messages appropriately is a behavioral question. Four saved items prove the former, while leaving the latter open.

## Why a quiet assistant needs a visible completion signal

The [integration guide](https://ampersand.humansand.ai/docs/GUIDES.html) makes silence a meaningful possibility. In a group chat, the assistant may have nothing useful to add. Software surrounding it must therefore be able to distinguish a finished turn from a failed connection.

We consumed the service's event stream until it reported `agent.session.idle`: the session had stopped working on that turn. Think of it as a light showing that the microphone has been put down. It says nothing about whether the meeting was scheduled successfully.

This distinction affects the experience of using an assistant. If an application treats every quiet turn as a technical failure, it may keep retrying until the model finally interrupts. The surrounding software would then punish the very restraint the product is supposed to allow.

Our runs produced text, so they do not demonstrate a successful silent intervention. They did make the completion boundary explicit. The same boundary lets a developer keep “the model finished” separate from “the people achieved their goal.”

For a founder considering an AI in team chat, that is a practical design issue. A product needs both a place for the assistant to speak and a way for the conversation to continue comfortably without it.

## What one scheduling story can teach

A benchmark is a defined test with a scoring procedure, intended to make performance measurable and, where permitted, comparable. Our fictional provider demonstration was ordinary API use, rather than a comparative benchmark. [Ampersand's terms](https://ampersand.humansand.ai/terms) restrict competitive benchmarking and competing-model training; access to the service should not be mistaken for permission to perform either.

The strongest observation we can make is local to this story. In the first run, the response supported raising relevant information without taking control of the decision. In the second, the service completed a continued conversation after we changed the information. We have no basis here for ranking its social intelligence or claiming improved outcomes for real groups.

For our Manager research, the more useful lesson concerns what to observe next. We would want to know whether an assistant notices a correction, how confidently it treats uncertain facts, and whether the people involved retain room to disagree. Counting completed answers would miss those qualities.

Sam's Friday is deliberately mundane. That is what gives it force. People revise plans, soften refusals and leave things unresolved. A collaborator has to make room for those changes. The next useful evidence would be the words it chooses when a once-certain fact becomes uncertain, and what the team does after hearing them.


---

**Continue reading:** [What happens when an AI pretends to be 48 different people?](https://aniccaai.com/blog/manager-artificial-societies-jordan-pilot-en)
