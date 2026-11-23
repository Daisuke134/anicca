import json
import uuid
import pytest
from fastapi.testclient import TestClient
from models.manager.product.http_api import create_app
from models.manager.product.interventions import InterventionStore


def context():
    return dict(source='daily_home', language='en', desired_state='calm', time_band='morning',
                synthetic_user={'answer_ids': {'desired_state': ['calm'], 'pain_points': ['stress']}, 'answer_version': 4})


class Generator:
    model = 'fixture-model'
    def __call__(self, ctx):
        self.context = ctx
        return [dict(id='a', kind='reflection', text='Let this breath finish.', probability=.8),
                dict(id='b', kind='none', text='', probability=.2)]


def test_home_context_and_bench_journal_are_committed_before_return(tmp_path):
    generator = Generator()
    store = InterventionStore(str(tmp_path / 'cases.db'), generator, draw=lambda: .1)
    key = str(uuid.uuid4())
    decision = store.decide('person', key, context())
    assert generator.context['synthetic_user']['answer_ids']['pain_points'] == ['stress']
    row = decision['managerbench_case']
    assert row['stimulus']['text'] == 'Let this breath finish.'
    assert row['stimulus']['generator_model'] == 'fixture-model'
    assert row['stimulus']['assigned_probability'] == .8
    assert row['situation']['answer_snapshot']['pain_points'] == ['stress']
    assert row['response'] == {}
    with store.connect() as db:
        saved = json.loads(db.execute('SELECT body FROM cases').fetchone()[0])
    assert saved['managerbench_case'] == row
    assert store.decide('person', key, context()) == decision


def test_push_extracts_onboarding_ids_without_forwarding_private_metadata(tmp_path):
    generator = Generator()
    store = InterventionStore(str(tmp_path / 'cases.db'), generator, draw=lambda: .1)
    ctx = {k: v for k, v in context().items() if k != 'synthetic_user'}
    ctx.update(source='notification', desired_state='unknown')
    store.decide_push('person', str(uuid.uuid4()), ctx, {
        'profile': {'name': 'PRIVATE', 'personalization': {'answerIds': {'desired_state': ['confidence']}, 'answerVersion': 4}},
        'recent_reactions': [], 'local_day': '2026-11-20', 'slot': '09:00'})
    assert generator.context['synthetic_user']['answer_ids']['desired_state'] == ['confidence']
    assert 'PRIVATE' not in json.dumps(generator.context)


def test_engine_failure_suppresses_without_journal_assignment(tmp_path):
    def unavailable(_):
        raise TimeoutError('fixture')
    app = create_app(str(tmp_path / 'cases.db'), b'x'*32, 'service', generator=unavailable)
    response = TestClient(app).post('/manager/decisions', headers={
        'Authorization': 'Bearer service', 'X-Manager-Subject': 'person'},
        json={'delivery_id': str(uuid.uuid4()), 'context': context()})
    assert response.status_code == 503


def test_rejects_free_text_conditioning(tmp_path):
    ctx = context()
    ctx['synthetic_user']['answer_ids']['name'] = ['Private Name']
    with pytest.raises(ValueError):
        InterventionStore(str(tmp_path / 'cases.db'), Generator()).decide('person', str(uuid.uuid4()), ctx)


def test_accepts_dotted_catalog_ids_in_recent_message_ids(tmp_path):
    """Regression (2026-11-23, the 1.11.0 blank home): the app sends its
    own viewed quote IDs back as legacy_recent_message_ids, and catalog
    IDs are dotted ("growth.calm.2", "adaptive..."). The answer-value
    regex excluded '.', so every returning user who had viewed such a
    quote got HTTP 422 on every decisions request and a blank home."""
    generator = Generator()
    store = InterventionStore(str(tmp_path / 'cases.db'), generator, draw=lambda: .1)
    ctx = context()
    ctx['synthetic_user']['answer_ids']['legacy_recent_message_ids'] = ['growth.calm.2', 'adaptive.presence.breath']
    decision = store.decide('person', str(uuid.uuid4()), ctx)
    assert decision['chosen']['text'] == 'Let this breath finish.'
    # Free text with spaces is still rejected even on an allowed axis.
    ctx['synthetic_user']['answer_ids']['legacy_recent_message_ids'] = ['not an id']
    with pytest.raises(ValueError):
        store.decide('person', str(uuid.uuid4()), ctx)


def test_none_and_measured_outcomes_export_without_invented_negatives(tmp_path):
    from models.manager.product.export_cases import export_cases
    path = str(tmp_path / 'cases.db')
    store = InterventionStore(path, Generator(), draw=lambda: .9)
    key = str(uuid.uuid4())
    result = store.decide('person', key, context())
    rows = list(export_cases(path))
    assert len(rows) == 1
    assert rows[0]['stimulus']['treatment_assigned'] == 'do_not_send'
    assert rows[0]['stimulus']['assigned_probability'] == .2
    assert rows[0]['response'] == {}
    store.observe('person', key, 'app_opened', result['decision_point_at'] + 2)
    store.observe('person', key, 'saved', result['outcome_window_end'] + 1)
    row = list(export_cases(path))[0]
    assert row['response']['app_opened'] is True
    assert 'saved' not in row['response']


def test_openrouter_existing_credit_default(monkeypatch, tmp_path):
    from models.manager.product.http_api import app_from_env
    for key in ('MANAGER_LLM_BASE_URL', 'MANAGER_LLM_MODEL', 'MANAGER_LLM_API_KEY', 'OPENAI_API_KEY'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture-key')
    monkeypatch.setenv('MANAGER_STORE_PATH', str(tmp_path / 'env.db'))
    monkeypatch.setenv('MANAGER_PSEUDONYM_KEY', 'x' * 32)
    monkeypatch.setenv('MANAGER_SERVICE_TOKEN', 'service')
    response = TestClient(app_from_env()).get('/manager/health', headers={
        'Authorization': 'Bearer service', 'X-Manager-Subject': 'person'})
    assert response.json()['generator_model'] == 'deepseek/deepseek-v4.1-flash-1017'


def test_openrouter_key_is_not_forwarded_to_custom_endpoint(monkeypatch, tmp_path):
    from models.manager.product.http_api import app_from_env
    from models.manager.product import interventions
    configured = []
    monkeypatch.setattr(interventions, 'ChatLLMGenerator', lambda base, model, api_key=None: configured.append(api_key) or Generator())
    monkeypatch.delenv('MANAGER_LLM_API_KEY', raising=False)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fixture-key')
    monkeypatch.setenv('MANAGER_LLM_BASE_URL', 'http://127.0.0.1:1234/v1')
    monkeypatch.setenv('MANAGER_LLM_MODEL', 'fixture')
    monkeypatch.setenv('MANAGER_STORE_PATH', str(tmp_path / 'env.db'))
    monkeypatch.setenv('MANAGER_PSEUDONYM_KEY', 'x' * 32)
    monkeypatch.setenv('MANAGER_SERVICE_TOKEN', 'service')
    app_from_env()
    assert configured == [None]


def test_generated_assignment_candidate_ids_include_chosen_message(tmp_path):
    store = InterventionStore(str(tmp_path / 'cases.db'), Generator(), draw=lambda: .1)
    result = store.decide('person', str(uuid.uuid4()), context())
    stimulus = result['managerbench_case']['stimulus']
    assert stimulus['message_id'] in stimulus['candidate_ids']
