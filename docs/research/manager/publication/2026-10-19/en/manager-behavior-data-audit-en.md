# Our AI Test Had Already Met 25 of the “New” People

**Anicca Research | November 3, 2026**

In our offline demonstration, 25 of the 26 people in an AI test also appeared in its training data. The entire population was fictional, but the mistake it exposed could make a real behavior-prediction system look more capable than it is.

Imagine giving an assistant the early pages of someone's diary, then testing it on a later entry from the same notebook. It might recognize familiar habits, recurring worries or a distinctive way of answering. That could be useful if the task is to understand this particular person. It tells you much less about how the assistant will handle a stranger whose diary it has never seen.

Our example used 40 fictional people, each with three answers. When we shuffled the answers into separate training and test groups, most of the supposedly new people were already familiar. Keeping each person's answers together changed the test completely, without adding a single row of data.

![Forty fictional people: a random row-level split leaks 25 people into both training and test; a person-level split keeps all 10 test people unseen.](https://aniccaai.com/blog/manager/media/93dfeca994994a32e7df1bf3fa21cc9415a7220c019c03c922ba1dfd807aa844.png)


## The appeal of a model that understands people

Our Manager research asks how predictions about human responses could inform decisions. The attraction is understandable: an assistant that anticipates when a suggestion will help, when someone needs more information or when a plan is likely to be rejected could support better choices.

There are already companies pursuing related pieces of this problem. [Artificial Societies](https://societies.ai/rothko) is developing a proprietary model to predict individual and collective behavior. [humans& describes Persimmon](https://persimmon.humansand.ai/blog/persimmon.html) as a model for simulating users across conversations. These are different projects, with their own methods and evidence, rather than interchangeable versions of a universal predictor.

For us, their existence makes a basic question more urgent. If we build a model that appears to understand people, what would persuade us that it can handle someone it has never encountered?

One answer is to give it a test. But a test inherits the assumptions used to assemble it. If the same person appears on both sides, the experiment may be asking about recognition and familiarity while the headline claims success with strangers.

Before training a next Manager model, we wanted to make that mismatch visible. We built an offline teaching example around fictional records. Its purpose was to inspect how we separate learning material from evaluation material, rather than to demonstrate any ability to predict real human behavior.

## Training is practice; testing is the closed-book part

During training, a model is adjusted using examples. During testing, we check predictions against answers reserved for evaluation. The point of keeping material aside is to learn something about how the model behaves beyond the examples used to teach it.

The school-exam analogy is helpful, with one complication. A pupil who practices on one set of questions and takes an exam on different questions may still have seen the same underlying story. Changing the question number does not necessarily make the material unfamiliar.

Human-response datasets have this complication built in. One person can supply many records: several survey answers, repeated diary entries, visits to a product or decisions made over time. A spreadsheet turns each observation into a row. The row looks separate on screen even when it belongs to the same life.

In our demonstration, **40 fictional people supplied three answers apiece, making 120 rows**. The distinction between people and rows is the whole experiment. We did not recruit participants, copy anyone's diary or collect private behavioral data for it.

We first divided the rows at random, using a fixed seed so the procedure could be repeated. That is a familiar way to create training and test sets. It is also a way to scatter one person's three answers across both sets.

## The arithmetic of an accidental reunion

After dividing the answer rows, we counted distinct people on each side. The training group contained **39 people**. The test group contained **26**. Of those, **25 appeared in both**.

The numbers add up because these are counts of unique people within each group, not separate populations. Twenty-five familiar people, plus fourteen seen only in training and one seen only in testing, account for all forty.

We then divided by person. Each fictional person's three answers stayed together. This produced **30 people in training and 10 in testing**, with **zero people shared** between the groups.

| How we divided the same 120 rows | People in training | People in testing | People on both sides |
| --- | ---: | ---: | ---: |
| Shuffle individual answers | 39 | 26 | **25** |
| Keep each person's answers together | 30 | 10 | **0** |

We did not train a predictive model and observe an inflated accuracy score in this exercise. The result is the overlap itself. It exposes a route by which a future performance claim could become misleading, before we spend resources producing that claim.

The headline's “new” people belong to this deliberately constructed example. The 25 overlaps are not evidence that a real deployed model memorized users, or that any named company's published results contain the same mistake.

## When familiarity becomes data leakage

Researchers call it **data leakage** when information crosses a boundary that the evaluation depends on keeping closed. For a claim about unfamiliar people, allowing the same people into training and testing weakens that boundary. The model may benefit from prior exposure even if the exact test answer was held aside.

Returning to the diary, a model might learn that its writer repeatedly dislikes early meetings. Predicting another answer from that writer could then be easier than predicting an unfamiliar person's preference. The resulting score mixes what the system knows about a recurring individual with what it has learned that transfers to others.

Keeping people separate prevents that particular shortcut. It does not automatically remove every shortcut. Two records might contain near-duplicate wording; an input might accidentally include the answer; a study identifier might reveal which outcome is likely. Each deserves attention when it can affect the claim being tested.

There is also a perfectly reasonable task in which familiarity is the point. A personal assistant should be able to learn from its user's earlier answers. Testing later behavior from a known person can be appropriate, provided the time order is respected and the claim says what was measured.

The failure occurs when the test asks one question and the article answers another. A system evaluated on familiar users should not be described as validated on unseen people. A careful split makes the question explicit before the score arrives.

## Four kinds of unfamiliar

For the next Manager model, “held out” needs a noun after it. Holding something out means reserving it from training and development so it can provide a more independent check. Different reservations support different claims.

- **People:** Can the model handle someone whose records it has never used?
- **Times:** Can it predict a later period using only information available beforehand?
- **Studies:** Does what it learned survive a new experiment or questionnaire?
- **Projects:** Does it remain useful in a different working context with different goals?

These tests can be designed separately or combined, depending on the intended use. Reserving whole people cannot by itself establish performance on a new type of study. Preserving chronological order cannot by itself establish that a model transfers to another project.

Time is particularly easy to mishandle in personal records. An entry written after an event may explain why the person acted as they did. That explanation is useful historical evidence, yet it was unavailable before the action. Feeding it into a prediction of the earlier event gives the model knowledge the deployed assistant would not have had.

Our teaching example included checks of future-information leakage alongside person overlap. The point is to reconstruct the assistant's actual position at the moment of prediction: what could it know then, and which answer was still in the future?

## A downloadable file has its own conditions

There is a second boundary to inspect before training: permission to use the material. A dataset can be easy to download while carrying restrictions that matter to a commercial project.

For example, the [SimBench dataset card](https://huggingface.co/datasets/pitehu/SimBench) lists **CC BY-NC-SA 4.0**. In plain terms, that license includes attribution, noncommercial and share-alike conditions. A public download should therefore not be treated as unrestricted commercial training material.

Source data, research code and model-service outputs can come with separate terms. The [Artificial Societies benchmark repository](https://github.com/artificial-societies/artificial-societies-benchmark) distinguishes the licenses for its code, released results and underlying study material. An API, the interface through which software calls a remote model, introduces another set of conditions. [Ampersand's terms](https://ampersand.humansand.ai/terms), for instance, restrict competitive benchmarking and competing-model training.

That separation prevents a common chain of assumptions: the code is open, so its input data must be unrestricted; the API returned an answer, so that answer must be available to train a competing model. Neither follows from access alone.

We also need to know which exact file was used. A SHA-256 hash works like a fingerprint for file contents, allowing another researcher to check whether the bytes match. It helps identify the evidence. It cannot tell us whether the people consented, the answers are accurate or the intended use is permitted.

## What the small audit changed

Our offline demonstration checked row identity, group holdouts, future-information leakage, source provenance and allowed-use metadata. Its **11 unit tests passed**. Those are software checks on a synthetic example, rather than validation of a model's predictions about real people.

The practical gain is an earlier, cheaper way to catch a false claim. Before collecting a performance score, we can inspect whether the evaluation actually reserves the people, periods and settings named in the research question. Before treating a dataset as training material, we can record its source and conditions of use.

A stricter test may yield a worse score. It can also give that score a more useful meaning. For Manager, a result on genuinely held-out people would address a question that a shuffled pile of their answers cannot settle.

The diary remains the simplest way to remember the distinction. Reading more pages from a familiar notebook may help an assistant understand its owner. To find out how it handles a stranger, eventually we have to give it a notebook it has never opened.


---

**Continue reading:** [A hands-on test of AI collaboration with humans& Ampersand](https://aniccaai.com/blog/manager-ampersand-api-firsthand-en)
