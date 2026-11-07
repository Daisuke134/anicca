#!/usr/bin/env python3
"""Resolve a tenant Capafy provider binding (references only) into publisher state.

The binding (LM_CAPAFY_BINDING_JSON) never carries credential values. This
resolver maps its credentialRef to a tenant-private secret slot that was
provisioned out of band, verifies the referenced account against the official
Capafy API, and materializes exactly the publisher state the existing factory
already consumes:

  - <CAPAFY_PUBLISHER_STATE_HOME>/config.json            (vendor token store shape)
  - <LIFE_MANAGER_STATE_HOME>/.env                        (CAPAFY_* entries the factory sources)
  - <CAPAFY_PUBLISHER_STATE_HOME>/browser-auth-state.json (when the slot carries one)
  - <agent HOME>/.config/ai/registry/browsers.toml       (when the slot carries one:
    registers the tenant-browser:v1 identity so the browser guard can lease it,
    pointing the Linux tenant owner at the materialized browser-auth-state.json)
  - <CAPAFY_PUBLISHER_STATE_HOME>/resolution.json         (secret-free receipt)

Fail closed: any mismatch or unverifiable account removes the materialized
files and raises ResolutionError with a bounded code. Credential values are
never printed, logged, or copied into the receipt.
"""
import datetime
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import urllib.request

API_ORIGIN = 'https://api.capafy.ai'
CREDENTIAL_REF = 'capafy-publisher-slot:v1'
BROWSER_SESSION_REF = 'tenant-browser:v1'
SLOT_RELATIVE = Path('secrets') / 'capafy-publisher.json'
ACCESS_TOKEN = re.compile(r'^am_sk_[A-Za-z0-9_-]{16,480}$')
ENV_KEYS = ('CAPAFY_ACCESS_TOKEN', 'CAPAFY_HOST_OPENROUTER_KEY',
            'CAPAFY_OPENROUTER_MANAGEMENT_KEY')


class ResolutionError(ValueError):
    """A bounded, non-sensitive publisher resolution failure."""


def _fail(code):
    raise ResolutionError(code)


def _private_file(path, owner):
    try:
        info = path.lstat()
        return (stat.S_ISREG(info.st_mode) and info.st_uid == owner
                and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
                and path.resolve(strict=True) == path)
    except OSError:
        return False


def _save_private(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.resolution-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _http_get(path, access_token):
    request = urllib.request.Request(API_ORIGIN + path, headers={
        'Authorization': 'Bearer ' + access_token, 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read())
    if isinstance(payload, dict) and isinstance(payload.get('data'), dict):
        return payload['data']
    if isinstance(payload, dict):
        return payload
    _fail('account_verification_failed')


def _load_slot(state_home, owner):
    slot_path = (state_home / SLOT_RELATIVE)
    if slot_path.resolve(strict=False).parent != (state_home / 'secrets').resolve(strict=False):
        _fail('slot_unavailable')
    if not _private_file(slot_path, owner):
        _fail('slot_unavailable')
    try:
        slot = json.loads(slot_path.read_text())
    except (OSError, ValueError):
        _fail('slot_invalid')
    if not isinstance(slot, dict):
        _fail('slot_invalid')
    token = slot.get('accessToken')
    if not isinstance(token, str) or not ACCESS_TOKEN.match(token):
        _fail('slot_invalid')
    if not isinstance(slot.get('userId'), str) or not slot['userId']:
        _fail('slot_invalid')
    if not isinstance(slot.get('email'), str) or '@' not in slot['email']:
        _fail('slot_invalid')
    if not isinstance(slot.get('hostOpenRouterKey'), str) or not slot['hostOpenRouterKey']:
        _fail('slot_invalid')
    browser_state = slot.get('browserAuthState')
    if browser_state is not None and (not isinstance(browser_state, dict)
                                      or not isinstance(browser_state.get('cookies'), list)):
        _fail('slot_invalid')
    return slot


def resolve_publisher(binding, *, state_home, publisher_home, owner=None,
                      http_get=None, now=None):
    """Materialize publisher state for a validated binding. Returns the receipt."""
    owner = os.geteuid() if owner is None else owner
    state_home = Path(state_home)
    publisher_home = Path(publisher_home)
    if not isinstance(binding, dict) or binding.get('provider') != 'capafy':
        _fail('binding_invalid')
    if binding.get('credentialRef') != CREDENTIAL_REF:
        _fail('binding_credential_ref_unknown')
    if binding.get('browserSessionRef') != BROWSER_SESSION_REF:
        _fail('binding_browser_ref_unknown')
    slot = _load_slot(state_home, owner)
    if slot['userId'] != binding.get('subjectId'):
        _fail('binding_subject_mismatch')
    get = http_get or _http_get
    try:
        profile = get('/agent/account/profile', slot['accessToken'])
        account = get('/agent/account', slot['accessToken'])
    except ResolutionError:
        raise
    except Exception:
        _fail('account_verification_unavailable')
    if not isinstance(profile, dict) or profile.get('userId') != binding['subjectId']:
        _fail('account_verification_failed')
    if (not isinstance(account, dict)
            or str(account.get('email', '')).lower() != slot['email'].lower()):
        _fail('account_verification_failed')
    token_store = {'access_token': slot['accessToken'], 'user_id': slot['userId'],
                   'email': slot['email'], 'name': slot.get('name', '')}
    env_lines = ['# Materialized by publisher_resolution.py for this tenant only.',
                 'CAPAFY_ACCESS_TOKEN=' + slot['accessToken'],
                 'CAPAFY_HOST_OPENROUTER_KEY=' + slot['hostOpenRouterKey']]
    if isinstance(slot.get('openRouterManagementKey'), str) and slot['openRouterManagementKey']:
        env_lines.append('CAPAFY_OPENROUTER_MANAGEMENT_KEY=' + slot['openRouterManagementKey'])
    writes = [(publisher_home / 'config.json',
               json.dumps(token_store, ensure_ascii=False, indent=2) + '\n'),
              (state_home / '.env', '\n'.join(env_lines) + '\n')]
    registry_path = None
    if slot.get('browserAuthState') is not None:
        state_file = publisher_home / 'browser-auth-state.json'
        writes.append((state_file,
                       json.dumps(slot['browserAuthState'], ensure_ascii=False) + '\n'))
        # The factory leases browsers by identity through the registry in the
        # agent HOME (<state_home>/home). Register the tenant identity and tell
        # the Linux tenant owner which materialized state seeds its profile.
        registry_path = (state_home / 'home' / '.config' / 'ai' / 'registry'
                         / 'browsers.toml')
        registry_text = (
            '# Materialized by publisher_resolution.py for this tenant only.\n'
            '[[identity]]\n'
            'id = "' + BROWSER_SESSION_REF + '"\n'
            'profile = "~/.cloak/profiles/tenant-browser"\n'
            'owner = "maritime-tenant"\n'
            'storage_state = "' + str(state_file) + '"\n')
        writes.append((registry_path, registry_text))
    targets = [path for path, _payload in writes]
    try:
        for path, payload in writes:
            _save_private(path, payload)
    except OSError:
        for target in targets:
            try:
                target.unlink()
            except OSError:
                pass
        _fail('materialization_failed')
    stamp = (now or datetime.datetime.now(datetime.timezone.utc)).isoformat()
    receipt = {'tenantId': binding.get('tenantId'), 'provider': 'capafy',
               'subjectId': binding['subjectId'], 'credentialRef': CREDENTIAL_REF,
               'browserSessionRef': BROWSER_SESSION_REF, 'resolvedAt': stamp,
               'accountVerified': True,
               'materials': [str(target) for target in targets],
               'browserSeeded': slot.get('browserAuthState') is not None,
               'browserRegistry': str(registry_path) if registry_path else None}
    _save_private(publisher_home / 'resolution.json',
                  json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    return receipt


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.parse_args()
    try:
        binding = json.loads(os.environ['LM_CAPAFY_BINDING_JSON'])
        state_home = Path(os.environ['LIFE_MANAGER_STATE_HOME'])
        publisher_home = Path(os.environ.get(
            'CAPAFY_PUBLISHER_STATE_HOME', state_home / 'runtime/capafy-publisher'))
        receipt = resolve_publisher(binding, state_home=state_home,
                                    publisher_home=publisher_home)
        print(json.dumps({'status': 'resolved', 'receipt': receipt}))
        return 0
    except ResolutionError as error:
        print(json.dumps({'status': 'deferred', 'errorClass': str(error)}))
        return 2
    except (KeyError, ValueError):
        print(json.dumps({'status': 'deferred', 'errorClass': 'binding_invalid'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
