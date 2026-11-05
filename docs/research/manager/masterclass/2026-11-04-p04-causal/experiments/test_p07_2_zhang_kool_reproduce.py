"""Software tests only; artificial arrays below are not participant evidence."""
import importlib.util
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
import pytest

MODULE = Path(__file__).with_name('p07_2_zhang_kool_reproduce.py')


def load_module():
    assert MODULE.exists(), 'reproduction wrapper has not been implemented'
    spec = importlib.util.spec_from_file_location('zk_reproduce', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_source_accepts_exact_bytes(tmp_path):
    m = load_module()
    p = tmp_path / 'fixture.txt'
    p.write_bytes(b'provenance fixture')
    assert m.verify_file(p, hashlib.sha256(p.read_bytes()).hexdigest()) == len(p.read_bytes())


def test_source_mismatch_is_rejected(tmp_path):
    m = load_module()
    p = tmp_path / 'fixture.txt'
    p.write_bytes(b'changed fixture')
    with pytest.raises(ValueError, match='SHA256'):
        m.verify_file(p, '0' * 64)


def test_missing_file_is_not_success(tmp_path):
    m = load_module()
    with pytest.raises(FileNotFoundError):
        m.verify_file(tmp_path / 'absent', '0' * 64)


def test_official_cells_do_not_include_external_export():
    m = load_module()
    assert 9 in m.EXECUTE_CELLS
    assert 18 not in m.EXECUTE_CELLS
    assert 19 not in m.EXECUTE_CELLS
    assert m.EXECUTE_CELLS[:6] == [0, 1, 2, 3, 5, 7]


def test_dwell_summary_averages_individual_durations_not_mean_probability():
    m = load_module()
    table = pd.DataFrame({'P_on_on': [.8, .9], 'P_off_off': [.5, .75]})
    result = m.transition_summary(table)
    assert result['on_expected_dwell_mean_trials'] == pytest.approx(7.5)
    assert result['off_expected_dwell_mean_trials'] == pytest.approx(3.0)
    assert result['on_expected_dwell_mean_trials'] != pytest.approx(1 / (1 - .85))


def test_invalid_probability_rejected():
    m = load_module()
    with pytest.raises(ValueError, match='transition'):
        m.transition_summary(pd.DataFrame({'P_on_on': [1.1], 'P_off_off': [.8]}))


def test_absorbing_state_explicit_not_json_infinity():
    m = load_module()
    result = m.transition_summary(pd.DataFrame({'P_on_on': [1.0], 'P_off_off': [.8]}))
    assert result['on_expected_dwell_mean_trials'] is None
    assert result['on_absorbing_states'] == 1


def test_93_person_scope_guard():
    m = load_module()
    with pytest.raises(ValueError, match='93'):
        m.validate_input(pd.DataFrame({'ID': [1], 'response': ['p'], 'chose_dom': [1], 'coherence_dom': [10]}))


def test_execution_scope_is_not_clinical_trial():
    m = load_module()
    assert m.SCOPE['clinical_trial'] is False
    assert m.SCOPE['model_comparison_100_masks'] is False
    assert m.SCOPE['online_prediction'] is False
    assert m.SCOPE['raw_to_clean_preprocessing_rerun'] is False
