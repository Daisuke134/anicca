# We Asked AI to Be 48 Different People. It Gave the Same Answer 48 Times.

**Anicca Research | November 3, 2026**

We asked a small AI model to answer a survey as 48 different respondents, and it chose the same top option every time. All 48 answers passed the format check; the human responses they were meant to imitate told a different story.

Picture a stack of questionnaires on a desk. Half use one description of a public-spending issue, half another. The response boxes are identical, but a few changed words can bring different associations to mind. In our November 3 pilot, the human reference answers shifted between the two versions. The AI's answers stayed fixed at the top of the scale.

That is an unusually clear failure to encounter while learning a research method. A program can accept every answer it receives, finish without a parsing error, and still produce a synthetic population that misses the phenomenon under investigation.

![Human-reference mean response changes from 0.646 to 0.792 across two wordings, while the local Qwen model returns 1.000 in both conditions.](https://aniccaai.com/blog/manager/media/0d5e7eb47e219484459f9a4cba18036b9c6b5dfe396c5c0e0c677797c1db480d.png)


## Why build an artificial society?

Before a company changes a product, it may want to know how customers will react. Before a researcher trusts a questionnaire, they may want to know whether its wording changes the answers. Asking real people takes time and resources. A convincing simulation promises a way to explore possibilities before committing to a larger study.

Artificial Societies is a company working on that problem: predicting how individuals and groups respond in context. Its proprietary model, [Rothko](https://societies.ai/rothko), is designed to produce behavioral decisions. The company describes training it on human behavioral data to represent differences that ordinary assistant models can flatten.

The appeal is easy to understand. A founder could rehearse a product decision; a researcher could examine a candidate survey design. But the promise depends on an awkward requirement. The simulated people need to reproduce relevant features of real responses, including disagreement, inconsistency and sensitivity to context.

A model that always supplies the reasonable-sounding answer might be pleasant company and a poor substitute for a population. Human research depends on differences between people. If a simulation smooths those differences away, it can erase the very thing a study was designed to measure.

We wanted to learn how to check that. We did not get access to Rothko or infer anything from running its proprietary model. Instead, we used Artificial Societies' public research framework with a small model we could run locally.

## Wording is part of the instrument

Imagine two versions of a hypothetical referendum question. One asks about paying for a public service; the other emphasizes the tax required to fund it. Even when both refer to the same proposal, they direct attention toward different aspects of the decision. This is an illustration of the measurement problem, rather than the actual wording from our pilot.

A survey question is an instrument, much like a thermometer. If changing its label changes the reading, a researcher needs to understand that effect. There may be reasons for the difference, and the task is to measure it accurately before using the answers as evidence.

Our pilot used an existing study by Jordan and collaborators involving alternative wording about social spending. We treated the political subject as a neutral measurement setting. We did not send messages to voters, advocate a policy position or use the results to target persuasion.

The human answers came from the [Jordan et al. replication archive at Harvard Dataverse](https://doi.org/10.7910/DVN/SH0F25), released under CC BY. A replication archive preserves material so other researchers can examine or repeat an analysis with attribution. These were previously collected survey responses. We did not conduct a new survey of 1,488 people.

That distinction is central to the experiment. The human observations gave us something outside the model against which to check its predictions. Without them, we would have had 48 computer-generated answers and little basis for deciding whether they resembled anyone.

## A test for something beyond plausible prose

The [Artificial Societies Benchmark](https://github.com/artificial-societies/artificial-societies-benchmark) supplies code, task definitions and scoring procedures for evaluating simulated respondents. A benchmark is a structured test: specify the task, collect outputs and compare them using agreed rules. Here, the question is whether synthetic answers behave like useful human measurements.

That goes beyond whether an answer sounds believable. A model might reproduce the overall popularity of an option while missing which people choose it. It might match one question and contradict itself on a related one. It might represent average opinions adequately and still fail to predict a shift caused by wording.

Those are different properties. Our pilot focused on the last: could the local model reproduce the difference between two wording conditions? You can think of it as checking whether a simulated thermometer moves when the real one does.

We first worked through the public research machinery. The recorded test suite finished with **68 tests passed and 7 skipped**. The skipped tests involved unavailable original human source files or evaluation candidates that had not been prepared. We also rebuilt the published scorecard's **7,128 cells** from its released component outputs.

That reconstruction helped us understand how results were assembled. It did not involve calling all the models whose results appeared there. Rebuilding a published table from existing measurements is different from collecting those measurements again. Our new model outputs came from the much smaller exercise that followed.

## Forty-eight turns at being someone else

We retrieved the licensed Jordan archive and used the official data-preparation code without changing its wording-preparation function. It produced **1,488 human profiles and 1,488 observations** for the prepared task.

From the benchmark split, we selected **24 participants per wording condition**, using a fixed random seed so the selection was repeatable. Each selected profile was used to construct a respondent prompt. The model's job was to provide that respondent's answer to the assigned question.

The model was **Qwen2.5:1.5b**, running locally through Ollama. The 1.5b label refers to roughly 1.5 billion learned parameters, the numerical settings adjusted during model training. This was a specific small-model configuration, rather than a stand-in for all AI models or for Rothko.

We used the benchmark's official prompt-building and answer-parsing functions. The parser checks whether a response can be read as one of the permitted answers. All 48 passed. That matters because invalid responses can otherwise make a comparison hard to interpret: a refusal or an unreadable sentence is not the same thing as a chosen survey option.

Here, there was no such ambiguity in the outputs. The local model selected the top response option for every profile, under both wordings. We had asked for differences between respondents and received a flat line.

## The human line moved

The scoring procedure placed responses on an ordered scale of **0, 0.5 and 1**. These numbers express the response categories for this task; they are not probabilities, judgments of moral correctness or predictions of a vote.

| Mean response on the 0–1 scale | Matched human observations | Local Qwen pilot |
| --- | ---: | ---: |
| Wording A | 0.6458 | 1.0000 |
| Wording B | 0.7917 | 1.0000 |
| B minus A | **+0.1458** | **0.0000** |

For the selected human observations, the second wording's mean was about 0.146 higher. For the model, subtracting one perfect-looking column of ones from another produced zero. Its absolute error in the difference between conditions was therefore about 0.146 on this scale.

The important failure was visible in the comparison. A column full of valid answers might look reassuring in an execution log. Against the human reference, it showed that this configuration missed the measured wording difference and produced none of the observed answer variation.

The numbers describe our selected 48-observation pilot. They are not an estimate from all 1,488 prepared respondents, an official leaderboard entry or a general conclusion about Qwen across every setting. A different model, prompt configuration or sample would require its own experiment.

We also cannot tell from these outputs why the model collapsed to one option. Assistant training, model capacity and inference settings are possible avenues to investigate. Selecting a cause without testing it would turn an informative failure into an unsupported story.

## Why a convincing answer can be the wrong product

A conversational assistant is often asked to give one useful response. A population simulator has a different job: preserve the patterns that matter across many responses. These aims can pull in different directions.

Suppose a product researcher wants to know whether changing a description affects reactions. A simulation that always gives the most favorable answer offers apparent certainty. Yet that certainty carries almost no information about the change. Both versions look equally successful because the simulator has run out of variation.

Our pilot makes that problem tangible without proving it is universal. It shows why checking the distribution of answers matters. The distribution is simply how responses are spread across the available options. If all the weight sits on one option, the researcher should notice before turning the output into a decision.

The next check depends on the question being asked. For overall demand, one would examine response frequencies. For repeated observations of the same person, consistency may matter. For wording experiments, the difference between conditions deserves its own score. One headline number cannot answer all three questions.

For our Manager research, this changes the order of attention. We need to establish that the model's predictions contain meaningful variation and track independent human evidence before asking whether those predictions improve decisions. A successful software run establishes only that we can collect and score outputs.

## What the identical answers gave us

The central lesson came from a mismatch a reader can see without understanding the code. The people in the reference data answered differently across the two wordings. Our local AI respondents all chose the same option.

That result says nothing about the performance of the proprietary Rothko model, which we did not run. It does show the value of trying a public validation method with real human reference data. The framework gave an ordinary completion log a scientific question to answer.

The questionnaire stack is a useful image to keep in mind. Forty-eight neatly filled forms can resemble a completed study. Before trusting the apparent crowd behind them, look at whether anyone in it ever answers differently, and whether those differences resemble the people the simulation is supposed to represent.


---

**Continue reading:** [Why a test set might have already met the people in its training data](https://aniccaai.com/blog/manager-behavior-data-audit-en)
