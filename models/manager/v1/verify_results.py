"""Verify completed result artifacts against the frozen v0 protocol."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def main():
    results = HERE / 'results'
    training = read(results / 'train_log.json')
    assert training['n_train'] == 2000
    assert training['global_step'] == 125
    assert training['log_history']
    assert training['train_runtime_sec'] > 0
    baseline = read(HERE.parent / 'v0/results/eval_base.json')
    measured = read(results / 'eval_manager-v1.json')
    for field in ('n_train_full', 'n_test_full', 'n_eval', 'ate_eval',
                  'random_qini_mean', 'random_qini_p95'):
        assert measured[field] == baseline[field], field
    for arm in ('population_prior', 't_learner_logreg'):
        assert measured['arms'][arm] == baseline['arms'][arm], arm
    value = measured['arms']['manager-v1']
    lo, hi = value['qini_boot95']
    assert lo <= hi
    assert measured['gate_vs_random']['pass'] == (lo > baseline['random_qini_p95'])
    base = read(results / 'behaviorbench_base.json')
    v1 = read(results / 'behaviorbench_v1.json')
    for result in (base, v1):
        assert result['complete'] and result['metrics']['n'] == 100
        records = result['records']
        assert result['metrics']['correct'] == sum(r['prediction'] == r['target'] for r in records)
        assert result['metrics']['invalid'] == sum(r['prediction'] is None for r in records)
    for key in ('protocol', 'source_sha256', 'prior_complement_marginal', 'prior_constant_3'):
        assert base[key] == v1[key], key
    assert [(r['row_index'], r['target']) for r in base['records']] == [
        (r['row_index'], r['target']) for r in v1['records']]
    provenance = read(results / 'provenance.json')
    root = HERE.parents[2]
    for path, digest in provenance['files_sha256'].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path
    print('PASS: training complete; frozen uplift baselines exact; BehaviorBench aligned; source hashes intact')


if __name__ == '__main__':
    main()
