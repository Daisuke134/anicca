"""Re-execute pinned Zhang & Kool Step7 cells; no clinical or online claims.

The authors' scientific cell source is executed unchanged after hash verification.
Only display-only cells and their two filesystem export cells are omitted. Outputs
are written under a separate directory so published parameter files stay intact.
Public reports contain aggregates, not participant-level records.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import numpy as np
import pandas as pd
from scipy import stats

EXECUTE_CELLS = [0, 1, 2, 3, 5, 7, 8, 9, 10, 11, 13, 15, 16, 17]
SCOPE = {
    'official_step7_two_state_fit': True,
    'clinical_trial': False,
    'model_comparison_100_masks': False,
    'online_prediction': False,
    'raw_to_clean_preprocessing_rerun': False,
    'hddm_or_all_paper_figures': False,
}
PINS = {
    'Step7_GLM-HMM.ipynb': '88dfa1259e05a55ab1708a13837b67e2032f236e871d490cc75da1aaa08e56f8',
    'self_state.csv': '5493e06ecc89f4e9561ef934ad76c6c3c7fc19842a685ae164c7b2f7245aef56',
    'trans_prob.csv': 'dee8a51ae63a6f779e2df8d7f54147dadefbf929ee10621b91b26573706a4287',
}


def verify_file(path: Path, expected: str) -> int:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f'SHA256 mismatch: {path.name}')
    return len(raw)


def validate_input(data: pd.DataFrame) -> dict:
    if data['ID'].nunique() != 93 or len(data) != 55800:
        raise ValueError('Expected exactly 93 participants and 55,800 source rows')
    if not (data.groupby('ID', sort=False).size() == 600).all():
        raise ValueError('Expected 600 trials per participant')
    if not data['chose_dom'].isin([0, 1]).all():
        raise ValueError('Choices must be binary, without imputation by this wrapper')
    if not np.isfinite(data['coherence_dom']).all():
        raise ValueError('Stimulus evidence must be finite')
    absent = ~data['response'].isin(['p', 'q'])
    return {
        'participants': int(data['ID'].nunique()),
        'trials': len(data),
        'trials_per_participant': 600,
        'missing_keypress_trials': int(absent.sum()),
        'missing_keypress_choice_encoding': {str(k): int(v) for k, v in data.loc[absent, 'chose_dom'].value_counts().items()},
    }


def transition_summary(table: pd.DataFrame) -> dict:
    result = {}
    for state in ['on', 'off']:
        p = table[f'P_{state}_{state}'].to_numpy(dtype=float)
        if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
            raise ValueError('Invalid transition probability')
        absorbing = int((p == 1).sum())
        result[f'{state}_stay_probability_mean'] = float(p.mean())
        result[f'{state}_absorbing_states'] = absorbing
        result[f'{state}_expected_dwell_mean_trials'] = None if absorbing else float(np.mean(1 / (1 - p)))
        result[f'{state}_expected_dwell_median_trials'] = None if absorbing else float(np.median(1 / (1 - p)))
        result[f'{state}_dwell_from_mean_transition_trials'] = None if p.mean() == 1 else float(1 / (1 - p.mean()))
    return result


def run(data_root: Path, out: Path) -> dict:
    data_root, out = data_root.resolve(), out.resolve()
    if data_root == out:
        raise ValueError('Output must not overwrite the original data directory')
    out.mkdir(parents=True, exist_ok=True)
    verified = {name: {'sha256': sha, 'bytes': verify_file(data_root / name, sha)} for name, sha in PINS.items()}
    original = pd.read_csv(data_root / 'self_state.csv', index_col=0)
    counts = validate_input(original)
    notebook = json.loads((data_root / 'Step7_GLM-HMM.ipynb').read_text())
    import matplotlib
    matplotlib.use('Agg')
    import ssm
    fits = []
    original_fit = ssm.HMM.fit

    def measured_fit(self, *args, **kwargs):
        started = time.perf_counter()
        result = original_fit(self, *args, **kwargs)
        values = np.asarray(result, dtype=float)
        fits.append({'iterations_returned': len(values), 'finite': bool(np.isfinite(values).all()),
                     'final_log_likelihood': float(values[-1]),
                     'minimum_ll_step': float(np.diff(values).min()) if len(values) > 1 else None,
                     'seconds': time.perf_counter() - started})
        print(f'FIT {len(fits)}/93 completed; iterations={len(values)}', file=progress, flush=True)
        return result

    previous = Path.cwd()
    started = time.perf_counter()
    namespace = {'__name__': '__official_notebook__'}
    progress = __import__('sys').stdout
    try:
        os.chdir(data_root)
        ssm.HMM.fit = measured_fit  # Measurement only: same arguments and return value.
        with (out / 'official_execution.private.log').open('w') as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                for index in EXECUTE_CELLS:
                    code = ''.join(notebook['cells'][index]['source'])
                    exec(compile(code, f'official-cell-{index}', 'exec'), namespace)
    finally:
        ssm.HMM.fit = original_fit
        os.chdir(previous)
    elapsed = time.perf_counter() - started
    table = namespace['trans_prob_weight']
    states = namespace['data_states']
    if len(table) != 93 or len(states) != 55800 or len(fits) != 93:
        raise RuntimeError('Partial fit cannot be reported as complete')
    if not all(item['finite'] for item in fits):
        raise RuntimeError('Non-finite fitted likelihood')
    if not np.isfinite(table.drop(columns='ID').to_numpy()).all():
        raise RuntimeError('Non-finite parameter')
    if not states['ON_cont'].between(0, 1).all():
        raise RuntimeError('Invalid posterior')
    table.to_csv(out / 'rerun_trans_prob.private.csv', index=False)
    states.to_csv(out / 'rerun_model_states.private.csv', index=False)
    author = pd.read_csv(data_root / 'trans_prob.csv', index_col=0)
    left = table.set_index('ID').sort_index()
    right = author.set_index('ID').sort_index()
    if not left.index.equals(right.index):
        raise RuntimeError('Author/rerun identity mismatch')
    diff = (left - right).abs()
    test = stats.ttest_rel(table['stim_off'], table['stim_on'])
    summary = {
        'status': 'OFFICIAL_STEP7_93_PARTICIPANT_REFIT_COMPLETED',
        'scope': SCOPE,
        'source_paper': 'https://doi.org/10.1038/s44271-026-00424-9',
        'source_project': 'https://osf.io/jbp6h/',
        'source_files': verified,
        'input': counts,
        'seed': 0,
        'maximum_em_iterations': 200,
        'tolerance': 0.0001,
        'executed_cells': EXECUTE_CELLS,
        'ssm_commit': subprocess.check_output(['git', '-C', str(data_root / 'ssm'), 'rev-parse', 'HEAD'], text=True).strip(),
        'python': platform.python_version(),
        'packages': {name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'pandas', 'autograd', 'ssm']},
        'fit_seconds': elapsed,
        'fits_completed': len(fits),
        'all_likelihoods_finite': all(x['finite'] for x in fits),
        'fits_at_iteration_limit': sum(x['iterations_returned'] >= 200 for x in fits),
        'fits_with_ll_decrease_over_1e_6': sum(x['minimum_ll_step'] is not None and x['minimum_ll_step'] < -1e-6 for x in fits),
        'rerun_transitions': transition_summary(table),
        'author_published_transitions': transition_summary(author),
        'parameter_abs_difference_vs_author': {'maximum': float(diff.to_numpy().max()), 'mean': float(diff.to_numpy().mean()), 'per_column_max': {k: float(v) for k, v in diff.max().items()}},
        'stimulus_weight_paired_t': {'statistic': float(test.statistic), 'pvalue': float(test.pvalue), 'n': 93},
        'on_task_hard_fraction': float((states['state_model'] == 'ON').mean()),
        'on_task_posterior_mean': float(states['ON_cont'].mean()),
        'limitations': [
            'Official cleaned input reused; original raw-to-clean pipeline not rerun.',
            'Official notebook includes omitted keypress trials according to its preexisting chose_dom encoding; no mask added in the faithful run.',
            'Expected states are retrospective smoothed posteriors using future responses, not online filtering.',
            'Original notebook cell source unchanged; display-only and original export cells omitted; same fit call wrapped only for timing/diagnostics.',
            'Dependencies pinned here, not a verified exact historical authors environment.',
            '100-mask crossvalidation, all state-count comparisons, HDDM and all figures not reproduced.',
            'OSF node license metadata unspecified; raw records and author notebook not redistributed in repository.',
            'Attention-state fit does not demonstrate reduced rumination, clinical benefit or a general-purpose behavioral foundation model.'
        ],
        'clinical_rnt_effect': None,
    }
    (out / 'P07-2_ZHANG_KOOL_STEP7_RESULTS.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    (out / 'fit_diagnostics.private.json').write_text(json.dumps(fits, indent=2) + '\n')
    print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.data_root, args.out)
