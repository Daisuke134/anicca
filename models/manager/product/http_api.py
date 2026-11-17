"""Mount router at the authenticated proxy's /manager prefix.

authenticate(request) MUST validate the existing app token and return its stable
account subject. No trusting a request-body person ID, no embedded app secret.
"""
import hashlib
import hmac
import uuid
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
        body = await request.json()
        try:
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
        body = await request.json()
        try:
            return store.observe(owner, body['delivery_id'], body['event'], body['observed_at'])
        except LookupError:
            raise HTTPException(409, 'sender assignment pending')
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, 'invalid observation')

    @api.delete('/evidence')
    async def delete(request: Request):
        store.delete(await subject(request))
        return {'deleted': True}

    return api
