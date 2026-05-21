#!/usr/bin/env python3
"""
NLP3 Assignment: Language Identification by Byte Language Model
Student ID: 2411218
Name: daisuke narita
"""

import collections
import os
import sys
from typing import Any, Dict, List, Tuple
import numpy as np

# Download dataset if not exists
def download_dataset():
    """Download the languages dataset from Google Drive"""
    import subprocess
    import zipfile
    
    if os.path.exists('languages'):
        print("Dataset already exists. Skipping download.")
        return
    
    print("Downloading dataset...")
    try:
        # Try using gdown if available
        import gdown
        file_id = '12CDdzmMuEInj0bqhMjlGLsONxZm4Tv6_'
        output = 'languages.zip'
        gdown.download(f'https://drive.google.com/uc?id={file_id}', output, quiet=False)
        
        # Unzip
        with zipfile.ZipFile(output, 'r') as zip_ref:
            zip_ref.extractall('.')
        
        # Remove zip file
        os.remove(output)
        print("Dataset downloaded successfully.")
    except ImportError:
        print("gdown not installed. Please install it with: pip install gdown")
        print("Or manually download the dataset from Google Drive.")
        sys.exit(1)
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        sys.exit(1)

class ByteLM:
  """Byte language model.

  This is a very naive language model, in which byte-wise ngram probabilities
  are estimated by maximum-likelihood without considering an issue of
  out-of-vocabulary.

  You may want to tweak `__init__`, `initial_state` and `logprob` methods to
  alleviate the problem. However, do not change `perplexity` in order to check
  whether the model is implemented correctly. When changing part of the codes,
  please try to make it readable by using appropriate variable names or adding
  comments. Feel free to add additional methods, if necessary.

  Usages:
    ```python
    lm = ByteLM(path/to/train/data)
    perplexity, prob = lm.perplexity(path/to/test/data)
    ```
  """

  # DO NOT CHANGE BOS VALUE.
  # 0 will never appear in a text, thus, used it as a special symbol for
  # a beginning-of-sentence symbol, i.e., BOS.
  BOS: int = 0

  def __init__(self, filename: str, order: int=3) -> None:
    """Initializes `ByteLM`.

    You can change the arguments for this method if necessary, e.g., adding
    hyperparameters to this model.

    Args:
      filename: str, text file to train this language model.
      order: int, the n-gram order that should be greater than 1.
    """
    if order <= 1:
      raise ValueError(f'`order` must be greater than 1: {order}')
    self.order = order

    # Collect n-gram counts. The dictionary comprises a key of tuple of
    # integers, i.e., (n-1)-gram, and its associated value of 256-dimensonal
    # vector, i.e., counts for the following chars.
    ngram_counts = collections.defaultdict(lambda: np.zeros([256]))
    with open(filename, 'br') as f:
      for line in f:  # read as a byte string.
        buffer = [self.BOS] + list(line)  # `buffer` is now a list of integers.
        for n in range(1, self.order + 1):
          for i in range(len(buffer) - n + 1):
            ngram = buffer[i:i + n]
            ngram_counts[tuple(ngram[:-1])][ngram[-1]] += 1

    # Maximum likelihood estimate for language model with smoothing.
    # BUG FIX: The original code assigned -inf for zero probabilities, which causes
    # infinite perplexity when test data contains bytes not seen in training data.
    # Solution: Apply Laplace smoothing (add-one smoothing) to ensure all probabilities
    # are positive and sum to 1. This prevents -inf values in log probabilities.
    self.ngrams: Dict[Tuple[int], np.ndarray] = {}
    for context, counts in ngram_counts.items():
      # Laplace smoothing: add 1 to each count, then normalize
      # This ensures all 256 possible bytes have non-zero probability
      smoothed_counts = counts + 1.0
      probs = smoothed_counts / np.sum(smoothed_counts)
      # Now all probabilities are positive, so log probabilities are finite
      log_probs = np.log(probs)
      self.ngrams[context] = log_probs

  def initial_state(self) -> Any:
    """Returns an initial state for language model computation.

    You can change the code in this method, but keep the API, e.g, input
    arguments, so that `perplexity()` method works as expected.

    Returns:
      A state representation for log probabilities computation.
    """
    return []

  def logprob(self, state: Any, x: int) -> Tuple[np.ndarray, Any]:
    """Returns log probabilities for the current input byte.

    You can change the code in this method, but keep the API, e.g, input
    arguments, so that `perplexity()` method works as expected.

    It is a naive method for backing off to lower order n-grams, and may not be
    optimal for the lower perplexity.

    Args:
      state: A state to compute log probability.
      x: int, the current byte to compute `p(y | state, x)`.
    Returns:
      A pair of (log_probs, next_state) where `log_probs` is `np.ndarray` of log
      probabilities p(y | state, x) of all bytes y, and `next_state` is a new
      state for the next log probability computation with a new input. Note that
      `log_probs[y]` is equal to `log p(y | state, x)`,
      `log_probs.shape == (256,)`, `np.exp(log_probs) >= 0` and
      `np.sum(np.exp(log_probs)) == 1`.
    """
    # Backoff to lower order when necessary.
    # Note: With smoothing applied in __init__, we no longer need to handle -inf cases here
    state = (state + [x])[-self.order + 1:]
    for i in range(len(state), 0, -1):
       context = state[-i:]
       assert len(context) < self.order
       ret = self.ngrams.get(tuple(context), None)
       if ret is not None:
         return ret, context

    # Backoff to unigram.
    ret = self.ngrams.get((), None)
    assert ret is not None  # Unigram should always exist after __init__
    return ret, []

  def perplexity(self, filename: str) -> Tuple[float, float]:
    """Computes perplexity for text data.

    DO NOT CHANGE THE API OR CODE IN THIS METHOD.

    Args:
      filename: str, text file to compute perplexity.
    Returns:
      A pair (perplexity, prob) where `perplexity` is the perplexity computed
      for `filename`. `prob` is the cumulative product of probabilities of all
      the bytes in `filename` to verify that this language model is
      probabilistic or not. `prob` should be close to 1, otherwise, this is not
      a language model.
    """
    # Cumulative log_prob for perplexity computation.
    cumulative_log_prob = 0.0
    # Verify the distribution so that this language model is probabilistic.
    prob = 1.0
    # Total number of bytes.
    total_bytes = 0
    with open(filename, 'br') as f:
      for line in f:
        state = self.initial_state()
        prev_x = self.BOS
        for x in line:
          log_probs, state = self.logprob(state, prev_x)
          assert log_probs.size == 256, f"expected 256, got: {log_probs.size}"
          cumulative_log_prob += log_probs[x]

          probs = np.exp(log_probs)
          assert (probs >= 0).all(), "expected greater than or equal to zero."
          prob *= np.sum(probs)  # Sum of `probs` should be close to 1.

          prev_x = x

        total_bytes += len(line)

    return np.exp(-cumulative_log_prob / total_bytes), prob


def main():
    print("=" * 80)
    print("NLP3 Assignment: Language Identification by Byte Language Model")
    print("Student ID: 2411218")
    print("Name: daisuke narita")
    print("=" * 80)
    print()
    
    # Download dataset
    download_dataset()
    
    # Check if dataset exists
    if not os.path.exists('languages'):
        print("Error: Dataset not found. Please download it manually.")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("Part 1: Testing ByteLM with different language models (70 points)")
    print("=" * 80)
    print()
    
    # Train language models for English, Japanese and two variants of Chinese
    print("Training language models...")
    model_eng = ByteLM("languages/dev/eng.dev")
    model_jpn = ByteLM("languages/dev/jpn.dev")
    model_zho_simpl = ByteLM("languages/dev/zho_simpl.dev")
    model_zho_trad = ByteLM("languages/dev/zho_trad.dev")
    
    # Test on English test data
    print("Testing on English test data...")
    perp_eng, prob_eng = model_eng.perplexity("languages/devtest/eng.devtest")
    perp_jpn, prob_jpn = model_jpn.perplexity("languages/devtest/eng.devtest")
    perp_zho_simpl, prob_zho_simpl = model_zho_simpl.perplexity("languages/devtest/eng.devtest")
    perp_zho_trad, prob_zho_trad = model_zho_trad.perplexity("languages/devtest/eng.devtest")
    
    # Print out perplexity and the cumulative product of sum of probabilities
    print(f"English model: perplexity: {perp_eng} prob: {prob_eng}")
    print(f"Japanese model: perplexity: {perp_jpn} prob: {prob_jpn}")
    print(f"Simplified Chinese model: perplexity: {perp_zho_simpl} prob: {prob_zho_simpl}")
    print(f"Traditional Chinese model: perplexity: {perp_zho_trad} prob: {prob_zho_trad}")
    
    # Assertions to make sure the perplexities are finite
    assert np.isfinite(perp_eng), f"perp_eng is not finite: {perp_eng}"
    assert np.isfinite(perp_jpn), f"perp_jpn is not finite: {perp_jpn}"
    assert np.isfinite(perp_zho_simpl), f"perp_zho_simpl is not finite: {perp_zho_simpl}"
    assert np.isfinite(perp_zho_trad), f"perp_zho_trad is not finite: {perp_zho_trad}"
    
    # Assertions to make sure the cumulative product of probabilities are close to one
    assert np.allclose(prob_eng, 1.0), f"prob_eng is not close to 1.0: {prob_eng}"
    assert np.allclose(prob_jpn, 1.0), f"prob_jpn is not close to 1.0: {prob_jpn}"
    assert np.allclose(prob_zho_simpl, 1.0), f"prob_zho_simpl is not close to 1.0: {prob_zho_simpl}"
    assert np.allclose(prob_zho_trad, 1.0), f"prob_zho_trad is not close to 1.0: {prob_zho_trad}"
    
    print("\n✓ All assertions passed!")
    
    print("\n" + "=" * 80)
    print("Part 2: Identifying the language of languages/unk.test (30 points)")
    print("=" * 80)
    print()
    
    # Get all language files
    dev_dir = "languages/dev"
    language_files = [f for f in os.listdir(dev_dir) if f.endswith('.dev')]
    language_files.sort()
    
    print(f"Found {len(language_files)} language files in {dev_dir}")
    print("Training models for all languages and testing on unk.test...")
    print()
    
    # Train models for all languages and compute perplexity
    results = []
    for lang_file in language_files:
        lang_code = lang_file.replace('.dev', '')
        try:
            model = ByteLM(os.path.join(dev_dir, lang_file))
            perp, prob = model.perplexity("languages/unk.test")
            results.append((lang_code, perp, prob))
            print(f"{lang_code:15s}: perplexity = {perp:15.6f}, prob = {prob:.6f}")
        except Exception as e:
            print(f"Error processing {lang_code}: {e}")
            continue
    
    # Find the language with the lowest perplexity
    if results:
        results.sort(key=lambda x: x[1])  # Sort by perplexity
        best_lang, best_perp, best_prob = results[0]
        
        print("\n" + "-" * 80)
        print("Results Summary:")
        print("-" * 80)
        print(f"Best match (lowest perplexity): {best_lang}")
        print(f"Perplexity: {best_perp:.6f}")
        print(f"Probability: {best_prob:.6f}")
        print()
        print("Top 5 languages (lowest perplexity):")
        for i, (lang, perp, prob) in enumerate(results[:5], 1):
            print(f"  {i}. {lang:15s}: {perp:15.6f}")
    else:
        print("Error: No results obtained.")
        sys.exit(1)
    
    return {
        'part1': {
            'perp_eng': perp_eng,
            'perp_jpn': perp_jpn,
            'perp_zho_simpl': perp_zho_simpl,
            'perp_zho_trad': perp_zho_trad,
            'prob_eng': prob_eng,
            'prob_jpn': prob_jpn,
            'prob_zho_simpl': prob_zho_simpl,
            'prob_zho_trad': prob_zho_trad,
        },
        'part2': {
            'best_lang': best_lang,
            'best_perp': best_perp,
            'best_prob': best_prob,
            'all_results': results,
        }
    }


if __name__ == '__main__':
    results = main()

