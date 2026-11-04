"""FastAPI -> httpx relay -> private service, with persistent per-user ownership."""
from copy import deepcopy
import json

import httpx
import pytest
from fastapi import FastAPI

from src.routers.kataster import router
from src.services.database import get_db
from src.services.kataster import KatasterRelay, PNG_SIGNATURE, get_relay

JOB = 'a' * 32
OWNER = {'X-Kratos-Identity-ID': 'identity-owner'}
OTHER = {'X-Kratos-Identity-ID': 'identity-other'}
BODY = {'adresse': 'Im Schönenfelde 14, 21109 Hamburg'}
RESULT = {
    'status': 'ok', 'grundstueck_status': 'ok',
    'grundstuecke': [{'gemarkung': 'Wilhelmsburg', 'flur': None, 'flurstueck': '2798'}],
    'bild': {'status': 'ok', 'datei': 'karte.png', 'breite_meter': 60},
    'dateien': {'json': f'/ergebnisse/{JOB}/grundstueck.json', 'bild': f'/ergebnisse/{JOB}/karte.png'},
}


@pytest.fixture(params=['/api/admin/liegenschaftskarte', '/api/installer/liegenschaftskarte'])
def prefix(request): return request.param


@pytest.fixture
def api(mongomock_motor_db):
    calls = []
    def handler(request):
        calls.append(request)
        if request.method == 'POST': return httpx.Response(200, json=deepcopy(RESULT))
        if request.url.path == '/laender': return httpx.Response(200, json={'HH': {'name': 'Hamburg'}})
        return httpx.Response(200, content=PNG_SIGNATURE + b'example', headers={'Content-Type': 'image/png'})
    app = FastAPI()
    for p in ('/api/admin/liegenschaftskarte', '/api/installer/liegenschaftskarte'):
        app.include_router(router, prefix=p)
    app.dependency_overrides[get_db] = lambda: mongomock_motor_db
    app.dependency_overrides[get_relay] = lambda: KatasterRelay(httpx.MockTransport(handler))
    return app, calls


def client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')


def upstream(app, handler):
    app.dependency_overrides[get_relay] = lambda: KatasterRelay(httpx.MockTransport(handler))


async def test_missing_identity_cannot_use_relay(api, prefix):
    app, calls = api
    async with client(app) as c:
        assert (await c.post(prefix + '/auszug', json=BODY)).status_code == 401
        assert (await c.get(prefix + '/laender')).status_code == 401
        assert (await c.get(prefix + f'/ergebnisse/{JOB}/karte.png')).status_code == 401
    assert calls == []


async def test_create_rewrites_links_defaults_and_downloads(api, prefix, mongomock_motor_db):
    app, calls = api
    async with client(app) as c:
        response = await c.post(prefix + '/auszug', json=BODY, headers=OWNER)
        assert response.status_code == 200
        result = response.json()
        assert result['dateien']['bild'] == prefix + f'/ergebnisse/{JOB}/karte.png'
        assert result['dateien']['json'] == prefix + f'/ergebnisse/{JOB}/grundstueck.json'
        assert json.loads(calls[0].content) == {**BODY, 'breite_meter': 60.0, 'nur_amtlich': True}
        assert calls[0].url.host == 'na-kataster'
        assert 'x-kratos-identity-id' not in calls[0].headers
        stored = await mongomock_motor_db.liegenschaftskarten.find_one({'_id': JOB})
        assert stored['created_by'] == 'identity-owner'
        metadata = await c.get(result['dateien']['json'], headers=OWNER)
        assert metadata.status_code == 200
        assert metadata.json()['grundstuecke'][0]['gemarkung'] == 'Wilhelmsburg'
        assert metadata.json()['dateien'] == result['dateien']
        assert len(calls) == 1
        image = await c.get(result['dateien']['bild'], headers=OWNER)
        assert image.status_code == 200
        assert image.headers['content-type'] == 'image/png'
        assert image.headers['cache-control'] == 'private, no-store'
        assert image.content.startswith(PNG_SIGNATURE)
        assert calls[1].url.path == f'/ergebnisse/{JOB}/karte.png'


async def test_other_user_and_unknown_job_are_hidden(api, prefix):
    app, calls = api
    async with client(app) as c:
        await c.post(prefix + '/auszug', json=BODY, headers=OWNER)
        for name in ['karte.png', 'grundstueck.json']:
            assert (await c.get(prefix + f'/ergebnisse/{JOB}/{name}', headers=OTHER)).status_code == 404
            assert (await c.get(prefix + f'/ergebnisse/{"b"*32}/{name}', headers=OWNER)).status_code == 404
    assert len(calls) == 1


async def test_duplicate_job_never_overwrites_owner(api, prefix):
    app, _ = api
    async with client(app) as c:
        assert (await c.post(prefix + '/auszug', json=BODY, headers=OWNER)).status_code == 200
        assert (await c.post(prefix + '/auszug', json=BODY, headers=OTHER)).status_code == 502
        assert (await c.get(prefix + f'/ergebnisse/{JOB}/grundstueck.json', headers=OWNER)).status_code == 200
        assert (await c.get(prefix + f'/ergebnisse/{JOB}/grundstueck.json', headers=OTHER)).status_code == 404


@pytest.mark.parametrize('body', [{}, {'adresse':'x'}, {**BODY,'breite_meter':0},
    {**BODY,'breite_meter':1001}, {**BODY,'nur_amtlich':'false'}, {**BODY,'url':'http://external'}])
async def test_validation_prevents_upstream_call(api, prefix, body):
    app, calls = api
    async with client(app) as c:
        assert (await c.post(prefix + '/auszug', json=body, headers=OWNER)).status_code == 422
    assert not calls


async def test_countries_are_relayed(api, prefix):
    app, calls = api
    async with client(app) as c: r = await c.get(prefix + '/laender', headers=OWNER)
    assert r.status_code == 200
    assert r.json()['HH']['name'] == 'Hamburg'
    assert calls[0].url.path == '/laender'


@pytest.mark.parametrize('path', ['http://evil/ergebnisse/'+JOB+'/karte.png', '/etc/passwd', '/ergebnisse/'+'b'*32+'/karte.png'])
async def test_untrusted_image_paths_are_rejected(api, prefix, path, mongomock_motor_db):
    app, _ = api
    result = deepcopy(RESULT); result['dateien']['bild'] = path
    upstream(app, lambda r: httpx.Response(200, json=result))
    async with client(app) as c:
        assert (await c.post(prefix + '/auszug', json=BODY, headers=OWNER)).status_code == 502
    assert await mongomock_motor_db.liegenschaftskarten.count_documents({}) == 0


async def test_partial_result_without_image(api, prefix):
    app, _ = api
    result = deepcopy(RESULT); result['status'] = 'teilweise'; result['dateien']['bild'] = None
    upstream(app, lambda r: httpx.Response(200, json=result))
    async with client(app) as c:
        response = await c.post(prefix + '/auszug', json=BODY, headers=OWNER)
        assert response.status_code == 200
        assert response.json()['dateien']['bild'] is None
        assert response.json()['status'] == 'teilweise'
        assert (await c.get(prefix + f'/ergebnisse/{JOB}/karte.png', headers=OWNER)).status_code == 404


@pytest.mark.parametrize('status,expected', [(422,422), (429,429), (500,502), (302,502)])
async def test_error_status_and_retry_after(api, prefix, status, expected):
    app, _ = api
    upstream(app, lambda r: httpx.Response(status, json={'code':'TEST','meldung':'Testfehler'}))
    async with client(app) as c: response = await c.post(prefix + '/auszug', json=BODY, headers=OWNER)
    assert response.status_code == expected
    if status == 429: assert response.headers['retry-after'] == '10'


@pytest.mark.parametrize('error,expected', [(httpx.ReadTimeout,504), (httpx.ConnectError,502)])
async def test_transport_errors_hide_internal_details(api, prefix, error, expected):
    app, _ = api
    def fail(request): raise error('http://na-kataster:8765 internal details', request=request)
    upstream(app, fail)
    async with client(app) as c: response = await c.post(prefix + '/auszug', json=BODY, headers=OWNER)
    assert response.status_code == expected
    assert 'na-kataster' not in response.text


async def test_main_app_registers_only_authenticated_namespaces():
    from src.main import app
    paths = {route.path for route in app.routes}
    assert '/api/admin/liegenschaftskarte/auszug' in paths
    assert '/api/installer/liegenschaftskarte/auszug' in paths
    assert '/api/liegenschaftskarte/auszug' not in paths
