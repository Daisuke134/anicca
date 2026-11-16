"""CPU diagnostic on official BehaviorBench survey-response prompts.

Research evaluation only; source data is CC BY-NC-ND 4.0 and not redistributed.
This is row accuracy on one task, not the official aggregate leaderboard.
No task labels are exposed to the model. Invalid generations count as wrong.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import time

REVISION = 'ec382c701589da2f24bf697dd1b3bb9f7bd62a35'
DATA_FILE = 'big_five/surv_resp_pred/test.jsonl'
SOURCE_SHA256 = '580b690b5bf7e69b58f1606cb0ee125a7d78a6308bce050fa2cb84eb1c289506'


def parse_answer(text):
    match = re.fullmatch(r'\s*\[([1-5])\]\s*', text)
    return int(match[1]) if match else None


def select_indices(total, n, seed):
    if not 0 < n < total:
        raise ValueError('Need 0 < n < total for complementary prior calibration')
    selected = sorted(random.Random(seed).sample(range(total), n))
    chosen = set(selected)
    return selected, [i for i in range(total) if i not in chosen]


def summarize(targets, predictions):
    if not targets or len(targets) != len(predictions):
        raise ValueError('Nonempty, aligned targets/predictions required')
    correct = sum(a == b for a, b in zip(targets, predictions))
    return {'n': len(targets), 'correct': correct, 'accuracy': correct / len(targets),
            'invalid': sum(p is None for p in predictions)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--data', help='Optional local copy of pinned official JSONL')
    args = ap.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from huggingface_hub import hf_hub_download
    source = args.data or hf_hub_download('befm/BehaviorBench', DATA_FILE,
                                         repo_type='dataset', revision=REVISION)
    raw = Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('BehaviorBench source hash differs from pinned revision')
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    selected, complement = select_indices(len(rows), args.n, args.seed)
    labels = [parse_answer(r['assistant']) for r in rows]
    if any(y is None for y in labels):
        raise ValueError('Unexpected official label format')
    # Estimate the marginal from non-evaluated rows, never from scored targets.
    counts = Counter(labels[i] for i in complement)
    prior = min(counts, key=lambda label: (-counts[label], label))
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.float32)
    model.eval()
    predictions, records = [], []
    start = time.monotonic()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for i in selected:
        row = rows[i]
        messages = [{'role': role, 'content': row[role]} for role in ('system', 'user')]
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        enc = tok(prompt, return_tensors='pt', add_special_tokens=False)
        with torch.no_grad():
            generated = model.generate(**enc, do_sample=False, max_new_tokens=8,
                                       pad_token_id=tok.eos_token_id)
        answer = tok.decode(generated[0, enc['input_ids'].shape[1]:], skip_special_tokens=True)
        prediction = parse_answer(answer)
        predictions.append(prediction)
        records.append({'row_index': i, 'prediction': prediction, 'target': labels[i],
                        'generated': answer, 'prompt_tokens': enc['input_ids'].shape[1]})
        result = {
            'model': args.model, 'dataset': 'befm/BehaviorBench', 'revision': REVISION,
            'file': DATA_FILE, 'source_sha256': hashlib.sha256(raw).hexdigest(),
            'protocol': {'task': 'surv_resp_pred', 'metric': 'row accuracy (not grouped leaderboard)',
                         'seed': args.seed, 'requested_n': args.n, 'dtype': 'float32',
                         'decoding': 'greedy, max_new_tokens=8, strict bracket parsing',
                         'subset': 'Python random.Random(seed).sample, sorted indices'},
            'complete': len(records) == args.n,
            'metrics': summarize([r['target'] for r in records], predictions),
            'prior_complement_marginal': {
                'calibration_n': len(complement), 'prediction': prior,
                **summarize([r['target'] for r in records], [prior] * len(records))},
            'prior_constant_3': summarize([r['target'] for r in records], [3] * len(records)),
            'historical_references': {'befm_accuracy': 0.5556, 'prior_accuracy': 0.6111,
                'scope': 'MaMe-Re 18 non-tied pairs; NOT BehaviorBench, not comparable'},
            'elapsed_sec': time.monotonic() - start, 'records': records,
        }
        temporary = out.with_suffix('.tmp')
        temporary.write_text(json.dumps(result, indent=2) + '\n')
        temporary.replace(out)
        if len(records) % 10 == 0:
            print(f'{len(records)}/{args.n}: {result["metrics"]}', flush=True)
    print(json.dumps(result['metrics']), flush=True)


if __name__ == '__main__':
    main()
