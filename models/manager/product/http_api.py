"""Mount router at the authenticated proxy's /manager prefix.

authenticate(request) MUST validate the existing app token and return its stable
account subject. No trusting a request-body person ID, no embedded app secret.
"""
import hashlib
import hmac
from fastapi import APIRouter, HTTPException, Request
from .interventions import InterventionStore


def router(store: InterventionStore, authenticate, pseudonym_key: bytes):
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


def create_app(path, pseudonym_key, service_token):
    """Private product service. Only the authenticated proxy supplies subjects."""
    from fastapi import FastAPI
    from models.manager.api.server import PRIOR_P_TREATED, PRIOR_P_CONTROL
    if not service_token:
        raise ValueError('service token required')

    async def authenticate(request):
        authorization = request.headers.get('authorization', '')
        if not hmac.compare_digest(authorization, 'Bearer ' + service_token):
            raise HTTPException(401, 'authentication required')
        return request.headers.get('x-manager-subject')

    def prior(context):
        raise HTTPException(503, detail={
            'backend': 'prior', 'error': 'text_generation_unavailable',
            'p_visit_treated': PRIOR_P_TREATED, 'p_visit_control': PRIOR_P_CONTROL,
        })

    app = FastAPI()
    app.include_router(router(InterventionStore(path, prior), authenticate, pseudonym_key))

    @app.get('/manager/health')
    async def health(request: Request):
        if not await authenticate(request):
            raise HTTPException(401, 'authentication required')
        return {'status': 'ok', 'default_backend': 'prior', 'generation_available': False}

    return app


def app_from_env():
    import os
    return create_app(os.environ['MANAGER_STORE_PATH'],
                      os.environ['MANAGER_PSEUDONYM_KEY'].encode(),
                      os.environ['MANAGER_SERVICE_TOKEN'])
