# Academic Introduction Humanizer — test case

## Input

Edit this introduction for a public-health manuscript. Preserve exactly: “42% of
participants reported delayed care,” “[Citation A],” the phrase “may contribute,”
and the stated gap that rural clinic access has not been studied in this county.
Do not add findings, causes, citations, or methods. Target: 170 words.

## Expected checks

- Contains the supplied 42% figure, citation placeholder, research gap, and uncertainty marker.
- Does not add a source, causal explanation, result, method, or claim of novelty.
- Flags any unsupported transition as `[AUTHOR CHECK]`.
