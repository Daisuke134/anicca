# Academic Methods Clarity Editor — verified demonstration

## Concrete input

```text
Field: public health
Target reader: journal reviewer
Word limit: 150 words

Methods excerpt:
We conducted an online survey of 84 adults from 3 May to 17 May 2025. People
were recruited through a community newsletter. Participants completed a 12-item
sleep questionnaire and reported their age. Participants who did not answer all
sleep questions were excluded before the primary analysis. We summarized the
data using descriptive statistics. The questionnaire was administered after
consent was obtained. The study was approved by the university committee.

Must remain exact: 84 adults; 3–17 May 2025; community newsletter; 12-item
sleep questionnaire; age; exclusion for incomplete sleep questions; descriptive
statistics. Do not add the committee name, approval number, location, software,
or results.
```

## Actual output

```text
Method map
| Element | Supplied detail |
| --- | --- |
| Design | Online survey |
| Participants | 84 adults |
| Recruitment | Community newsletter |
| Collection period | 3–17 May 2025 |
| Measures | 12-item sleep questionnaire; age |
| Exclusion | Incomplete sleep-question responses before primary analysis |
| Analysis | Descriptive statistics |
| Ethics statement | University committee approval; consent obtained |

Constraints and author checks
| Item | Treatment |
| --- | --- |
| All listed counts, dates, measures, exclusion, and analysis wording | preserved |
| Committee name and approval number | [AUTHOR CHECK] not supplied |
| Location and software | [AUTHOR CHECK] not supplied; not added |
| Order of consent and questionnaire | reordered to match the supplied statement that consent came first |

Revised methods passage
An online survey was conducted with 84 adults from 3 May to 17 May 2025.
Participants were recruited through a community newsletter. After consent was
obtained, participants completed a 12-item sleep questionnaire and reported
their age. Participants with incomplete responses to the sleep questionnaire
were excluded before the primary analysis. The data were summarized using
descriptive statistics. The study was approved by the university committee.

Edit ledger
- Reordered the procedure so consent precedes questionnaire completion.
- Replaced “did not answer all sleep questions” with “incomplete responses to
  the sleep questionnaire” while preserving the same exclusion condition.
- Kept the supplied design, count, dates, recruitment route, measures,
  analysis type, and approval statement.
- Did not add a committee name, approval number, location, software, or results.
```

## Verification notes

1. The revised passage preserves every item explicitly marked “Must remain exact” in the input.
2. It uses only supplied information; committee name, approval number, location, software, and results remain absent.
3. The procedure order is clarified from the supplied statement that consent was obtained before the questionnaire.
4. The output follows the skill contract: method map, constraint table, revision, and edit ledger. It does not browse, validate the study, access records, or submit material anywhere.
