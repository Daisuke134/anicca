"""Mount router at the authenticated proxy's /manager prefix.

authenticate(request) MUST validate the existing app token and return its stable
account subject. No trusting a request-body person ID, no embedded app secret.
"""
import hashlib
import hmac
from fastapi import APIRouter, HTTPException, Request
from .interventions import InterventionStore


def router(store: InterventionStore, authenticate, pseudonym_key: bytes, authenticate_sender=None):
    if len(pseudonym_key) < 32:
        raise ValueError('server pseudonym key must contain at least 32 bytes')
    api = APIRouter(prefix='/manager')

    async def subject(request):
        account = await authenticate(request)
        if not account:
            raise HTTPException(401, 'authentication required')
        return hmac.new(pseudonym_key, str(account).encode(), hashlib.sha256).hexdigest()

    @api.post('/decisions')
    async def decide(request: Request):
        owner = await subject(request)
        try:
            body = await request.json()
            # Sync model/database work must not block the gateway event loop.
            from starlette.concurrency import run_in_threadpool
            return await run_in_threadpool(store.decide, owner, body['delivery_id'], body['context'])
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, 'invalid decision or model output')
        except PermissionError:
            raise HTTPException(410, 'subject deleted')
        except OSError:
            raise HTTPException(503, 'generation unavailable')

    @api.post('/push-decisions')
    async def push_decisions(request: Request):
        # Separate trusted service identity; app tokens cannot select other users.
        if authenticate_sender is None or not await authenticate_sender(request):
            raise HTTPException(401, 'sender authentication required')
        try:
            body = await request.json()
            items = body['decisions']
            if not isinstance(items, list) or not 1 <= len(items) <= 100:
                raise ValueError('invalid batch')
            from starlette.concurrency import run_in_threadpool
            results = []
            for item in items:
                if not isinstance(item['subject'], str) or not item['subject']:
                    raise ValueError('invalid subject')
                owner = hmac.new(pseudonym_key, item['subject'].encode(), hashlib.sha256).hexdigest()
                results.append(await run_in_threadpool(store.decide_push, owner,
                    item['delivery_id'], item['context'], item['push_state']))
            return {'decisions': results}
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, 'invalid push decision or model output')
        except PermissionError:
            raise HTTPException(410, 'subject deleted')
        except OSError:
            raise HTTPException(503, 'generation unavailable')

    @api.post('/observations')
    async def observe(request: Request):
        owner = await subject(request)
        try:
            body = await request.json()
            return store.observe(owner, body['delivery_id'], body['event'], body['observed_at'])
        except LookupError:
            raise HTTPException(409, 'sender assignment pending')
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, 'invalid observation')

    @api.post('/decision-records')
    async def decision_records(request: Request):
        owner = await subject(request)
        from .decision_records import ingest
        from starlette.concurrency import run_in_threadpool
        try:
            return await run_in_threadpool(
                ingest, str(store.path) + '.decision-records.jsonl', owner, await request.json())
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, 'invalid decision record')

    @api.delete('/evidence')
    async def delete(request: Request):
        store.delete(await subject(request))
        return {'deleted': True}

    return api


def create_app(path, pseudonym_key, service_token, generator=None, sender_token=None):
    """Private product service. Only the authenticated proxy supplies subjects.

    With a generator configured, decisions are generated per person at
    decision time by that LLM engine. Without one, the service stays in
    the honest prior mode: decisions fail closed with explicit labelling.
    """
    from fastapi import FastAPI
    from models.manager.api.server import PRIOR_P_TREATED, PRIOR_P_CONTROL
    if not service_token:
        raise ValueError('service token required')

    async def authenticate(request):
        authorization = request.headers.get('authorization', '')
        if not hmac.compare_digest(authorization, 'Bearer ' + service_token):
            raise HTTPException(401, 'authentication required')
        return request.headers.get('x-manager-subject')

    async def authenticate_sender(request):
        if not sender_token:
            return False
        authorization = request.headers.get('authorization', '')
        return hmac.compare_digest(authorization, 'Bearer ' + sender_token)

    def prior(context):
        raise HTTPException(503, detail={
            'backend': 'prior', 'error': 'text_generation_unavailable',
            'p_visit_treated': PRIOR_P_TREATED, 'p_visit_control': PRIOR_P_CONTROL,
        })

    app = FastAPI()
    app.include_router(router(InterventionStore(path, generator or prior),
                              authenticate, pseudonym_key,
                              authenticate_sender=authenticate_sender if sender_token else None))

    @app.get('/manager/health')
    async def health(request: Request):
        if not await authenticate(request):
            raise HTTPException(401, 'authentication required')
        if generator is None:
            return {'status': 'ok', 'default_backend': 'prior', 'generation_available': False}
        return {'status': 'ok', 'default_backend': 'manager-v1', 'generation_available': True,
                'generator_model': getattr(generator, 'model', 'manager-v1')}

    return app


def app_from_env():
    import os
    generator = None
    base_url = os.environ.get('MANAGER_LLM_BASE_URL', 'https://openrouter.ai/api/v1')
    model = os.environ.get('MANAGER_LLM_MODEL', 'deepseek/deepseek-v4.1-flash-1017')
    key = os.environ.get('MANAGER_LLM_API_KEY')
    if not key and base_url.rstrip('/') == 'https://openrouter.ai/api/v1':
        key = os.environ.get('OPENROUTER_API_KEY')
    # A missing existing credit/key remains unavailable; never use another paid account.
    if key or (os.environ.get('MANAGER_LLM_BASE_URL') and os.environ.get('MANAGER_LLM_MODEL')):
        from .interventions import ChatLLMGenerator
        generator = ChatLLMGenerator(base_url, model, api_key=key)
    return create_app(os.environ['MANAGER_STORE_PATH'],
                      os.environ['MANAGER_PSEUDONYM_KEY'].encode(),
                      os.environ['MANAGER_SERVICE_TOKEN'],
                      generator=generator,
                      sender_token=os.environ.get('MANAGER_SENDER_TOKEN'))
